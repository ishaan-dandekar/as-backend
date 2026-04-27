from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from unittest.mock import patch
from datetime import datetime
from django.utils import timezone

from apps.core.authentication import generate_tokens
from apps.projects.models import Project


User = get_user_model()


class UserProfileAcademicDetailsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='24102115',
            email='24102115@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
            branch='Computer Engineering',
            admission_year=2024,
        )
        access_token, _ = generate_tokens(str(self.user.id))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    @patch('apps.core.student_utils.timezone.now')
    def test_profile_returns_dynamic_academic_status(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 10, 12, 0, 0))

        response = self.client.get('/api/user/profile')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['uid'], '24102115')
        self.assertEqual(response.data['data']['department'], 'Computer Engineering')
        self.assertEqual(response.data['data']['admission_year'], 2024)
        self.assertEqual(response.data['data']['year'], 'TE')
        self.assertEqual(response.data['data']['academic_status'], 'TE')

    def test_student_cannot_update_derived_academic_fields(self):
        response = self.client.patch(
            '/api/user/profile',
            {'branch': 'IT', 'year': 'BE'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.branch, 'Computer Engineering')
        self.assertEqual(self.user.admission_year, 2024)
        self.assertIn('derived from the APSIT UID', response.data['message'])

    def test_profile_includes_total_and_active_project_counts(self):
        Project.objects.create(
            title='Active Project',
            description='Visible active project',
            tech_stack=['python'],
            owner=self.user,
            status='ACTIVE',
        )
        Project.objects.create(
            title='Completed Project',
            description='Finished project',
            tech_stack=['django'],
            owner=self.user,
            status='COMPLETED',
        )

        response = self.client.get('/api/user/profile')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['projects_count'], 2)
        self.assertEqual(response.data['data']['active_projects_count'], 1)

    @patch('apps.core.student_utils.timezone.now')
    def test_profile_backfills_missing_academic_fields_from_uid(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 10, 12, 0, 0))
        self.user.branch = None
        self.user.admission_year = None
        self.user.save(update_fields=['branch', 'admission_year'])

        response = self.client.get('/api/user/profile')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['department'], 'Computer Engineering')
        self.assertEqual(response.data['data']['admission_year'], 2024)
        self.assertEqual(response.data['data']['academic_status'], 'TE')
        self.user.refresh_from_db()
        self.assertEqual(self.user.branch, 'Computer Engineering')
        self.assertEqual(self.user.admission_year, 2024)

    @patch('apps.core.student_utils.timezone.now')
    def test_admin_with_numeric_uid_still_gets_academic_details(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 10, 12, 0, 0))
        self.user.role = 'ADMIN'
        self.user.branch = None
        self.user.admission_year = None
        self.user.save(update_fields=['role', 'branch', 'admission_year'])

        response = self.client.get('/api/user/profile')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['role'], 'ADMIN')
        self.assertEqual(response.data['data']['department'], 'Computer Engineering')
        self.assertEqual(response.data['data']['academic_status'], 'TE')


class MoodleIdPrimaryKeyTests(APITestCase):
    def test_user_primary_key_defaults_to_moodle_id(self):
        user = User.objects.create_user(
            username='24102115@apsit.edu.in',
            email='24102115@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
        )

        self.assertEqual(user.id, '24102115')
        self.assertEqual(user.username, '24102115')
