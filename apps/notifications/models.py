from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('PROJECT_INVITE', 'Project Invite'),
        ('TEAM_INVITE', 'Team Invite'),
        ('JOIN_REQUEST', 'Join Request'),
        ('JOIN_APPROVED', 'Join Approved'),
        ('JOIN_REJECTED', 'Join Rejected'),
        ('TEAM_UPDATE', 'Team Update'),
        ('PROJECT_UPDATE', 'Project Update'),
        ('EVENT_REMINDER', 'Event Reminder'),
        ('MESSAGE', 'Message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=25, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_id = models.CharField(max_length=255, blank=True, null=True)
    related_type = models.CharField(max_length=50, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username}"
