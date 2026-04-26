from django.db import migrations


TARGET_TABLES = [
    'projects_project',
    'teams_joinrequest',
    'teams_team_members',
    'teams_team',
    'events_event',
    'notifications_notification',
    'users_userprofilemeta',
]


def repair_user_fk_tables(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return

    cursor = schema_editor.connection.cursor()

    existing_tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    if 'projects_project' not in existing_tables:
        return

    project_foreign_keys = cursor.execute("PRAGMA foreign_key_list(projects_project)").fetchall()
    if not any(fk[2] == 'auth_user' for fk in project_foreign_keys):
        return

    Team = apps.get_model('teams', 'Team')
    JoinRequest = apps.get_model('teams', 'JoinRequest')
    Project = apps.get_model('projects', 'Project')
    Event = apps.get_model('events', 'Event')
    Notification = apps.get_model('notifications', 'Notification')
    UserProfileMeta = apps.get_model('users', 'UserProfileMeta')

    create_order = [
        UserProfileMeta,
        Team,
        JoinRequest,
        Event,
        Notification,
        Project,
    ]

    schema_editor.connection.disable_constraint_checking()
    try:
        for table_name in TARGET_TABLES:
            schema_editor.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        for model in create_order:
            schema_editor.create_model(model)
    finally:
        schema_editor.connection.enable_constraint_checking()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_rename_teams_joined_count'),
        ('users', '0001_initial'),
        ('teams', '0001_initial'),
        ('events', '0001_initial'),
        ('notifications', '0001_initial'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(repair_user_fk_tables, migrations.RunPython.noop),
    ]
