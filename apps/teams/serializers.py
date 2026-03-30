from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Team, JoinRequest
from apps.users.models import get_user_profile_picture_url

User = get_user_model()


class TeamMemberSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    def get_profile_picture_url(self, obj):
        return get_user_profile_picture_url(obj)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile_picture_url']


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'members', 'member_count', 'capacity', 'created_at', 'updated_at']


class JoinRequestSerializer(serializers.ModelSerializer):
    user = TeamMemberSerializer(read_only=True)

    class Meta:
        model = JoinRequest
        fields = ['id', 'team', 'user', 'status', 'message', 'created_at']
