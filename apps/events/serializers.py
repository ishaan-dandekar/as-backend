from rest_framework import serializers
from .models import Event
from django.contrib.auth import get_user_model
from apps.users.models import get_user_profile_picture_url

User = get_user_model()


class EventOrganizerSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    def get_profile_picture_url(self, obj):
        return get_user_profile_picture_url(obj)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile_picture_url']


class EventSerializer(serializers.ModelSerializer):
    organizer = EventOrganizerSerializer(read_only=True)
    organizer_id = serializers.UUIDField(source='organizer.id', read_only=True)
    type = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'image_url', 'location', 'start_date', 'end_date',
                  'organizer', 'organizer_id', 'status', 'attendee_count', 'capacity', 'tags', 'type',
                  'is_registered', 'created_at', 'updated_at']

    def get_type(self, obj):
        joined_text = ' '.join(
            [
                str(obj.title or ''),
                str(obj.description or ''),
                ' '.join(str(tag or '') for tag in (obj.tags or [])),
            ]
        ).lower()

        if 'hackathon' in joined_text:
            return 'HACKATHON'
        if 'workshop' in joined_text:
            return 'WORKSHOP'
        if 'meetup' in joined_text or 'orientation' in joined_text or 'seminar' in joined_text:
            return 'MEETUP'
        return 'OTHER'

    def get_is_registered(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False
        return str(request.user_id) in (obj.attendees or [])
