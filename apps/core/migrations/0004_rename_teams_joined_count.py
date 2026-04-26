from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_user_branch_year'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='teams_joined',
            new_name='teams_joined_count',
        ),
    ]
