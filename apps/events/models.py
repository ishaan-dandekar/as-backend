from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('HACKATHON', 'Hackathon'),
        ('WORKSHOP', 'Workshop'),
        ('MEETUP', 'Meetup'),
        ('OTHER', 'Other'),
    ]

    EVENT_STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='OTHER')
    status = models.CharField(max_length=20, choices=EVENT_STATUS_CHOICES, default='UPCOMING')
    attendees = models.JSONField(default=list, blank=True)
    attendee_count = models.IntegerField(default=0)
    capacity = models.IntegerField(default=100)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.title
