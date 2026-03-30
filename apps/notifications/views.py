from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()


class NotificationListView(APIView):
    def get(self, request):
        """Get notifications (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        unread_only = request.query_params.get('unreadOnly', 'false').lower() == 'true'
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))

        notifications = Notification.objects.filter(user_id=request.user_id)

        if unread_only:
            notifications = notifications.filter(is_read=False)

        total = notifications.count()
        start = (page - 1) * limit
        end = start + limit
        notifications = notifications[start:end]

        serializer = NotificationSerializer(notifications, many=True)
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


class NotificationMarkReadView(APIView):
    def patch(self, request, notification_id):
        """Mark notification as read (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            notification = Notification.objects.get(id=notification_id, user_id=request.user_id)
            notification.is_read = True
            notification.save()
            return Response({'success': True, 'data': NotificationSerializer(notification).data})
        except Notification.DoesNotExist:
            return Response({'success': False, 'message': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    def post(self, request):
        """Mark all notifications as read (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        Notification.objects.filter(user_id=request.user_id, is_read=False).update(is_read=True)
        return Response({'success': True, 'message': 'All notifications marked as read'})


class NotificationDeleteView(APIView):
    def delete(self, request, notification_id):
        """Delete notification (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            notification = Notification.objects.get(id=notification_id, user_id=request.user_id)
            notification.delete()
            return Response({'success': True, 'message': 'Notification deleted'})
        except Notification.DoesNotExist:
            return Response({'success': False, 'message': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationUnreadCountView(APIView):
    def get(self, request):
        """Get unread notification count (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        count = Notification.objects.filter(user_id=request.user_id, is_read=False).count()
        return Response({'success': True, 'data': {'unread_count': count}})
