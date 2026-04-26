from django.db import migrations


DROP_SQL = [
    'DROP TABLE IF EXISTS "projects_project";',
    'DROP TABLE IF EXISTS "teams_joinrequest";',
    'DROP TABLE IF EXISTS "teams_team_members";',
    'DROP TABLE IF EXISTS "teams_team";',
    'DROP TABLE IF EXISTS "events_event";',
    'DROP TABLE IF EXISTS "notifications_notification";',
    'DROP TABLE IF EXISTS "users_userprofilemeta";',
]


CREATE_SQL = [
    """
    CREATE TABLE "users_userprofilemeta" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "profile_picture_url" varchar(200) NULL,
        "updated_at" datetime NOT NULL,
        "user_id" char(32) NOT NULL UNIQUE REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    """
    CREATE TABLE "teams_team" (
        "id" char(32) NOT NULL PRIMARY KEY,
        "name" varchar(255) NOT NULL,
        "description" text NULL,
        "member_count" integer NOT NULL,
        "capacity" integer NOT NULL,
        "member_roles" text NOT NULL CHECK ((JSON_VALID("member_roles") OR "member_roles" IS NULL)),
        "is_active" bool NOT NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "owner_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE INDEX "teams_team_owner_id_idx" ON "teams_team" ("owner_id");',
    """
    CREATE TABLE "teams_team_members" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "team_id" char(32) NOT NULL REFERENCES "teams_team" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE UNIQUE INDEX "teams_team_members_team_id_user_id_uniq" ON "teams_team_members" ("team_id", "user_id");',
    'CREATE INDEX "teams_team_members_team_id_idx" ON "teams_team_members" ("team_id");',
    'CREATE INDEX "teams_team_members_user_id_idx" ON "teams_team_members" ("user_id");',
    """
    CREATE TABLE "teams_joinrequest" (
        "id" char(32) NOT NULL PRIMARY KEY,
        "status" varchar(20) NOT NULL,
        "message" text NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "team_id" char(32) NOT NULL REFERENCES "teams_team" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE UNIQUE INDEX "teams_joinrequest_team_id_user_id_uniq" ON "teams_joinrequest" ("team_id", "user_id");',
    'CREATE INDEX "teams_joinrequest_team_id_idx" ON "teams_joinrequest" ("team_id");',
    'CREATE INDEX "teams_joinrequest_user_id_idx" ON "teams_joinrequest" ("user_id");',
    """
    CREATE TABLE "events_event" (
        "id" char(32) NOT NULL PRIMARY KEY,
        "title" varchar(255) NOT NULL,
        "description" text NOT NULL,
        "image_url" varchar(200) NULL,
        "location" varchar(255) NOT NULL,
        "start_date" datetime NOT NULL,
        "end_date" datetime NOT NULL,
        "status" varchar(20) NOT NULL,
        "attendees" text NOT NULL CHECK ((JSON_VALID("attendees") OR "attendees" IS NULL)),
        "attendee_count" integer NOT NULL,
        "capacity" integer NOT NULL,
        "tags" text NOT NULL CHECK ((JSON_VALID("tags") OR "tags" IS NULL)),
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "organizer_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE INDEX "events_event_organizer_id_idx" ON "events_event" ("organizer_id");',
    """
    CREATE TABLE "notifications_notification" (
        "id" char(32) NOT NULL PRIMARY KEY,
        "type" varchar(25) NOT NULL,
        "title" varchar(255) NOT NULL,
        "message" text NOT NULL,
        "related_id" varchar(255) NULL,
        "related_type" varchar(50) NULL,
        "is_read" bool NOT NULL,
        "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)),
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "user_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE INDEX "notifications_notification_user_id_idx" ON "notifications_notification" ("user_id");',
    'CREATE INDEX "notifications_notification_user_id_is_read_idx" ON "notifications_notification" ("user_id", "is_read");',
    """
    CREATE TABLE "projects_project" (
        "id" char(32) NOT NULL PRIMARY KEY,
        "title" varchar(255) NOT NULL,
        "description" text NOT NULL,
        "thumbnail_url" varchar(200) NULL,
        "images" text NOT NULL CHECK ((JSON_VALID("images") OR "images" IS NULL)),
        "tech_stack" text NOT NULL CHECK ((JSON_VALID("tech_stack") OR "tech_stack" IS NULL)),
        "status" varchar(25) NOT NULL,
        "team_member_count" integer NOT NULL,
        "team_capacity" integer NOT NULL,
        "github_url" varchar(200) NULL,
        "live_url" varchar(200) NULL,
        "bookmarked_by" text NOT NULL CHECK ((JSON_VALID("bookmarked_by") OR "bookmarked_by" IS NULL)),
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "owner_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "team_id" char(32) NULL REFERENCES "teams_team" ("id") DEFERRABLE INITIALLY DEFERRED
    );
    """,
    'CREATE INDEX "projects_project_owner_id_idx" ON "projects_project" ("owner_id");',
    'CREATE INDEX "projects_project_team_id_idx" ON "projects_project" ("team_id");',
]


def fix_sqlite_user_fk_targets(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return

    cursor = schema_editor.connection.cursor()
    project_foreign_keys = cursor.execute("PRAGMA foreign_key_list(projects_project)").fetchall()
    if not any(fk[2] == 'auth_user' for fk in project_foreign_keys):
        return

    schema_editor.connection.disable_constraint_checking()
    try:
        for statement in DROP_SQL:
            schema_editor.execute(statement)
        for statement in CREATE_SQL:
            schema_editor.execute(statement)
    finally:
        schema_editor.connection.enable_constraint_checking()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_repair_user_fk_tables'),
    ]

    operations = [
        migrations.RunPython(fix_sqlite_user_fk_targets, migrations.RunPython.noop),
    ]
