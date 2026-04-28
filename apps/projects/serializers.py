from rest_framework import serializers
from .models import Project
from django.contrib.auth import get_user_model
from apps.users.models import get_user_profile_picture_url
from apps.core.discovery import infer_project_domains
from apps.notifications.models import Notification

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
    domain_tags = serializers.SerializerMethodField()
    current_user_join_state = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'thumbnail_url', 'images', 'tech_stack', 'domain_tags', 'owner',
                  'status', 'team', 'team_member_count', 'team_capacity', 'github_url', 'live_url',
                  'is_bookmarked', 'current_user_join_state', 'created_at', 'updated_at']

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_id'):
            return str(request.user_id) in obj.bookmarked_by
        return False

    def get_domain_tags(self, obj):
        return infer_project_domains(obj.title, obj.description, obj.tech_stack)

    def get_current_user_join_state(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return 'IDLE'

        current_user_id = str(request.user_id)
        if str(getattr(obj.owner, 'id', '')) == current_user_id:
            return 'OWNER'

        if obj.team and obj.team.members.filter(id=current_user_id).exists():
            return 'JOINED'

        existing_requests = Notification.objects.filter(
            user=obj.owner,
            type='JOIN_REQUEST',
            related_id=str(obj.id),
            related_type='PROJECT',
        )

        for notification in existing_requests:
            metadata = notification.metadata or {}
            if (
                str(metadata.get('requester_id')) == current_user_id
                and metadata.get('status', 'PENDING') == 'PENDING'
            ):
                return 'REQUEST_PENDING'

        return 'IDLE'
