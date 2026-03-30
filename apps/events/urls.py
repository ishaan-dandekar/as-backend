from django.urls import path
from . import views

urlpatterns = [
    path('', views.EventCreateListView.as_view(), name='event-list-create'),
    path('<uuid:event_id>/', views.EventDetailView.as_view(), name='event-detail'),
    path('<uuid:event_id>/register', views.EventRegisterView.as_view(), name='event-register'),
    path('<uuid:event_id>/unregister', views.EventUnregisterView.as_view(), name='event-unregister'),
]
