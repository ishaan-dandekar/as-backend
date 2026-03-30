"""
Main URL Configuration for Project Hub API
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        'message': 'APSIT Student Sphere API',
        'endpoints': {
            'auth': request.build_absolute_uri('/api/auth/'),
            'user': request.build_absolute_uri('/api/user/'),
            'projects': request.build_absolute_uri('/api/projects/'),
            'teams': request.build_absolute_uri('/api/teams/'),
            'events': request.build_absolute_uri('/api/events/'),
            'notifications': request.build_absolute_uri('/api/notifications/'),
            'health': request.build_absolute_uri('/api/health/'),
        }
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/auth/', include('apps.auth.urls')),
    path('api/user/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/teams/', include('apps.teams.urls')),
    path('api/events/', include('apps.events.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/health/', include('apps.core.urls')),
]
