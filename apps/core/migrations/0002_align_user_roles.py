from django.db import migrations, models


def migrate_roles_forward(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(role='USER').update(role='STUDENT')
    User.objects.filter(role='ADMIN').update(role='DEPARTMENT')


def migrate_roles_backward(apps, schema_editor):
    User = apps.get_model('core', 'User')
    User.objects.filter(role='STUDENT').update(role='USER')
    User.objects.filter(role='DEPARTMENT').update(role='ADMIN')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('STUDENT', 'Student'), ('DEPARTMENT', 'Department')],
                default='STUDENT',
                max_length=20,
            ),
        ),
    ]
