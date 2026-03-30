from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from apps.core.authentication import generate_tokens
from apps.users.models import get_user_profile_picture_url, set_user_profile_picture_url
from urllib.parse import urlencode
import requests
import json
import jwt

User = get_user_model()

ALLOWED_EMAIL_DOMAIN = 'apsit.edu.in'


class GoogleOAuthStartView(APIView):
    """Returns the Google OAuth authorization URL for the frontend to open."""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            return Response(
                {'success': False, 'message': 'Google OAuth is not configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = urlencode({
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'select_account',
            'hd': ALLOWED_EMAIL_DOMAIN,  # hints Google to show only APSIT accounts
        })

        return Response({
            'success': True,
            'data': {
                'authorizationUrl': f'https://accounts.google.com/o/oauth2/v2/auth?{params}',
            },
        })


class GoogleOAuthCallbackView(APIView):
    """Handles the OAuth callback from Google. Exchanges code for tokens, fetches profile,
    finds or creates the user, and returns JWT tokens via postMessage to the frontend popup."""
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        frontend_origin = settings.FRONTEND_APP_URL.rstrip('/')

        if error:
            return self._redirect_result('error', f'Google sign-in was cancelled or failed: {error}', frontend_origin)

        if not code:
            return self._redirect_result('error', 'Missing authorization code from Google.', frontend_origin)

        # Exchange code for tokens
        try:
            token_resp = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
                },
                timeout=20,
            )
            token_data = token_resp.json()
        except Exception:
            return self._redirect_result('error', 'Failed to communicate with Google. Please try again.', frontend_origin)

        if token_resp.status_code != 200 or 'access_token' not in token_data:
            error_desc = token_data.get('error_description', token_data.get('error', 'Unknown error'))
            return self._redirect_result('error', f'Google token exchange failed: {error_desc}', frontend_origin)

        access_token = token_data['access_token']

        # Fetch user profile from Google
        try:
            profile_resp = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=20,
            )
            profile = profile_resp.json()
        except Exception:
            return self._redirect_result('error', 'Failed to fetch your Google profile.', frontend_origin)

        if profile_resp.status_code != 200:
            return self._redirect_result('error', 'Failed to fetch your Google profile.', frontend_origin)

        email = (profile.get('email') or '').strip().lower()
        name = (profile.get('name') or '').strip()
        picture = profile.get('picture', '')

        # Validate APSIT email domain
        if not email.endswith(f'@{ALLOWED_EMAIL_DOMAIN}'):
            return self._redirect_result(
                'error',
                f'Please use your APSIT Google account (@{ALLOWED_EMAIL_DOMAIN}). You signed in with {email}.',
                frontend_origin,
            )

        # Find or create user
        try:
            user = User.objects.get(email__iexact=email)
            # Update profile info from Google on each login
            updated_fields = []
            if name and user.first_name != name:
                user.first_name = name
                updated_fields.append('first_name')
            if updated_fields:
                user.save(update_fields=updated_fields)
            if picture and get_user_profile_picture_url(user) != picture:
                set_user_profile_picture_url(user, picture)
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=name,
                password=None,  # No password needed for Google OAuth
            )
            if picture:
                set_user_profile_picture_url(user, picture)

        # Generate JWT tokens
        access_jwt, refresh_jwt = generate_tokens(str(user.id))

        # Auto-detect role from email prefix
        local_part = email.split('@')[0]
        is_likely_student = local_part.replace('.', '').replace('_', '').replace('-', '').isdigit() or any(
            c.isdigit() for c in local_part
        )
        role = 'STUDENT' if is_likely_student else 'DEPARTMENT'

        payload = {
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.first_name or local_part,
                'profile_picture_url': get_user_profile_picture_url(user) or picture,
            },
            'token': access_jwt,
            'refreshToken': refresh_jwt,
            'role': role,
        }

        return self._redirect_result('success', 'Signed in successfully!', frontend_origin, payload)

    def _redirect_result(self, status_text, message, target_origin, payload=None):
        """Redirect the popup to a frontend callback page with the result encoded in the URL."""
        import base64
        result = {
            'type': 'google_oauth',
            'status': status_text,
            'message': message,
            'payload': payload or {},
        }
        encoded = base64.urlsafe_b64encode(json.dumps(result).encode()).decode()
        redirect_url = f"{target_origin}/auth/callback?data={encoded}"
        return HttpResponseRedirect(redirect_url)


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response({
                'success': False,
                'message': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)

            access_token, _ = generate_tokens(str(user.id))

            return Response({
                'success': True,
                'data': {
                    'access_token': access_token,
                }
            }, status=status.HTTP_200_OK)

        except jwt.ExpiredSignatureError:
            return Response({
                'success': False,
                'message': 'Refresh token has expired'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response({
                'success': False,
                'message': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
