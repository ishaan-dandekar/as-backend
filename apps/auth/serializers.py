from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import get_user_profile_picture_url

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    unique_id = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    def get_unique_id(self, obj):
        return f"AS-{str(obj.id).split('-')[0].upper()}"

    def get_profile_picture_url(self, obj):
        return get_user_profile_picture_url(obj)

    class Meta:
        model = User
        fields = ['id', 'unique_id', 'username', 'email', 'first_name', 'last_name', 'profile_picture_url']
