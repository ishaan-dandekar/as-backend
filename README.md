# APSIT Student Sphere Backend

Backend service for APSIT Student Sphere, a student collaboration and networking platform where students can discover peers, build projects, form teams, join events, and receive notifications.

## Stack

- **Framework**: Django 4.2.9 + Django REST Framework 3.14.0
- **Database**: MySQL 5.7+ (configured for localhost:3306)
- **API Authentication**: JWT (PyJWT)
- **Documentation**: REST API endpoints (40+ endpoints)

## Quick Start

### 1. Prerequisites

- Python 3.9+ installed
- MySQL 5.7+ running on `localhost:3306`
- Virtual environment (recommended)

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create MySQL database and an app-specific user
# On Ubuntu, root often uses auth_socket and may fail with password auth.
sudo mysql -e "CREATE DATABASE IF NOT EXISTS project_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'project_hub_user'@'localhost' IDENTIFIED BY 'project_hub_password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON project_hub.* TO 'project_hub_user'@'localhost'; FLUSH PRIVILEGES;"
```

Or run the helper script (recommended):

```bash
./scripts/setup_mysql.sh
```

The script automatically generates a strong DB password (if needed for MySQL password policy) and writes the final DB settings into `.env`.

### 4. Environment Configuration

The `.env` file is already configured with defaults:

```env
# MySQL Configuration
DB_ENGINE=mysql
DB_NAME=project_hub
DB_USER=project_hub_user
DB_PASSWORD=project_hub_password
DB_HOST=127.0.0.1
DB_PORT=3306

# JWT Configuration
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=7

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# External APIs (Optional)
GITHUB_API_TOKEN=your-github-token
LEETCODE_API_URL=https://leetcode.com/graphql

# GitHub OAuth (Required for authorized profile linking)
GITHUB_OAUTH_CLIENT_ID=your-github-oauth-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-oauth-client-secret
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/user/github/oauth/callback
GITHUB_OAUTH_SCOPE=read:user user:email repo
FRONTEND_APP_URL=http://localhost:3000
```

Create a GitHub OAuth app with callback URL:

`http://localhost:8000/api/user/github/oauth/callback`

### 5. Run Migrations & Start Server

```bash
# Apply migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver 8000
```

Server will be available at: `http://localhost:8000`

## Troubleshooting MySQL Login

If you see this error:

`django.db.utils.OperationalError: (1698, "Access denied for user 'root'@'localhost'")`

It usually means MySQL root is configured with socket authentication on Linux. Use a dedicated DB user (`project_hub_user`) as shown above, then verify your `.env` has matching values before running:

```bash
python manage.py migrate
python manage.py runserver 8000
```

## API Endpoints

All endpoints are prefixed with `/api/v1/` in production. Authentication uses Bearer tokens in Authorization header:

```
Authorization: Bearer <access_token>
```

### 1. Authentication Endpoints

#### Register User
```
POST /api/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}

Response:
{
  "success": true,
  "data": {
    "user": { ... user data ... },
    "access": "eyJhbGc...",
    "refresh": "eyJhbGc..."
  }
}
```

#### Login
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!"
}

Response:
{
  "success": true,
  "data": {
    "user": { ... user data ... },
    "access": "eyJhbGc...",
    "refresh": "eyJhbGc..."
  }
}
```

#### Refresh Access Token
```
POST /api/auth/refresh
Content-Type: application/json
Authorization: Bearer <refresh_token>

{
  "refresh": "eyJhbGc..."
}

Response:
{
  "success": true,
  "data": {
    "access": "eyJhbGc..."
  }
}
```

#### Logout
```
POST /api/auth/logout
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "message": "Logged out successfully"
}
```

### 2. User Endpoints

#### Get My Profile
```
GET /api/user/profile
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": {
    "id": "uuid",
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "bio": "Software developer",
    "skills": ["Python", "JavaScript"],
    "interests": ["Web Dev", "AI"],
    "github_username": "johndoe",
    "leetcode_username": "johndoe",
    "profile_picture_url": "https://...",
    "github_stats": { "repos": 5, "followers": 10 },
    "leetcode_stats": { "solved": 50, "rank": 1500 }
  }
}
```

#### Update My Profile
```
PATCH /api/user/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "bio": "Updated bio",
  "skills": ["Python", "JavaScript", "Go"],
  "interests": ["Web Dev", "AI", "DevOps"]
}

Response: { "success": true, "data": { ... updated user ... } }
```

#### Get User by ID
```
GET /api/user/<user_id>

Response:
{
  "success": true,
  "data": { ... public user info ... }
}
```

#### Search Users
```
GET /api/user/search?q=john&page=1&limit=10

Response:
{
  "success": true,
  "data": [
    { "id": "uuid", "username": "john", ... },
    { "id": "uuid", "username": "johnny", ... }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 2,
    "pages": 1
  }
}
```

#### Get GitHub Stats
```
GET /api/user/github/<username>

Response:
{
  "success": true,
  "data": {
    "username": "johndoe",
    "repos": 5,
    "followers": 10,
    "following": 5,
    "public_gists": 2
  }
}
```

### 3. Project Endpoints

#### List Projects
```
GET /api/projects/?status=ACTIVE&tech_stack=Python&page=1&limit=10

Response:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Project Title",
      "description": "Description",
      "status": "ACTIVE",
      "tech_stack": ["Python", "Django", "PostgreSQL"],
      "owner": { "id": "uuid", "username": "johndoe" },
      "team": null,
      "is_bookmarked": false,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 10, "total": 25, "pages": 3 }
}
```

#### Create Project
```
POST /api/projects/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "My Awesome Project",
  "description": "A full-stack web application",
  "status": "LOOKING_FOR_TEAMMATES",
  "tech_stack": ["React", "Node.js", "MongoDB"]
}

Response:
{
  "success": true,
  "data": { "id": "uuid", ... project data ... }
}
```

#### Get Project Details
```
GET /api/projects/<project_id>

Response:
{
  "success": true,
  "data": { ... full project details ... }
}
```

#### Update Project
```
PATCH /api/projects/<project_id>
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "description": "Updated description",
  "status": "IN_PROGRESS"
}

Response: { "success": true, "data": { ... updated project ... } }
```

#### Delete Project
```
DELETE /api/projects/<project_id>
Authorization: Bearer <access_token>

Response: { "success": true, "message": "Project deleted successfully" }
```

#### Bookmark Project
```
POST /api/projects/<project_id>/bookmark
Authorization: Bearer <access_token>

Response: { "success": true, "data": { ... project data ... } }
```

#### Get My Projects
```
GET /api/projects/my-projects
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": [ ... user's projects ... ]
}
```

### 4. Team Endpoints

#### Create Team
```
POST /api/teams/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Team Name",
  "description": "Team description",
  "capacity": 5
}

Response:
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Team Name",
    "description": "Team description",
    "owner": { "id": "uuid", "username": "johndoe" },
    "members": [ { "id": "uuid", "username": "johndoe" } ],
    "member_count": 1,
    "capacity": 5,
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

#### Get Team Details
```
GET /api/teams/<team_id>

Response: { "success": true, "data": { ... team data ... } }
```

#### Update Team
```
PATCH /api/teams/<team_id>
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "description": "Updated description",
  "capacity": 10
}

Response: { "success": true, "data": { ... updated team ... } }
```

#### Delete Team
```
DELETE /api/teams/<team_id>
Authorization: Bearer <access_token>

Response: { "success": true, "message": "Team deleted successfully" }
```

#### Request to Join Team
```
POST /api/teams/<team_id>/join
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": {
    "id": "uuid",
    "user": { "id": "uuid", "username": "johndoe" },
    "team": { "id": "uuid", "name": "Team Name" },
    "status": "PENDING",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

#### Approve Join Request
```
POST /api/teams/join-request/<request_id>/approve
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "APPROVED",
    ... join request data ...
  }
}
```

### 5. Event Endpoints

#### List Events
```
GET /api/events/?status=UPCOMING&page=1&limit=10

Response:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Hackathon 2024",
      "description": "24-hour coding competition",
      "location": "Virtual",
      "start_date": "2024-02-01T09:00:00Z",
      "end_date": "2024-02-02T09:00:00Z",
      "organizer": { "id": "uuid", "username": "organizer" },
      "status": "UPCOMING",
      "attendee_count": 50,
      "capacity": 100,
      "tags": ["hackathon", "coding"]
    }
  ],
  "pagination": { ... }
}
```

#### Create Event
```
POST /api/events/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Hackathon 2024",
  "description": "24-hour coding competition",
  "location": "Virtual",
  "start_date": "2024-02-01T09:00:00Z",
  "end_date": "2024-02-02T09:00:00Z",
  "capacity": 100,
  "tags": ["hackathon", "coding"]
}

Response: { "success": true, "data": { ... event data ... } }
```

#### Get Event Details
```
GET /api/events/<event_id>

Response: { "success": true, "data": { ... event details ... } }
```

#### Update Event
```
PATCH /api/events/<event_id>
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "ONGOING"
}

Response: { "success": true, "data": { ... updated event ... } }
```

#### Delete Event
```
DELETE /api/events/<event_id>
Authorization: Bearer <access_token>

Response: { "success": true, "message": "Event deleted successfully" }
```

#### Register for Event
```
POST /api/events/<event_id>/register
Authorization: Bearer <access_token>

Response: { "success": true, "data": { ... event data ... } }
```

#### Unregister from Event
```
POST /api/events/<event_id>/unregister
Authorization: Bearer <access_token>

Response: { "success": true, "data": { ... event data ... } }
```

### 6. Notification Endpoints

#### Get Notifications (Polling)
```
GET /api/notifications/?unreadOnly=false&page=1&limit=10
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "type": "PROJECT_INVITE",
      "title": "You've been invited to join a project",
      "message": "John invited you to join 'My Project'",
      "is_read": false,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

#### Mark Notification as Read
```
PATCH /api/notifications/<notification_id>/read
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": { ... notification data ... }
}
```

#### Mark All as Read
```
POST /api/notifications/read-all
Authorization: Bearer <access_token>

Response: { "success": true, "message": "All notifications marked as read" }
```

#### Delete Notification
```
DELETE /api/notifications/<notification_id>/
Authorization: Bearer <access_token>

Response: { "success": true, "message": "Notification deleted" }
```

#### Get Unread Count
```
GET /api/notifications/unread-count/
Authorization: Bearer <access_token>

Response:
{
  "success": true,
  "data": { "unread_count": 5 }
}
```

### 7. Health Check

#### System Health
```
GET /api/health/

Response:
{
  "success": true,
  "message": "API is running",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## Database Schema

### User Model
- `id` (UUID): Unique identifier
- `username` (String): Unique username
- `email` (String): Unique email
- `password` (String): Hashed password
- `first_name`, `last_name` (String): User name
- `bio` (Text): User biography
- `skills` (JSON): Array of skill tags
- `interests` (JSON): Array of interest tags
- `github_username` (String): GitHub profile link
- `leetcode_username` (String): LeetCode profile link
- `profile_picture_url` (URL): Profile image
- `github_stats` (JSON): Cached GitHub statistics
- `leetcode_stats` (JSON): Cached LeetCode statistics
- `role` (String): User role (USER, ADMIN)
- `created_at`, `updated_at` (DateTime): Timestamps
- `is_active` (Boolean): Account active status

### Project Model
- `id` (UUID): Unique identifier
- `title` (String): Project name
- `description` (Text): Project description
- `status` (String): LOOKING_FOR_TEAMMATES | IN_PROGRESS | COMPLETED | ACTIVE
- `tech_stack` (JSON): Technologies used
- `owner` (FK): Project creator
- `team` (FK): Associated team (optional)
- `bookmarked_by` (JSON): User IDs who bookmarked
- `created_at`, `updated_at` (DateTime): Timestamps

### Team Model
- `id` (UUID): Unique identifier
- `name` (String): Team name
- `description` (Text): Team description
- `owner` (FK): Team creator
- `members` (M2M): Team members through JoinRequest
- `member_count` (Integer): Current member count
- `capacity` (Integer): Max members
- `member_roles` (JSON): Role assignments for members
- `created_at`, `updated_at` (DateTime): Timestamps

### JoinRequest Model
- `id` (UUID): Unique identifier
- `user` (FK): User requesting to join
- `team` (FK): Target team
- `status` (String): PENDING | APPROVED | REJECTED
- `created_at`, `updated_at` (DateTime): Timestamps

### Event Model
- `id` (UUID): Unique identifier
- `title` (String): Event name
- `description` (Text): Event details
- `location` (String): Event location
- `start_date`, `end_date` (DateTime): Event timing
- `organizer` (FK): Event creator
- `status` (String): UPCOMING | ONGOING | COMPLETED | CANCELLED
- `attendees` (JSON): User IDs attending
- `attendee_count` (Integer): Current attendee count
- `capacity` (Integer): Max attendees
- `tags` (JSON): Event tags/categories
- `created_at`, `updated_at` (DateTime): Timestamps

### Notification Model
- `id` (UUID): Unique identifier
- `user` (FK): Target user
- `type` (String): PROJECT_INVITE | TEAM_INVITE | JOIN_REQUEST | JOIN_APPROVED | etc.
- `title` (String): Notification title
- `message` (Text): Notification content
- `related_id` (String): Reference to related entity
- `related_type` (String): Type of related entity
- `is_read` (Boolean): Read status
- `metadata` (JSON): Additional data
- `created_at`, `updated_at` (DateTime): Timestamps

## Authentication Flow

1. **Register/Login**: Get `access` and `refresh` tokens
2. **API Requests**: Include `Authorization: Bearer <access_token>` header
3. **Token Expiration**: Use `refresh` token to get new `access` token
4. **Logout**: Token becomes invalid on backend (stateless JWT)

## Error Responses

All errors follow standard format:

```json
{
  "success": false,
  "message": "Error description",
  "errors": {
    "field_name": ["Error detail"]
  }
}
```

Common HTTP Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request / Validation Error
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Server Error

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Django debug mode |
| `DB_ENGINE` | `django.db.backends.mysql` | Database backend |
| `DB_NAME` | `project_hub` | Database name |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | `` | Database password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |
| `SECRET_KEY` | `...` | Django secret key |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_HOURS` | `24` | Access token life |
| `JWT_REFRESH_EXPIRATION_DAYS` | `7` | Refresh token life |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | CORS whitelist |

## Deployment Notes (Future)

For production deployment:

1. Set `DEBUG = False` in settings.py
2. Use environment-specific `.env` files
3. Run migrations: `python manage.py migrate`
4. Collect static files: `python manage.py collectstatic`
5. Use production WSGI server (Gunicorn, uWSGI)
6. Configure HTTPS with SSL certificates
7. Set up database backups and monitoring
8. Configure logging and error tracking

## Development Tips

### Running Tests
```bash
python manage.py test
```

### Creating Superuser
```bash
python manage.py createsuperuser
```

### Database Migrations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

### Shell Access
```bash
python manage.py shell
```

## License

MIT License - feel free to use this project for your own purposes.

## Support

For issues or questions, please create an issue in the repository.
