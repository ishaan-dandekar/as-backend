from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Project
from .serializers import ProjectSerializer
from django.db.models import Q
from apps.notifications.models import Notification
from apps.core.discovery import infer_project_domains

User = get_user_model()


def _normalized_tokens(values):
    tokens = set()
    for value in values or []:
        normalized = str(value or '').strip().lower()
        if normalized:
            tokens.add(normalized)
    return tokens


def _normalize_github_repo_url(value):
    return str(value or '').strip().rstrip('/').lower()


def _find_existing_owned_project(user, payload):
    github_url = _normalize_github_repo_url(
        payload.get('github_url') or payload.get('githubUrl')
    )
    title = str(payload.get('title') or '').strip()
    owned_projects = Project.objects.filter(owner=user).order_by('-updated_at')

    if github_url:
        for project in owned_projects.exclude(github_url__isnull=True).exclude(github_url=''):
            if _normalize_github_repo_url(project.github_url) == github_url:
                return project

    if title:
        fallback_project = owned_projects.filter(title__iexact=title).first()
        if fallback_project:
            return fallback_project

    return None


def _project_recommendation_score(user, project):
    score = 0
    user_skill_tokens = _normalized_tokens(getattr(user, 'skills', []))
    project_skill_tokens = _normalized_tokens(getattr(project, 'tech_stack', []))

    tech_overlap = len(user_skill_tokens.intersection(project_skill_tokens))
    score += tech_overlap * 5

    if getattr(user, 'branch', None) and getattr(project.owner, 'branch', None) and user.branch == project.owner.branch:
        score += 3

    if getattr(user, 'year', None) and getattr(project.owner, 'year', None) and user.year == project.owner.year:
        score += 2

    if (project.team_capacity or 0) > (project.team_member_count or 0):
        score += 4
    elif project.status == 'LOOKING_FOR_TEAMMATES':
        score += 2

    if project.status == 'ACTIVE':
        score += 2
    elif project.status == 'LOOKING_FOR_TEAMMATES':
        score += 3

    return score


class ProjectCreateListView(APIView):
    def get(self, request):
        """List all projects with optional filtering"""
        query = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', '')
        tech_stack = request.query_params.get('techStack', '')
        domains = request.query_params.getlist('domains') or request.query_params.getlist('domain')
        if not domains:
            raw_domains = request.query_params.get('domains', '') or request.query_params.get('domain', '')
            domains = [item.strip() for item in str(raw_domains).split(',') if item.strip()]
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 10))

        projects = Project.objects.select_related('owner').all()

        if query:
            projects = projects.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if status_filter:
            projects = projects.filter(status=status_filter)
        if tech_stack:
            tech_list = tech_stack.split(',')
            for tech in tech_list:
                projects = projects.filter(tech_stack__contains=tech)

        if domains:
            requested_domains = {str(item).strip().lower() for item in domains if str(item).strip()}
            filtered_projects = []
            for project in projects:
                project_domains = {
                    tag.lower()
                    for tag in infer_project_domains(project.title, project.description, project.tech_stack)
                }
                if project_domains.intersection(requested_domains):
                    filtered_projects.append(project)
            projects = filtered_projects
        else:
            projects = list(projects)

        total = len(projects)
        start = (page - 1) * limit
        end = start + limit
        projects = projects[start:end]

        serializer = ProjectSerializer(projects, many=True, context={'request': request})
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
        """Create a new project (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=request.user_id)
            existing_project = _find_existing_owned_project(user, request.data)
            if existing_project:
                serializer = ProjectSerializer(existing_project, data=request.data, partial=True)
                if serializer.is_valid():
                    project = serializer.save()
                    return Response({'success': True, 'data': ProjectSerializer(project, context={'request': request}).data})
                return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            serializer = ProjectSerializer(data=request.data)
            if serializer.is_valid():
                project = serializer.save(owner=user)
                return Response({'success': True, 'data': ProjectSerializer(project, context={'request': request}).data}, status=status.HTTP_201_CREATED)
            return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class ProjectDetailView(APIView):
    def get(self, request, project_id):
        """Get project details"""
        try:
            project = Project.objects.get(id=project_id)
            serializer = ProjectSerializer(project, context={'request': request})
            return Response({'success': True, 'data': serializer.data})
        except Project.DoesNotExist:
            return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, project_id):
        """Update project (owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = Project.objects.get(id=project_id)
            if str(project.owner.id) != str(request.user_id):
                return Response({'success': False, 'message': 'Only owner can update'}, status=status.HTTP_403_FORBIDDEN)

            serializer = ProjectSerializer(project, data=request.data, partial=True)
            if serializer.is_valid():
                project = serializer.save()
                return Response({'success': True, 'data': ProjectSerializer(project, context={'request': request}).data})
            return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Project.DoesNotExist:
            return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, project_id):
        """Delete project (owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = Project.objects.get(id=project_id)
            if str(project.owner.id) != str(request.user_id):
                return Response({'success': False, 'message': 'Only owner can delete'}, status=status.HTTP_403_FORBIDDEN)

            project.delete()
            return Response({'success': True, 'message': 'Project deleted successfully'})
        except Project.DoesNotExist:
            return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)


class ProjectBookmarkView(APIView):
    def post(self, request, project_id):
        """Toggle bookmark on project (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = Project.objects.get(id=project_id)
            user_id_str = str(request.user_id)

            if user_id_str in project.bookmarked_by:
                project.bookmarked_by.remove(user_id_str)
            else:
                project.bookmarked_by.append(user_id_str)

            project.save()
            serializer = ProjectSerializer(project, context={'request': request})
            return Response({'success': True, 'data': serializer.data, 'is_bookmarked': user_id_str in project.bookmarked_by})
        except Project.DoesNotExist:
            return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)


class UserProjectsView(APIView):
    def get(self, request):
        """Get user's projects (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            projects = Project.objects.filter(owner_id=request.user_id)
            serializer = ProjectSerializer(projects, many=True, context={'request': request})
            return Response({'success': True, 'data': serializer.data})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PublicUserProjectsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, user_id):
        """Get projects for a specific user (public), optionally filtered by status"""
        status_filter = request.query_params.get('status', '')

        projects = Project.objects.filter(owner_id=user_id)
        if status_filter:
            projects = projects.filter(status=status_filter)

        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class RecommendedProjectsView(APIView):
    def get(self, request):
        """Return backend-ranked project recommendations for the authenticated user."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        projects = (
            Project.objects.select_related('owner')
            .exclude(owner_id=request.user_id)
            .exclude(owner__role__in=['DEPARTMENT', 'ADMIN'])
            .exclude(status='COMPLETED')
        )

        ranked = []
        for project in projects:
            score = _project_recommendation_score(user, project)
            updated_ts = project.updated_at.timestamp() if project.updated_at else 0
            ranked.append({
                'project': project,
                'score': score,
                'updated_ts': updated_ts,
            })

        ranked.sort(key=lambda item: (item['score'], item['updated_ts']), reverse=True)

        positive_matches = [item['project'] for item in ranked if item['score'] > 0]
        if positive_matches:
            selected_projects = positive_matches[:8]
        else:
            selected_projects = [item['project'] for item in ranked[:8]]

        serializer = ProjectSerializer(selected_projects, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class ProjectRequestToJoinView(APIView):
    def post(self, request, project_id):
        """Request to join/work on a project (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        requester_id = str(request.user_id)
        if str(project.owner_id) == requester_id:
            return Response({'success': False, 'message': 'You already own this project'}, status=status.HTTP_400_BAD_REQUEST)

        requester = User.objects.filter(id=request.user_id).first()
        if not requester:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        existing_requests = Notification.objects.filter(
            user=project.owner,
            type='JOIN_REQUEST',
            related_id=str(project.id),
            related_type='PROJECT',
        )
        for notification in existing_requests:
            metadata = notification.metadata or {}
            if (
                str(metadata.get('requester_id')) == requester_id
                and metadata.get('status', 'PENDING') == 'PENDING'
            ):
                return Response({'success': False, 'message': 'Request already submitted'}, status=status.HTTP_400_BAD_REQUEST)

        message = str(request.data.get('message') or '').strip()

        Notification.objects.create(
            user=project.owner,
            type='JOIN_REQUEST',
            title='New project join request',
            message=f"{requester.first_name or requester.username} requested to work on {project.title}",
            related_id=str(project.id),
            related_type='PROJECT',
            metadata={
                'project_id': str(project.id),
                'project_title': project.title,
                'requester_id': requester_id,
                'requester_name': requester.first_name or requester.username,
                'requester_email': requester.email,
                'request_message': message,
                'status': 'PENDING',
            },
        )

        return Response({'success': True, 'data': {'requested': True}, 'message': 'Request submitted successfully'})


class ProjectJoinRequestListView(APIView):
    def get(self, request):
        """Get incoming join requests for projects owned by authenticated user"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        notifications = Notification.objects.filter(
            user_id=request.user_id,
            type='JOIN_REQUEST',
            related_type='PROJECT',
        ).order_by('-created_at')

        items = []
        for notification in notifications:
            metadata = notification.metadata or {}
            items.append({
                'id': str(notification.id),
                'project_id': metadata.get('project_id') or notification.related_id,
                'project_title': metadata.get('project_title') or 'Project',
                'requester_id': metadata.get('requester_id'),
                'requester_name': metadata.get('requester_name') or 'Unknown User',
                'requester_email': metadata.get('requester_email') or '',
                'message': metadata.get('request_message') or '',
                'status': metadata.get('status', 'PENDING'),
                'created_at': notification.created_at,
            })

        pending_count = sum(1 for item in items if item.get('status') == 'PENDING')
        return Response({'success': True, 'data': {'items': items, 'pending_count': pending_count}})


class ProjectJoinRequestRespondView(APIView):
    def post(self, request, request_id):
        """Accept or reject a join request (project owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        action = str(request.data.get('action') or '').upper()
        if action not in ['ACCEPT', 'REJECT']:
            return Response({'success': False, 'message': 'action must be ACCEPT or REJECT'}, status=status.HTTP_400_BAD_REQUEST)

        notification = Notification.objects.filter(
            id=request_id,
            user_id=request.user_id,
            type='JOIN_REQUEST',
            related_type='PROJECT',
        ).first()

        if not notification:
            return Response({'success': False, 'message': 'Join request not found'}, status=status.HTTP_404_NOT_FOUND)

        metadata = notification.metadata or {}
        if metadata.get('status', 'PENDING') != 'PENDING':
            return Response({'success': False, 'message': 'Request already processed'}, status=status.HTTP_400_BAD_REQUEST)

        requester_id = metadata.get('requester_id')
        project_id = metadata.get('project_id') or notification.related_id
        project_title = metadata.get('project_title') or 'project'

        requester = User.objects.filter(id=requester_id).first() if requester_id else None
        project = Project.objects.filter(id=project_id).first() if project_id else None

        if action == 'ACCEPT':
            if not requester:
                return Response({'success': False, 'message': 'Requester not found'}, status=status.HTTP_404_NOT_FOUND)

            if not project:
                return Response({'success': False, 'message': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

            team = project.team
            if not team:
                team_capacity = project.team_capacity if (project.team_capacity or 0) > 0 else 5
                team = Team.objects.create(
                    name=f"{project.title} Team",
                    description=f"Team for {project.title}",
                    owner=project.owner,
                    capacity=team_capacity,
                    member_count=1,
                )
                team.members.add(project.owner)
                team.member_roles[str(project.owner.id)] = 'OWNER'
                team.save(update_fields=['member_roles'])
                project.team = team

            if not team.members.filter(id=requester.id).exists():
                if team.member_count >= team.capacity:
                    return Response({'success': False, 'message': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)

                team.members.add(requester)
                team.member_roles[str(requester.id)] = 'MEMBER'
                team.member_count = team.members.count()
                team.save(update_fields=['member_roles', 'member_count', 'updated_at'])

            project.team_member_count = team.member_count
            if (project.team_capacity or 0) <= 0:
                project.team_capacity = team.capacity
            project.save(update_fields=['team', 'team_member_count', 'team_capacity', 'updated_at'])

        metadata['status'] = 'ACCEPTED' if action == 'ACCEPT' else 'REJECTED'
        notification.metadata = metadata
        notification.is_read = True
        notification.save(update_fields=['metadata', 'is_read', 'updated_at'])

        if requester_id:
            response_type = 'JOIN_APPROVED' if action == 'ACCEPT' else 'JOIN_REJECTED'
            response_title = 'Project request approved' if action == 'ACCEPT' else 'Project request rejected'
            response_message = (
                f"Your request to join {project_title} was approved."
                if action == 'ACCEPT'
                else f"Your request to join {project_title} was rejected."
            )

            Notification.objects.create(
                user_id=requester_id,
                type=response_type,
                title=response_title,
                message=response_message,
                related_id=str(project_id) if project_id else None,
                related_type='PROJECT',
                metadata={
                    'project_id': project_id,
                    'project_title': project_title,
                    'status': metadata['status'],
                },
            )

        return Response({'success': True, 'data': {'status': metadata['status']}})
