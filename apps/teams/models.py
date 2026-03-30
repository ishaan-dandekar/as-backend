from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Team(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('MEMBER', 'Member'),
        ('MODERATOR', 'Moderator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams_owned')
    members = models.ManyToManyField(User, related_name='teams_joined', blank=True)
    member_count = models.IntegerField(default=1)
    capacity = models.IntegerField(default=5)
    member_roles = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class JoinRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('team', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.team.name}"
