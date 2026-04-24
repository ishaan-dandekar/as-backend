from django.urls import path
from . import views

urlpatterns = [
    path('', views.TeamCreateView.as_view(), name='team-create'),
    path('discover/', views.TeamDiscoverView.as_view(), name='team-discover'),
    path('join-requests/', views.TeamJoinRequestListView.as_view(), name='team-join-request-list'),
    path('join-request/<uuid:join_request_id>/respond', views.JoinRequestRespondView.as_view(), name='team-join-request-respond'),
    path('<uuid:team_id>/', views.TeamDetailView.as_view(), name='team-detail'),
    path('<uuid:team_id>/join', views.TeamJoinView.as_view(), name='team-join'),
    path('join-request/<uuid:join_request_id>/approve', views.JoinRequestApproveView.as_view(), name='join-request-approve'),
]
