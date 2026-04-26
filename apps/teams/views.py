from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError
from .models import Team, JoinRequest
from .serializers import TeamSerializer, JoinRequestSerializer, TeamMemberSerializer
from apps.core.discovery import extract_team_search_keywords

User = get_user_model()


class TeamCreateView(APIView):
    def get(self, request):
        """Get teams for authenticated user"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            search_query = (request.query_params.get('q') or '').strip().lower()
            teams = Team.objects.filter(members__id=request.user_id, is_active=True).distinct()
            if search_query:
                teams = [
                    team for team in teams
                    if search_query in ' '.join(extract_team_search_keywords(team.name, team.description))
                    or search_query in str(team.description or '').lower()
                    or search_query in str(team.name or '').lower()
                ]
            serializer = TeamSerializer(teams, many=True)
            return Response({'success': True, 'data': serializer.data})
        except (OperationalError, ProgrammingError):
            return Response({'success': True, 'data': []})

    def post(self, request):
        """Create a new team (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=request.user_id)
            name = request.data.get('name')
            description = request.data.get('description', '')
            capacity = request.data.get('capacity', 5)

            if not name:
                return Response({'success': False, 'message': 'Team name is required'}, status=status.HTTP_400_BAD_REQUEST)

            team = Team.objects.create(name=name, description=description, owner=user, capacity=capacity)
            team.members.add(user)
            team.member_roles[str(user.id)] = 'OWNER'
            team.save()

            return Response({'success': True, 'data': TeamSerializer(team).data}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class TeamDiscoverView(APIView):
    def get(self, request):
        """Get active teams the authenticated user is not part of."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            search_query = (request.query_params.get('q') or '').strip().lower()
            teams = Team.objects.filter(is_active=True).exclude(members__id=request.user_id).distinct()
            if search_query:
                teams = [
                    team for team in teams
                    if search_query in ' '.join(extract_team_search_keywords(team.name, team.description))
                    or search_query in str(team.description or '').lower()
                    or search_query in str(team.name or '').lower()
                ]
            serializer = TeamSerializer(teams, many=True)
            return Response({'success': True, 'data': serializer.data})
        except (OperationalError, ProgrammingError):
            return Response({'success': True, 'data': []})


class TeamDetailView(APIView):
    def get(self, request, team_id):
        """Get team details"""
        try:
            team = Team.objects.get(id=team_id)
            return Response({'success': True, 'data': TeamSerializer(team).data})
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, team_id):
        """Update team (owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            team = Team.objects.get(id=team_id)
            if str(team.owner.id) != str(request.user_id):
                return Response({'success': False, 'message': 'Only owner can update'}, status=status.HTTP_403_FORBIDDEN)

            serializer = TeamSerializer(team, data=request.data, partial=True)
            if serializer.is_valid():
                team = serializer.save()
                return Response({'success': True, 'data': TeamSerializer(team).data})
            return Response({'success': False, 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, team_id):
        """Delete team (owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            team = Team.objects.get(id=team_id)
            if str(team.owner.id) != str(request.user_id):
                return Response({'success': False, 'message': 'Only owner can delete'}, status=status.HTTP_403_FORBIDDEN)

            team.delete()
            return Response({'success': True, 'message': 'Team deleted successfully'})
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)


class TeamMemberRemoveView(APIView):
    def delete(self, request, team_id, user_id):
        """Remove a member from the team (owner only)."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(team.owner.id) != str(request.user_id):
            return Response({'success': False, 'message': 'Only owner can remove members'}, status=status.HTTP_403_FORBIDDEN)

        if str(team.owner.id) == str(user_id):
            return Response({'success': False, 'message': 'Team leader cannot be removed'}, status=status.HTTP_400_BAD_REQUEST)

        member = User.objects.filter(id=user_id).first()
        if not member or not team.members.filter(id=user_id).exists():
            return Response({'success': False, 'message': 'Member not found on this team'}, status=status.HTTP_404_NOT_FOUND)

        team.members.remove(member)
        team.member_roles.pop(str(user_id), None)
        team.member_count = team.members.count()
        team.save(update_fields=['member_roles', 'member_count', 'updated_at'])

        return Response({'success': True, 'message': 'Member removed successfully'})


class TeamJoinView(APIView):
    def post(self, request, team_id):
        """Request to join team (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            team = Team.objects.get(id=team_id)
            user = User.objects.get(id=request.user_id)
            message = request.data.get('message', '')

            if team.members.filter(id=user.id).exists():
                return Response({'success': False, 'message': 'Already a member of this team'}, status=status.HTTP_400_BAD_REQUEST)

            if JoinRequest.objects.filter(team=team, user=user).exists():
                return Response({'success': False, 'message': 'Join request already exists'}, status=status.HTTP_400_BAD_REQUEST)

            if team.member_count >= team.capacity:
                return Response({'success': False, 'message': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)

            join_request = JoinRequest.objects.create(team=team, user=user, message=message)
            return Response({'success': True, 'data': JoinRequestSerializer(join_request).data}, status=status.HTTP_201_CREATED)
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)


class TeamJoinRequestListView(APIView):
    def get(self, request):
        """Get pending join requests for teams owned by authenticated user."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        join_requests = JoinRequest.objects.filter(
            team__owner_id=request.user_id,
            status='PENDING',
            team__is_active=True,
        ).select_related('team', 'user').order_by('-created_at')

        items = []
        for join_request in join_requests:
            items.append({
                'id': str(join_request.id),
                'team_id': str(join_request.team.id),
                'team_name': join_request.team.name,
                'status': join_request.status,
                'message': join_request.message or '',
                'created_at': join_request.created_at,
                'user': TeamMemberSerializer(join_request.user).data,
            })

        return Response({'success': True, 'data': {'items': items, 'count': len(items)}})


class JoinRequestRespondView(APIView):
    def post(self, request, join_request_id):
        """Approve or reject a join request (team owner only)."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        action = str(request.data.get('action') or '').upper()
        if action not in ['APPROVE', 'REJECT']:
            return Response({'success': False, 'message': 'action must be APPROVE or REJECT'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            join_request = JoinRequest.objects.select_related('team', 'user').get(id=join_request_id)
        except JoinRequest.DoesNotExist:
            return Response({'success': False, 'message': 'Join request not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(join_request.team.owner.id) != str(request.user_id):
            return Response({'success': False, 'message': 'Only team owner can respond'}, status=status.HTTP_403_FORBIDDEN)

        if join_request.status != 'PENDING':
            return Response({'success': False, 'message': 'Request already processed'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'APPROVE':
            if join_request.team.member_count >= join_request.team.capacity:
                return Response({'success': False, 'message': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)

            if not join_request.team.members.filter(id=join_request.user.id).exists():
                join_request.team.members.add(join_request.user)
                join_request.team.member_roles[str(join_request.user.id)] = 'MEMBER'
                join_request.team.member_count = join_request.team.members.count()
                join_request.team.save(update_fields=['member_roles', 'member_count', 'updated_at'])

            join_request.status = 'APPROVED'
        else:
            join_request.status = 'REJECTED'

        join_request.save(update_fields=['status', 'updated_at'])

        return Response({'success': True, 'data': {'status': join_request.status}})


class JoinRequestApproveView(APIView):
    def post(self, request, join_request_id):
        """Legacy approve endpoint for backward compatibility."""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            join_request = JoinRequest.objects.select_related('team', 'user').get(id=join_request_id)
        except JoinRequest.DoesNotExist:
            return Response({'success': False, 'message': 'Join request not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(join_request.team.owner.id) != str(request.user_id):
            return Response({'success': False, 'message': 'Only team owner can approve'}, status=status.HTTP_403_FORBIDDEN)

        if join_request.status != 'PENDING':
            return Response({'success': False, 'message': 'Request already processed'}, status=status.HTTP_400_BAD_REQUEST)

        if join_request.team.member_count >= join_request.team.capacity:
            return Response({'success': False, 'message': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)

        if not join_request.team.members.filter(id=join_request.user.id).exists():
            join_request.team.members.add(join_request.user)
            join_request.team.member_roles[str(join_request.user.id)] = 'MEMBER'
            join_request.team.member_count = join_request.team.members.count()
            join_request.team.save(update_fields=['member_roles', 'member_count', 'updated_at'])

        join_request.status = 'APPROVED'
        join_request.save(update_fields=['status', 'updated_at'])

        return Response({'success': True, 'data': JoinRequestSerializer(join_request).data})
