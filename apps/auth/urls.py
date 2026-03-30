from django.urls import path
from . import views

urlpatterns = [
    path('google/start', views.GoogleOAuthStartView.as_view(), name='google-oauth-start'),
    path('google/callback', views.GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
    path('refresh', views.RefreshTokenView.as_view(), name='refresh'),
    path('logout', views.LogoutView.as_view(), name='logout'),
]
