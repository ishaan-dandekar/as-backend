from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProjectCreateListView.as_view(), name='project-list-create'),
    path('by-user/<uuid:user_id>/', views.PublicUserProjectsView.as_view(), name='project-by-user-public'),
    path('join-requests/', views.ProjectJoinRequestListView.as_view(), name='project-join-request-list'),
    path('join-requests/<uuid:request_id>/respond', views.ProjectJoinRequestRespondView.as_view(), name='project-join-request-respond'),
    path('<uuid:project_id>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('<uuid:project_id>/bookmark', views.ProjectBookmarkView.as_view(), name='project-bookmark'),
    path('<uuid:project_id>/request', views.ProjectRequestToJoinView.as_view(), name='project-request-to-join'),
    path('my-projects/', views.UserProjectsView.as_view(), name='user-projects'),
]
