from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Project(models.Model):
    PROJECT_STATUS_CHOICES = [
        ('LOOKING_FOR_TEAMMATES', 'Looking For Teammates'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ACTIVE', 'Active'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.URLField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    tech_stack = models.JSONField(default=list)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    status = models.CharField(max_length=25, choices=PROJECT_STATUS_CHOICES, default='LOOKING_FOR_TEAMMATES')
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    team_member_count = models.IntegerField(default=0)
    team_capacity = models.IntegerField(default=0)
    github_url = models.URLField(blank=True, null=True)
    live_url = models.URLField(blank=True, null=True)
    bookmarked_by = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
