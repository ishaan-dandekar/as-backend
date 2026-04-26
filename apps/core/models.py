from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    BRANCH_CHOICES = [
        ('CE', 'CE'),
        ('IT', 'IT'),
        ('AI-ML', 'AI-ML'),
        ('DS', 'DS'),
        ('Civil', 'Civil'),
        ('Mechanical', 'Mechanical'),
    ]

    YEAR_CHOICES = [
        ('FE', 'FE'),
        ('SE', 'SE'),
        ('TE', 'TE'),
        ('BE', 'BE'),
    ]

    USER_ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('DEPARTMENT', 'Department'),
    ]

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    email = models.EmailField(unique=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    branch = models.CharField(max_length=20, choices=BRANCH_CHOICES, blank=True, null=True)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES, blank=True, null=True)
    skills = models.JSONField(default=list, blank=True)
    interests = models.JSONField(default=list, blank=True)
    github_username = models.CharField(max_length=100, blank=True, null=True)
    leetcode_username = models.CharField(max_length=100, blank=True, null=True)
    projects_created = models.IntegerField(default=0)
    projects_completed = models.IntegerField(default=0)
    teams_joined_count = models.IntegerField(default=0)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default='STUDENT')
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

    @staticmethod
    def derive_moodle_id(username, email, fallback=''):
        username_value = (username or '').strip()
        email_value = (email or '').strip().lower()

        if username_value.isdigit():
            return username_value

        local_part = email_value.split('@')[0] if '@' in email_value else ''
        if local_part.isdigit():
            return local_part

        if local_part:
            return local_part

        if username_value:
            return username_value

        return (fallback or '').strip()

    @classmethod
    def derive_login_identifier(cls, username, email, fallback=''):
        return cls.derive_moodle_id(username, email, fallback=fallback)

    def save(self, *args, **kwargs):
        canonical_id = self.derive_moodle_id(self.username, self.email, fallback=str(self.id or ''))
        if not self.id and canonical_id:
            self.id = canonical_id

        if canonical_id and (not self.username or '@' in self.username):
            self.username = self.derive_login_identifier(self.username, self.email, fallback=canonical_id)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
