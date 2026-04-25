from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Event
from .serializers import EventSerializer

User = get_user_model()


def _get_authenticated_user(request):
    if not hasattr(request, 'user_id'):
        return None, Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        return User.objects.get(id=request.user_id), None
    except User.DoesNotExist:
        return None, Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


def _ensure_department_user(user):
    if getattr(user, 'role', '').upper() not in {'DEPARTMENT', 'ADMIN'}:
        return Response(
            {'success': False, 'message': 'Only department users can manage events'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


class EventCreateListView(APIView):
    def get(self, request):
        """List all events with optional filtering"""
        status_filter = request.query_params.get('status', '')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))

        events = Event.objects.all()

        if status_filter:
            events = events.filter(status=status_filter)

        total = events.count()
        start = (page - 1) * limit
        end = start + limit
        events = events[start:end]

        serializer = EventSerializer(events, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })

    def post(self, request):
        """Create a new event (authenticated)"""
        user, error_response = _get_authenticated_user(request)
        if error_response:
            return error_response

        role_error = _ensure_department_user(user)
        if role_error:
            return role_error

        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(organizer=user, attendees=[str(user.id)], attendee_count=1)
            return Response(
                {'success': True, 'data': EventSerializer(event, context={'request': request}).data},
                status=status.HTTP_201_CREATED,
            )
        return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class EventDetailView(APIView):
    def get(self, request, event_id):
        """Get event details"""
        try:
            event = Event.objects.get(id=event_id)
            return Response({'success': True, 'data': EventSerializer(event, context={'request': request}).data})
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, event_id):
        """Update event (organizer only)"""
        user, error_response = _get_authenticated_user(request)
        if error_response:
            return error_response

        role_error = _ensure_department_user(user)
        if role_error:
            return role_error

        try:
            event = Event.objects.get(id=event_id)
            if str(event.organizer.id) != str(user.id):
                return Response({'success': False, 'message': 'Only organizer can update'}, status=status.HTTP_403_FORBIDDEN)

            serializer = EventSerializer(event, data=request.data, partial=True)
            if serializer.is_valid():
                event = serializer.save()
                return Response({'success': True, 'data': EventSerializer(event, context={'request': request}).data})
            return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, event_id):
        """Delete event (organizer only)"""
        user, error_response = _get_authenticated_user(request)
        if error_response:
            return error_response

        role_error = _ensure_department_user(user)
        if role_error:
            return role_error

        try:
            event = Event.objects.get(id=event_id)
            if str(event.organizer.id) != str(user.id):
                return Response({'success': False, 'message': 'Only organizer can delete'}, status=status.HTTP_403_FORBIDDEN)

            event.delete()
            return Response({'success': True, 'message': 'Event deleted successfully'})
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)


class EventRegisterView(APIView):
    def post(self, request, event_id):
        """Register for event (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            event = Event.objects.get(id=event_id)
            user_id_str = str(request.user_id)

            if user_id_str in event.attendees:
                return Response({'success': False, 'message': 'Already registered for this event'}, status=status.HTTP_400_BAD_REQUEST)

            if event.attendee_count >= event.capacity:
                return Response({'success': False, 'message': 'Event is full'}, status=status.HTTP_400_BAD_REQUEST)

            event.attendees.append(user_id_str)
            event.attendee_count += 1
            event.save()

            return Response({'success': True, 'data': EventSerializer(event, context={'request': request}).data})
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)


class EventUnregisterView(APIView):
    def post(self, request, event_id):
        """Unregister from event (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            event = Event.objects.get(id=event_id)
            user_id_str = str(request.user_id)

            if user_id_str not in event.attendees:
                return Response({'success': False, 'message': 'Not registered for this event'}, status=status.HTTP_400_BAD_REQUEST)

            event.attendees.remove(user_id_str)
            event.attendee_count -= 1
            event.save()

            return Response({'success': True, 'data': EventSerializer(event, context={'request': request}).data})
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
