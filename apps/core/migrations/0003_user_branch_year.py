from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_align_user_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='branch',
            field=models.CharField(
                blank=True,
                choices=[
                    ('CE', 'CE'),
                    ('IT', 'IT'),
                    ('AI-ML', 'AI-ML'),
                    ('DS', 'DS'),
                    ('Civil', 'Civil'),
                    ('Mechanical', 'Mechanical'),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='year',
            field=models.CharField(
                blank=True,
                choices=[('FE', 'FE'), ('SE', 'SE'), ('TE', 'TE'), ('BE', 'BE')],
                max_length=2,
                null=True,
            ),
        ),
    ]
