from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Health check endpoint"""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({
            'success': True,
            'message': 'Server is running',
            'status': 'OK'
        })
