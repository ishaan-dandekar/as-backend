from django.db import migrations, models


def _derive_moodle_id(username, email, fallback=''):
    username_value = (username or '').strip()
    email_value = (email or '').strip().lower()

    if username_value.isdigit():
        return username_value

    local_part = email_value.split('@')[0] if '@' in email_value else ''
    if local_part.isdigit():
        return local_part

    if local_part:
        return local_part

    if username_value:
        return username_value

    return (fallback or '').strip()


def migrate_user_primary_keys_to_moodle_id(apps, schema_editor):
    User = apps.get_model('core', 'User')
    Team = apps.get_model('teams', 'Team')
    JoinRequest = apps.get_model('teams', 'JoinRequest')
    Event = apps.get_model('events', 'Event')
    Notification = apps.get_model('notifications', 'Notification')
    Project = apps.get_model('projects', 'Project')
    UserProfileMeta = apps.get_model('users', 'UserProfileMeta')

    mapping = {}
    occupied_ids = set(User.objects.values_list('id', flat=True))

    for user in User.objects.all():
        old_id = str(user.id)
        new_id = _derive_moodle_id(user.username, user.email, fallback=old_id)

        if not new_id or new_id == old_id:
            continue

        if new_id in occupied_ids:
            raise RuntimeError(
                f"Cannot migrate user IDs: derived Moodle ID '{new_id}' already exists."
            )

        mapping[old_id] = new_id
        occupied_ids.discard(old_id)
        occupied_ids.add(new_id)

    if not mapping:
        return

    through_model = Team.members.through

    schema_editor.connection.disable_constraint_checking()
    try:
        for old_id, new_id in mapping.items():
            Team.objects.filter(owner_id=old_id).update(owner_id=new_id)
            JoinRequest.objects.filter(user_id=old_id).update(user_id=new_id)
            through_model.objects.filter(user_id=old_id).update(user_id=new_id)
            Event.objects.filter(organizer_id=old_id).update(organizer_id=new_id)
            Notification.objects.filter(user_id=old_id).update(user_id=new_id)
            Project.objects.filter(owner_id=old_id).update(owner_id=new_id)
            UserProfileMeta.objects.filter(user_id=old_id).update(user_id=new_id)
            User.objects.filter(id=old_id).update(id=new_id)
    finally:
        schema_editor.connection.enable_constraint_checking()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_fix_sqlite_user_fk_targets'),
        ('users', '0001_initial'),
        ('teams', '0001_initial'),
        ('events', '0001_initial'),
        ('notifications', '0001_initial'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='id',
            field=models.CharField(editable=False, max_length=32, primary_key=True, serialize=False),
        ),
        migrations.RunPython(migrate_user_primary_keys_to_moodle_id, migrations.RunPython.noop),
    ]
