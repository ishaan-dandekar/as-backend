from django.db import migrations, models


def infer_event_type(apps, schema_editor):
    Event = apps.get_model('events', 'Event')

    for event in Event.objects.all():
        joined_text = ' '.join(
            [
                str(event.title or ''),
                str(event.description or ''),
                ' '.join(str(tag or '') for tag in (event.tags or [])),
            ]
        ).lower()

        if 'hackathon' in joined_text:
            event.event_type = 'HACKATHON'
        elif 'workshop' in joined_text:
            event.event_type = 'WORKSHOP'
        elif 'meetup' in joined_text or 'orientation' in joined_text or 'seminar' in joined_text:
            event.event_type = 'MEETUP'
        else:
            event.event_type = 'OTHER'

        event.save(update_fields=['event_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('HACKATHON', 'Hackathon'),
                    ('WORKSHOP', 'Workshop'),
                    ('MEETUP', 'Meetup'),
                    ('OTHER', 'Other'),
                ],
                default='OTHER',
                max_length=20,
            ),
        ),
        migrations.RunPython(infer_event_type, migrations.RunPython.noop),
    ]
