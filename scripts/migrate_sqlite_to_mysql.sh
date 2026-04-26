#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
MANAGE_PY="${ROOT_DIR}/manage.py"
SQLITE_DB_PATH="${ROOT_DIR}/db.sqlite3"
TMP_DIR="${ROOT_DIR}/tmp"
FIXTURE_PATH="${TMP_DIR}/sqlite_to_mysql_dump.json"

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_DB="${MYSQL_DB:-project_hub}"
MYSQL_USER="${MYSQL_USER:-project_hub_user}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-project_hub_password}"
MYSQL_ROOT_USER="${MYSQL_ROOT_USER:-root}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
MYSQL_ADMIN_MODE="${MYSQL_ADMIN_MODE:-auto}"
MYSQL_SOCKET="${MYSQL_SOCKET:-/var/run/mysqld/mysqld.sock}"
OPEN_MYSQL_SHELL="${OPEN_MYSQL_SHELL:-true}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Missing virtualenv python at ${VENV_PYTHON}"
  exit 1
fi

if [[ ! -f "${MANAGE_PY}" ]]; then
  echo "Could not find manage.py at ${MANAGE_PY}"
  exit 1
fi

if [[ ! -f "${SQLITE_DB_PATH}" ]]; then
  echo "Could not find SQLite database at ${SQLITE_DB_PATH}"
  exit 1
fi

if ! command -v mysql >/dev/null 2>&1; then
  echo "The mysql CLI is required but was not found in PATH."
  echo "Install MySQL client tools first, then rerun this script."
  exit 1
fi

run_admin_sql() {
  local sql="$1"

  if [[ "${MYSQL_ADMIN_MODE}" == "password" || "${MYSQL_ADMIN_MODE}" == "auto" ]]; then
    if MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql \
      --host="${MYSQL_HOST}" \
      --port="${MYSQL_PORT}" \
      --user="${MYSQL_ROOT_USER}" \
      -e "SELECT 1;" >/dev/null 2>&1; then
      MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql \
        --host="${MYSQL_HOST}" \
        --port="${MYSQL_PORT}" \
        --user="${MYSQL_ROOT_USER}" \
        <<SQL
${sql}
SQL
      return
    fi
  fi

  if [[ "${MYSQL_ADMIN_MODE}" == "socket" || "${MYSQL_ADMIN_MODE}" == "auto" ]]; then
    if command -v sudo >/dev/null 2>&1 && sudo mysql --socket="${MYSQL_SOCKET}" -e "SELECT 1;" >/dev/null 2>&1; then
      sudo mysql --socket="${MYSQL_SOCKET}" <<SQL
${sql}
SQL
      return
    fi

    if mysql --socket="${MYSQL_SOCKET}" --user="${MYSQL_ROOT_USER}" -e "SELECT 1;" >/dev/null 2>&1; then
      mysql --socket="${MYSQL_SOCKET}" --user="${MYSQL_ROOT_USER}" <<SQL
${sql}
SQL
      return
    fi
  fi

  echo "Could not connect as MySQL admin."
  echo "Tried password auth to ${MYSQL_ROOT_USER}@${MYSQL_HOST}:${MYSQL_PORT}"
  echo "and socket auth via ${MYSQL_SOCKET}."
  echo
  echo "Try one of these:"
  echo "1. Set MYSQL_ADMIN_MODE=password and provide the correct MYSQL_ROOT_PASSWORD."
  echo "2. Set MYSQL_ADMIN_MODE=socket and rerun."
  echo "3. Verify MySQL root access manually with: sudo mysql"
  exit 1
}

mkdir -p "${TMP_DIR}"

echo "1/7 Backing up current SQLite database..."
cp "${SQLITE_DB_PATH}" "${SQLITE_DB_PATH}.backup.$(date +%Y%m%d_%H%M%S)"

echo "2/7 Exporting SQLite data to JSON fixture..."
DB_ENGINE=sqlite3 \
SQLITE_DB_NAME="${SQLITE_DB_PATH}" \
"${VENV_PYTHON}" "${MANAGE_PY}" dumpdata \
  --natural-foreign \
  --natural-primary \
  --exclude contenttypes \
  --exclude auth.permission \
  --indent 2 \
  > "${FIXTURE_PATH}"

echo "3/7 Creating MySQL database and user if needed..."
run_admin_sql "
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DB}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
ALTER USER '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${MYSQL_DB}\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
"

echo "4/7 Running Django migrations on MySQL..."
DB_ENGINE=mysql \
DB_NAME="${MYSQL_DB}" \
DB_USER="${MYSQL_USER}" \
DB_PASSWORD="${MYSQL_PASSWORD}" \
DB_HOST="${MYSQL_HOST}" \
DB_PORT="${MYSQL_PORT}" \
"${VENV_PYTHON}" "${MANAGE_PY}" migrate --noinput

echo "5/7 Loading exported data into MySQL..."
DB_ENGINE=mysql \
DB_NAME="${MYSQL_DB}" \
DB_USER="${MYSQL_USER}" \
DB_PASSWORD="${MYSQL_PASSWORD}" \
DB_HOST="${MYSQL_HOST}" \
DB_PORT="${MYSQL_PORT}" \
"${VENV_PYTHON}" "${MANAGE_PY}" loaddata "${FIXTURE_PATH}"

echo "6/7 Verifying migrated data counts..."
DB_ENGINE=sqlite3 \
SQLITE_DB_NAME="${SQLITE_DB_PATH}" \
"${VENV_PYTHON}" "${MANAGE_PY}" shell -c "
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.teams.models import Team
from apps.events.models import Event
from apps.notifications.models import Notification
User = get_user_model()
print('SQLite counts:', {
    'users': User.objects.count(),
    'projects': Project.objects.count(),
    'teams': Team.objects.count(),
    'events': Event.objects.count(),
    'notifications': Notification.objects.count(),
})
"

DB_ENGINE=mysql \
DB_NAME="${MYSQL_DB}" \
DB_USER="${MYSQL_USER}" \
DB_PASSWORD="${MYSQL_PASSWORD}" \
DB_HOST="${MYSQL_HOST}" \
DB_PORT="${MYSQL_PORT}" \
"${VENV_PYTHON}" "${MANAGE_PY}" shell -c "
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.teams.models import Team
from apps.events.models import Event
from apps.notifications.models import Notification
User = get_user_model()
print('MySQL counts:', {
    'users': User.objects.count(),
    'projects': Project.objects.count(),
    'teams': Team.objects.count(),
    'events': Event.objects.count(),
    'notifications': Notification.objects.count(),
})
"

echo "7/7 Migration complete."
echo
echo "Use MySQL from terminal with:"
echo "MYSQL_PWD='${MYSQL_PASSWORD}' mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER} ${MYSQL_DB}"
echo

if [[ "${OPEN_MYSQL_SHELL}" == "true" ]]; then
  echo "Opening MySQL terminal..."
  MYSQL_PWD="${MYSQL_PASSWORD}" mysql \
    --host="${MYSQL_HOST}" \
    --port="${MYSQL_PORT}" \
    --user="${MYSQL_USER}" \
    "${MYSQL_DB}"
fi
