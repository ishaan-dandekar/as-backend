from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_user_admission_year_alter_user_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='branch',
            field=models.CharField(
                blank=True,
                choices=[
                    ('Civil', 'Civil'),
                    ('Computer Engineering', 'Computer Engineering'),
                    ('EXTC (Discontinued)', 'EXTC (Discontinued)'),
                    ('IT', 'IT'),
                    ('Mechanical', 'Mechanical'),
                    ('AIML', 'AIML'),
                    ('Data Science', 'Data Science'),
                ],
                max_length=32,
                null=True,
            ),
        ),
    ]
