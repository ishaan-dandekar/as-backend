from django.db import migrations


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


def sync_usernames_to_primary_key(apps, schema_editor):
    User = apps.get_model('core', 'User')

    occupied_usernames = set(User.objects.values_list('username', flat=True))

    for user in User.objects.all():
        desired_username = _derive_moodle_id(user.username, user.email, fallback=str(user.id))
        current_username = (user.username or '').strip()

        if not desired_username or current_username == desired_username:
            continue

        occupied_usernames.discard(current_username)
        if desired_username in occupied_usernames:
            raise RuntimeError(
                f"Cannot sync username for user '{user.id}': username '{desired_username}' already exists."
            )

        user.username = desired_username
        user.save(update_fields=['username'])
        occupied_usernames.add(desired_username)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_moodle_id_primary_key'),
    ]

    operations = [
        migrations.RunPython(sync_usernames_to_primary_key, migrations.RunPython.noop),
    ]
