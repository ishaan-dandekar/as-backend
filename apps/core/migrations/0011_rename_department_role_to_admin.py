from django.db import migrations, models


def migrate_roles_forward(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(role='DEPARTMENT').update(role='ADMIN')


def migrate_roles_backward(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(role='ADMIN').update(role='DEPARTMENT')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_user_branch'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('STUDENT', 'Student'), ('ADMIN', 'Admin')],
                default='STUDENT',
                max_length=20,
            ),
        ),
    ]
