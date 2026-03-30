from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError
from .models import Team, JoinRequest
from .serializers import TeamSerializer, JoinRequestSerializer

User = get_user_model()


class TeamCreateView(APIView):
    def get(self, request):
        """Get teams for authenticated user"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            teams = Team.objects.filter(members__id=request.user_id, is_active=True).distinct()
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

            join_request = JoinRequest.objects.create(team=team, user=user, message=message)
            return Response({'success': True, 'data': JoinRequestSerializer(join_request).data}, status=status.HTTP_201_CREATED)
        except Team.DoesNotExist:
            return Response({'success': False, 'message': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)


class JoinRequestApproveView(APIView):
    def post(self, request, join_request_id):
        """Approve join request (team owner only)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            join_request = JoinRequest.objects.get(id=join_request_id)
            if str(join_request.team.owner.id) != str(request.user_id):
                return Response({'success': False, 'message': 'Only team owner can approve'}, status=status.HTTP_403_FORBIDDEN)

            if join_request.team.member_count >= join_request.team.capacity:
                return Response({'success': False, 'message': 'Team is full'}, status=status.HTTP_400_BAD_REQUEST)

            join_request.team.members.add(join_request.user)
            join_request.team.member_count += 1
            join_request.team.member_roles[str(join_request.user.id)] = 'MEMBER'
            join_request.team.save()

            join_request.status = 'APPROVED'
            join_request.save()

            return Response({'success': True, 'data': JoinRequestSerializer(join_request).data})
        except JoinRequest.DoesNotExist:
            return Response({'success': False, 'message': 'Join request not found'}, status=status.HTTP_404_NOT_FOUND)
