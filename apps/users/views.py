from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import requests
from django.conf import settings
from django.core.cache import cache
from django.core import signing
from django.db.models import Q
from urllib.parse import urlencode, urlparse
import uuid
import json
from .models import get_user_profile_picture_url
from apps.core.discovery import normalize_skill_tag, normalize_tags

User = get_user_model()
GITHUB_OAUTH_STATE_SALT = 'project-hub-github-oauth-state'
GITHUB_OAUTH_SESSION_PREFIX = 'github_oauth_session:'
GITHUB_OAUTH_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
VALID_BRANCHES = {choice[0] for choice in getattr(User, 'BRANCH_CHOICES', [])}
VALID_YEARS = {choice[0] for choice in getattr(User, 'YEAR_CHOICES', [])}


def _normalized_user_role(user):
    role = (getattr(user, 'role', '') or '').upper()
    if role in {'DEPARTMENT', 'ADMIN'}:
        return 'DEPARTMENT'
    return 'STUDENT'


def _build_github_stats_payload(profile_data, repos_data):
    total_stars = sum(repo.get('stargazers_count', 0) for repo in repos_data)
    total_forks = sum(repo.get('forks_count', 0) for repo in repos_data)

    language_counts = {}
    for repo in repos_data:
        language = repo.get('language')
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    top_languages = [
        {'name': name, 'count': count}
        for name, count in sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        'user': {
            'login': profile_data.get('login'),
            'name': profile_data.get('name') or profile_data.get('login'),
            'avatar_url': profile_data.get('avatar_url'),
            'bio': profile_data.get('bio'),
            'public_repos': profile_data.get('public_repos', 0),
            'followers': profile_data.get('followers', 0),
            'following': profile_data.get('following', 0),
            'html_url': profile_data.get('html_url'),
            'created_at': profile_data.get('created_at'),
        },
        'repos': profile_data.get('public_repos', 0) + profile_data.get('total_private_repos', 0),
        'totalStars': total_stars,
        'totalForks': total_forks,
        'topLanguages': top_languages,
        'recentRepos': [
            {
                'id': repo.get('id'),
                'name': repo.get('name'),
                'full_name': repo.get('full_name'),
                'description': repo.get('description'),
                'html_url': repo.get('html_url'),
                'stargazers_count': repo.get('stargazers_count', 0),
                'forks_count': repo.get('forks_count', 0),
                'language': repo.get('language'),
                'updated_at': repo.get('updated_at'),
                'private': repo.get('private', False),
            }
            for repo in repos_data[:5]
        ],
        'contributionsThisYear': 0,
    }


def _github_headers(access_token=None):
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    token = access_token or settings.GITHUB_API_TOKEN
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _cache_session(session_id, payload):
    cache.set(
        f'{GITHUB_OAUTH_SESSION_PREFIX}{session_id}',
        payload,
        timeout=GITHUB_OAUTH_SESSION_TTL_SECONDS,
    )


def _get_cached_session(session_id):
    return cache.get(f'{GITHUB_OAUTH_SESSION_PREFIX}{session_id}')


def _delete_cached_session(session_id):
    cache.delete(f'{GITHUB_OAUTH_SESSION_PREFIX}{session_id}')


def _safe_user_payload(user):
    moodle_id = str(user.id)

    teams_joined_value = getattr(user, 'teams_joined', None)
    if hasattr(teams_joined_value, 'count'):
        try:
            teams_joined_value = teams_joined_value.count()
        except Exception:
            teams_joined_value = 0
    elif teams_joined_value is None:
        teams_joined_value = getattr(user, 'teams_joined_count', 0)

    github_username_value = getattr(user, 'github_username', None)
    if github_username_value is None:
        github_username_value = getattr(user, 'last_name', None) or None

    skill_tags = normalize_tags(getattr(user, 'skills', []))

    return {
        'id': str(user.id),
        'moodle_id': moodle_id,
        'unique_id': moodle_id,
        'username': user.username,
        'email': user.email,
        'role': _normalized_user_role(user),
        'name': getattr(user, 'first_name', '') or user.username,
        'profile_picture_url': get_user_profile_picture_url(user),
        'bio': getattr(user, 'bio', ''),
        'branch': getattr(user, 'branch', None),
        'year': getattr(user, 'year', None),
        'github_username': github_username_value,
        'leetcode_username': getattr(user, 'leetcode_username', None),
        'skills': skill_tags,
        'skill_tags': skill_tags,
        'interests': getattr(user, 'interests', []),
        'projects_created': getattr(user, 'projects_created', 0),
        'projects_completed': getattr(user, 'projects_completed', 0),
        'teams_joined': teams_joined_value,
    }


def _derive_moodle_id(user):
    return str(user.id)


def _resolve_user_by_identifier(identifier: str):
    identifier = (identifier or '').strip()
    if not identifier:
        return None

    # Preferred: direct primary key match (Moodle ID)
    user = User.objects.filter(id=identifier).first()
    if user:
        return user

    # Fallback: username match (often moodle ID)
    user = User.objects.filter(username__iexact=identifier).first()
    if user:
        return user

    # Fallback: APSIT email local-part moodle ID, e.g. 12345@apsit.edu.in
    user = User.objects.filter(email__istartswith=f'{identifier}@').first()
    return user


class UserProfileView(APIView):
    def get(self, request):
        """Get user profile (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=request.user_id)
            return Response({
                'success': True,
                'data': _safe_user_payload(user)
            })
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request):
        """Update user profile (authenticated)"""
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=request.user_id)

            immutable_google_fields = []
            if 'first_name' in request.data or 'name' in request.data:
                immutable_google_fields.append('name')
            if 'profile_picture_url' in request.data:
                immutable_google_fields.append('profile_picture_url')
            if 'location' in request.data:
                immutable_google_fields.append('location')

            if immutable_google_fields:
                return Response(
                    {
                        'success': False,
                        'message': (
                            'The following fields are managed from your Google account and cannot be edited here: '
                            + ', '.join(immutable_google_fields)
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            branch = request.data.get('branch') if 'branch' in request.data else None
            year = request.data.get('year') if 'year' in request.data else None

            if _normalized_user_role(user) != 'STUDENT':
                if 'branch' in request.data or 'year' in request.data:
                    return Response(
                        {
                            'success': False,
                            'message': 'Only student profiles can set branch and year.',
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                if 'branch' in request.data:
                    normalized_branch = str(branch or '').strip()
                    if normalized_branch and normalized_branch not in VALID_BRANCHES:
                        return Response(
                            {
                                'success': False,
                                'message': f"branch must be one of: {', '.join(sorted(VALID_BRANCHES))}",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    user.branch = normalized_branch or None

                if 'year' in request.data:
                    normalized_year = str(year or '').strip().upper()
                    if normalized_year and normalized_year not in VALID_YEARS:
                        return Response(
                            {
                                'success': False,
                                'message': f"year must be one of: {', '.join(sorted(VALID_YEARS))}",
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    user.year = normalized_year or None

            # Update allowed fields
            for field in ['bio', 'github_url', 'linkedin_url', 'interests', 'github_username', 'leetcode_username']:
                if field in request.data and hasattr(user, field):
                    setattr(user, field, request.data[field])

            if 'skills' in request.data and hasattr(user, 'skills'):
                raw_skills = request.data.get('skills') or []
                if not isinstance(raw_skills, list):
                    raw_skills = [raw_skills]
                user.skills = normalize_tags(raw_skills)

            if 'github_username' in request.data and not hasattr(user, 'github_username'):
                user.last_name = request.data.get('github_username') or ''

            user.save()
            return Response({
                'success': True,
                'data': _safe_user_payload(user)
            })
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class UserDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, user_id):
        """Get user by primary ID (Moodle ID) or fallback identifiers."""
        user = _resolve_user_by_identifier(user_id)
        if not user:
            return Response({'success': False, 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'data': _safe_user_payload(user)
        })


class GitHubOAuthStartView(APIView):
    def get(self, request):
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        frontend_origin = (request.query_params.get('frontend_origin') or '').strip().rstrip('/')
        callback_origin = settings.FRONTEND_APP_URL.rstrip('/')
        if frontend_origin and self._is_allowed_frontend_origin(frontend_origin):
            callback_origin = frontend_origin

        missing = []
        if not settings.GITHUB_OAUTH_CLIENT_ID:
            missing.append('GITHUB_OAUTH_CLIENT_ID')
        if not settings.GITHUB_OAUTH_CLIENT_SECRET:
            missing.append('GITHUB_OAUTH_CLIENT_SECRET')

        if missing:
            return Response(
                {
                    'success': False,
                    'message': f"GitHub OAuth is not configured. Missing: {', '.join(missing)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        state_payload = {
            'user_id': str(request.user_id),
            'nonce': uuid.uuid4().hex,
            'frontend_origin': callback_origin,
        }
        signed_state = signing.dumps(state_payload, salt=GITHUB_OAUTH_STATE_SALT)

        authorize_query = urlencode({
            'client_id': settings.GITHUB_OAUTH_CLIENT_ID,
            'redirect_uri': settings.GITHUB_OAUTH_REDIRECT_URI,
            'scope': settings.GITHUB_OAUTH_SCOPE,
            'state': signed_state,
        })

        return Response({
            'success': True,
            'data': {
                'authorizationUrl': f'https://github.com/login/oauth/authorize?{authorize_query}'
            }
        })

    def _is_allowed_frontend_origin(self, origin: str) -> bool:
        try:
            parsed = urlparse(origin)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                return False
        except Exception:
            return False

        allowed_origins = {settings.FRONTEND_APP_URL.rstrip('/')}
        allowed_origins.update(o.rstrip('/') for o in getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
        return origin in allowed_origins


class GitHubOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        frontend_origin = settings.FRONTEND_APP_URL.rstrip('/')

        if error:
            return self._html_result('error', f'GitHub authorization failed: {error}', frontend_origin)

        if not code or not state:
            return self._html_result(
                'error',
                'This URL is a GitHub callback endpoint. Start from Profile > Authorize GitHub so GitHub can append code and state automatically.',
                frontend_origin,
            )

        try:
            payload = signing.loads(state, salt=GITHUB_OAUTH_STATE_SALT, max_age=600)
        except signing.SignatureExpired:
            return self._html_result('error', 'OAuth state expired. Please retry.', frontend_origin)
        except signing.BadSignature:
            return self._html_result('error', 'Invalid OAuth state', frontend_origin)

        state_frontend_origin = (payload.get('frontend_origin') or '').strip().rstrip('/')
        if state_frontend_origin and self._is_allowed_frontend_origin(state_frontend_origin):
            frontend_origin = state_frontend_origin

        user_id = payload.get('user_id')
        if not user_id:
            return self._html_result('error', 'Invalid OAuth payload', frontend_origin)

        token_resp = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            data={
                'client_id': settings.GITHUB_OAUTH_CLIENT_ID,
                'client_secret': settings.GITHUB_OAUTH_CLIENT_SECRET,
                'code': code,
                'redirect_uri': settings.GITHUB_OAUTH_REDIRECT_URI,
                'state': state,
            },
            timeout=20,
        )

        try:
            token_json = token_resp.json()
        except ValueError:
            token_json = {}

        if token_resp.status_code != 200:
            details = token_json.get('error_description') or token_json.get('error') or token_resp.text
            return self._html_result('error', f'Failed to exchange GitHub authorization code: {details}', frontend_origin)

        if token_json.get('error'):
            details = token_json.get('error_description') or token_json.get('error')
            return self._html_result('error', f'GitHub token exchange rejected: {details}', frontend_origin)

        access_token = token_json.get('access_token')
        if not access_token:
            return self._html_result('error', 'GitHub token not returned. Verify Client ID/Secret and callback URL match the OAuth app exactly.', frontend_origin)

        profile_resp = requests.get(
            f"{settings.GITHUB_API_URL}/user",
            headers=_github_headers(access_token),
            timeout=20,
        )

        if profile_resp.status_code != 200:
            return self._html_result('error', 'Unable to fetch GitHub profile', frontend_origin)

        profile = profile_resp.json()
        github_username = profile.get('login')

        if not github_username:
            return self._html_result('error', 'GitHub username is missing from profile response', frontend_origin)

        session_id = uuid.uuid4().hex
        _cache_session(session_id, {
            'user_id': str(user_id),
            'access_token': access_token,
            'github_username': github_username,
        })

        try:
            user = User.objects.get(id=user_id)
            if hasattr(user, 'github_username'):
                user.github_username = github_username
                user.save(update_fields=['github_username'])
        except User.DoesNotExist:
            pass

        payload = {
            'sessionId': session_id,
            'githubUsername': github_username,
        }
        return self._html_result('success', 'GitHub connected', frontend_origin, payload)

    def _is_allowed_frontend_origin(self, origin: str) -> bool:
        try:
            parsed = urlparse(origin)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                return False
        except Exception:
            return False

        allowed_origins = {settings.FRONTEND_APP_URL.rstrip('/')}
        allowed_origins.update(o.rstrip('/') for o in getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
        return origin in allowed_origins

    def _html_result(self, status_text, message, target_origin, payload=None):
        payload = payload or {}
        message_json = {
            'type': 'github_oauth',
            'status': status_text,
            'message': message,
            'payload': payload,
        }
        message_js = json.dumps(message_json)

        html = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>GitHub Authorization</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        margin: 0;
        background: #f8fafc;
        color: #334155;
      }}
      .container {{
        text-align: center;
        padding: 2rem;
      }}
      .spinner {{
        width: 40px;
        height: 40px;
        border: 3px solid #e2e8f0;
        border-top-color: #0d9488;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin: 0 auto 1rem;
      }}
      @keyframes spin {{
        to {{ transform: rotate(360deg); }}
      }}
      p {{ font-size: 14px; color: #64748b; }}
    </style>
  </head>
  <body>
    <div class="container">
      <div class="spinner"></div>
      <p>Completing authorization...</p>
      <p id="fallback" style="display:none; margin-top: 12px;">
        <a href="#" onclick="window.close(); return false;"
           style="color: #0d9488; text-decoration: underline;">Click here to close this window</a>
      </p>
    </div>
    <script>
      (function() {{
        var message = {message_js};
        var targetOrigin = '{target_origin}';

                if (window.opener && !window.opener.closed) {{
                    try {{
                        window.opener.postMessage(message, targetOrigin);
                    }} catch (e) {{}}
                }}

                // Deterministic handoff: always redirect popup to frontend origin with OAuth params.
                // The frontend settings page will persist session, notify opener, and close the popup.
                try {{
                    var params = new URLSearchParams();
                    params.set('github_oauth', message.status || 'error');
                    params.set('github_message', message.message || '');

                    if (message.status === 'success' && message.payload) {{
                        if (message.payload.sessionId) params.set('session_id', message.payload.sessionId);
                        if (message.payload.githubUsername) params.set('github_username', message.payload.githubUsername);
                    }}

                    var nextUrl = targetOrigin + '/settings?' + params.toString();
                    window.location.replace(nextUrl);
                    return;
                }} catch (e) {{}}

                // If redirect fails, keep popup open with manual close fallback.
                var fb = document.getElementById('fallback');
                if (fb) fb.style.display = 'block';
      }})();
    </script>
  </body>
</html>
"""

        return HttpResponse(html, content_type='text/html; charset=utf-8')


class GitHubAuthorizedStatsView(APIView):
    def get(self, request):
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        session_id = request.headers.get('X-GitHub-Session') or request.query_params.get('session_id')

        if not session_id:
            return Response({'success': False, 'message': 'Missing GitHub session id'}, status=status.HTTP_400_BAD_REQUEST)

        oauth_session = _get_cached_session(session_id)
        if not oauth_session:
            return Response({'success': False, 'message': 'GitHub session expired. Please reconnect.'}, status=status.HTTP_401_UNAUTHORIZED)

        if str(oauth_session.get('user_id')) != str(request.user_id):
            return Response({'success': False, 'message': 'GitHub session does not belong to this user'}, status=status.HTTP_403_FORBIDDEN)

        access_token = oauth_session.get('access_token')
        if not access_token:
            return Response({'success': False, 'message': 'Invalid GitHub session'}, status=status.HTTP_401_UNAUTHORIZED)

        profile_resp = requests.get(
            f"{settings.GITHUB_API_URL}/user",
            headers=_github_headers(access_token),
            timeout=20,
        )
        repos_resp = requests.get(
            f"{settings.GITHUB_API_URL}/user/repos",
            headers=_github_headers(access_token),
            params={
                'sort': 'updated',
                'per_page': 100,
                'visibility': 'all',
                'affiliation': 'owner,collaborator,organization_member',
            },
            timeout=20,
        )

        if profile_resp.status_code != 200 or repos_resp.status_code != 200:
            return Response({'success': False, 'message': 'Failed to fetch authorized GitHub data'}, status=status.HTTP_400_BAD_REQUEST)

        profile_data = profile_resp.json()
        repos_data = repos_resp.json() if isinstance(repos_resp.json(), list) else []

        stats_payload = _build_github_stats_payload(profile_data, repos_data)

        return Response({
            'success': True,
            'data': {
                **stats_payload,
                'sessionId': session_id,
                'githubUsername': profile_data.get('login'),
            }
        })


class GitHubOAuthDisconnectView(APIView):
    def post(self, request):
        if not hasattr(request, 'user_id'):
            return Response({'success': False, 'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        session_id = request.data.get('session_id') or request.headers.get('X-GitHub-Session')
        if session_id:
            oauth_session = _get_cached_session(session_id)
            if oauth_session and str(oauth_session.get('user_id')) == str(request.user_id):
                # Revoke the token at GitHub so the app is actually unauthorized, not just locally disconnected.
                access_token = oauth_session.get('access_token')
                if access_token and settings.GITHUB_OAUTH_CLIENT_ID and settings.GITHUB_OAUTH_CLIENT_SECRET:
                    try:
                        requests.delete(
                            f"https://api.github.com/applications/{settings.GITHUB_OAUTH_CLIENT_ID}/token",
                            auth=(settings.GITHUB_OAUTH_CLIENT_ID, settings.GITHUB_OAUTH_CLIENT_SECRET),
                            headers={
                                'Accept': 'application/vnd.github+json',
                                'X-GitHub-Api-Version': '2022-11-28',
                            },
                            json={'access_token': access_token},
                            timeout=20,
                        )
                    except requests.RequestException:
                        # Best effort revoke; proceed with local cleanup.
                        pass
                _delete_cached_session(session_id)

        try:
            user = User.objects.get(id=request.user_id)
            if hasattr(user, 'github_username'):
                user.github_username = None
                user.save(update_fields=['github_username'])
        except User.DoesNotExist:
            pass

        return Response({'success': True, 'message': 'GitHub disconnected'})


class GitHubStatsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, username):
        """Get GitHub stats for user"""
        try:
            headers = {}
            if settings.GITHUB_API_TOKEN:
                headers['Authorization'] = f'token {settings.GITHUB_API_TOKEN}'

            response = requests.get(f'{settings.GITHUB_API_URL}/users/{username}', headers=headers)

            if response.status_code != 200:
                return Response({'success': False, 'message': 'GitHub user not found'}, status=status.HTTP_404_NOT_FOUND)

            data = response.json()
            return Response({
                'success': True,
                'data': {
                    'username': data.get('login'),
                    'public_repos': data.get('public_repos'),
                    'followers': data.get('followers'),
                    'following': data.get('following'),
                    'joined_at': data.get('created_at'),
                }
            })
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserSearchView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Search users"""
        query = (request.query_params.get('q') or '').strip()
        normalized_query = query.lower()
        skills = request.query_params.getlist('skills')
        if not skills:
            skills = [
                item.strip()
                for item in str(request.query_params.get('skills', '')).split(',')
                if item.strip()
            ]

        try:
            limit = int(request.query_params.get('limit', 25))
        except (TypeError, ValueError):
            limit = 25

        limit = max(1, min(limit, 100))

        users = User.objects.all()
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(branch__icontains=query)
                | Q(year__icontains=query)
                | Q(github_username__icontains=query)
                | Q(leetcode_username__icontains=query)
            )

        users = list(users.order_by('first_name', 'username'))
        normalized_skills = {normalize_skill_tag(skill).lower() for skill in skills if normalize_skill_tag(skill)}

        if normalized_skills:
            users = [
                user for user in users
                if normalized_skills.issubset({
                    normalized_skill.lower()
                    for normalized_skill in normalize_tags(getattr(user, 'skills', []))
                })
            ]

        if query:
            users = [
                user for user in users
                if normalized_query in _derive_moodle_id(user).lower()
                or normalized_query in f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".lower()
                or normalized_query in (user.username or '').lower()
                or normalized_query in (user.email or '').lower()
                or normalized_query in (getattr(user, 'github_username', '') or '').lower()
                or normalized_query in (getattr(user, 'leetcode_username', '') or '').lower()
                or any(
                    normalized_query in skill.lower()
                    for skill in normalize_tags(getattr(user, 'skills', []))
                )
            ]

        users = users[:limit]
        return Response({
            'success': True,
            'data': [{
                'id': str(user.id),
                'moodle_id': _derive_moodle_id(user),
                'unique_id': _derive_moodle_id(user),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_picture_url': get_user_profile_picture_url(user),
                'branch': getattr(user, 'branch', None),
                'year': getattr(user, 'year', None),
                'skills': normalize_tags(getattr(user, 'skills', [])),
                'skill_tags': normalize_tags(getattr(user, 'skills', [])),
                'github_username': getattr(user, 'github_username', None),
                'leetcode_username': getattr(user, 'leetcode_username', None),
            } for user in users]
        })
