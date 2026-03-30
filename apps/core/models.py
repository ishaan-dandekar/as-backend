from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    USER_ROLE_CHOICES = [
        ('USER', 'User'),
        ('ADMIN', 'Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    skills = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    github_username = models.CharField(max_length=100, blank=True, null=True)
    leetcode_username = models.CharField(max_length=100, blank=True, null=True)
    projects_created = models.IntegerField(default=0)
    projects_completed = models.IntegerField(default=0)
    teams_joined = models.IntegerField(default=0)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default='USER')
    is_active_custom = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Override groups and user_permissions to avoid conflicts with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_user_groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_user_permissions',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.username
