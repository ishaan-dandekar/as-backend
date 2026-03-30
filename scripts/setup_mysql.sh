#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="/media/vivi/Data/Projects/Mini-Project/.venv/bin/python"
ENV_FILE="$PROJECT_DIR/.env"

generate_strong_password() {
  local raw
  raw="$(tr -dc 'A-Za-z0-9@#%+=_' </dev/urandom | head -c 18)"
  printf '%s' "${raw}Aa1!"
}

is_strong_password() {
  local p="$1"
  [[ ${#p} -ge 12 ]] && [[ "$p" =~ [A-Z] ]] && [[ "$p" =~ [a-z] ]] && [[ "$p" =~ [0-9] ]] && [[ "$p" =~ [^A-Za-z0-9] ]]
}

upsert_env() {
  local key="$1"
  local value="$2"

  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<'EOF'
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=mysql
DB_NAME=project_hub
DB_USER=project_hub_user
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=7
EOF
fi

DB_NAME="$(grep -E '^DB_NAME=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
DB_USER="$(grep -E '^DB_USER=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
DB_PASSWORD="$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"

DB_NAME="${DB_NAME:-project_hub}"
DB_USER="${DB_USER:-project_hub_user}"

if [[ -z "${DB_PASSWORD}" ]] || ! is_strong_password "$DB_PASSWORD"; then
  DB_PASSWORD="$(generate_strong_password)"
fi

upsert_env "DB_ENGINE" "mysql"
upsert_env "DB_NAME" "$DB_NAME"
upsert_env "DB_USER" "$DB_USER"
upsert_env "DB_PASSWORD" "$DB_PASSWORD"
upsert_env "DB_HOST" "127.0.0.1"
upsert_env "DB_PORT" "3306"

echo "[1/3] Provisioning MySQL database and user..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
sudo mysql -e "ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
sudo mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

echo "[2/3] Verifying Django can read migrations..."
cd "$PROJECT_DIR"
"$PYTHON_BIN" manage.py showmigrations > /tmp/project_hub_migrations.txt

if [[ -s /tmp/project_hub_migrations.txt ]]; then
  echo "[3/3] Success: Django connected to MySQL."
  echo "Database credentials are saved in .env"
  echo "  DB_USER=${DB_USER}"
  echo "  DB_NAME=${DB_NAME}"
  echo "Run next:"
  echo "  $PYTHON_BIN manage.py migrate"
  echo "  $PYTHON_BIN manage.py runserver"
else
  echo "Verification failed: no migration output found."
  exit 1
fi
