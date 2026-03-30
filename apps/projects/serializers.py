from rest_framework import serializers
from .models import Project
from django.contrib.auth import get_user_model
from apps.users.models import get_user_profile_picture_url

User = get_user_model()


class ProjectOwnerSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    def get_profile_picture_url(self, obj):
        return get_user_profile_picture_url(obj)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile_picture_url']


class ProjectSerializer(serializers.ModelSerializer):
    owner = ProjectOwnerSerializer(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'thumbnail_url', 'images', 'tech_stack', 'owner',
                  'status', 'team', 'team_member_count', 'team_capacity', 'github_url', 'live_url',
                  'is_bookmarked', 'created_at', 'updated_at']

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_id'):
            return str(request.user_id) in obj.bookmarked_by
        return False
