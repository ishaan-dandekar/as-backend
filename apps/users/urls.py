from django.urls import path
from . import views

urlpatterns = [
    path('profile', views.UserProfileView.as_view(), name='user-profile'),
    path('github/oauth/start', views.GitHubOAuthStartView.as_view(), name='github-oauth-start'),
    path('github/oauth/callback', views.GitHubOAuthCallbackView.as_view(), name='github-oauth-callback'),
    path('github/oauth/stats', views.GitHubAuthorizedStatsView.as_view(), name='github-oauth-stats'),
    path('github/oauth/disconnect', views.GitHubOAuthDisconnectView.as_view(), name='github-oauth-disconnect'),
    path('github/<str:username>', views.GitHubStatsView.as_view(), name='github-stats'),
    path('search', views.UserSearchView.as_view(), name='user-search'),
    path('<str:user_id>', views.UserDetailView.as_view(), name='user-detail'),
]
