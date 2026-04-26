from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Team, JoinRequest
from apps.users.models import get_user_profile_picture_url
from apps.core.discovery import extract_team_search_keywords

User = get_user_model()


class TeamMemberSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    moodle_id = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    def get_profile_picture_url(self, obj):
        return get_user_profile_picture_url(obj)

    def get_moodle_id(self, obj):
        username = (obj.username or '').strip()
        email = (obj.email or '').strip().lower()

        if username.isdigit():
            return username

        local_part = email.split('@')[0] if '@' in email else ''
        if local_part.isdigit():
            return local_part

        return username or str(obj.id)

    def get_role(self, obj):
        member_roles = self.context.get('member_roles', {})
        return member_roles.get(str(obj.id), 'MEMBER')

    def get_name(self, obj):
        full_name = ' '.join(
            part.strip()
            for part in [getattr(obj, 'first_name', ''), getattr(obj, 'last_name', '')]
            if part and part.strip()
        ).strip()

        if full_name:
            return full_name

        first_name = (getattr(obj, 'first_name', '') or '').strip()
        if first_name:
            return first_name

        username = (obj.username or '').strip()
        email = (obj.email or '').strip()
        if '@' in username and email:
            return email.split('@')[0]

        return username or email or str(obj.id)

    class Meta:
        model = User
        fields = ['id', 'moodle_id', 'name', 'username', 'email', 'profile_picture_url', 'role']


class TeamSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    owner_id = serializers.CharField(source='owner.id', read_only=True)
    search_keywords = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    def get_members(self, obj):
        serializer = TeamMemberSerializer(
            obj.members.all(),
            many=True,
            context={'member_roles': obj.member_roles or {}},
        )
        return serializer.data

    def get_search_keywords(self, obj):
        return extract_team_search_keywords(obj.name, obj.description)

    def get_project(self, obj):
        project = obj.projects.order_by('-updated_at').first()
        return str(project.id) if project else None

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'owner_id', 'project', 'members', 'member_count', 'capacity', 'search_keywords', 'created_at', 'updated_at']


class JoinRequestSerializer(serializers.ModelSerializer):
    user = TeamMemberSerializer(read_only=True)

    class Meta:
        model = JoinRequest
        fields = ['id', 'team', 'user', 'status', 'message', 'created_at']
