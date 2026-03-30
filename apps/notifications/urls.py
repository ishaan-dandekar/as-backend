from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<uuid:notification_id>/read', views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('read-all', views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('<uuid:notification_id>/', views.NotificationDeleteView.as_view(), name='notification-delete'),
    path('unread-count/', views.NotificationUnreadCountView.as_view(), name='notification-unread-count'),
]
