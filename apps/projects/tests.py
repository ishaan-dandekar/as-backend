from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from unittest.mock import patch
from datetime import datetime
from django.utils import timezone

from apps.core.authentication import generate_tokens
from apps.projects.models import Project


User = get_user_model()


class RecommendedProjectsViewTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='24102115',
            email='24102115@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
            branch='Computer Engineering',
            admission_year=2024,
            skills=['python', 'django'],
        )
        self.matching_owner = User.objects.create_user(
            username='24102215',
            email='24102215@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
            branch='Computer Engineering',
            admission_year=2024,
        )
        self.admin_owner = User.objects.create_user(
            username='dept1',
            email='dept1@apsit.edu.in',
            password='testpass123',
            role='ADMIN',
        )

        self.best_project = Project.objects.create(
            title='Django Portal',
            description='A matching project',
            tech_stack=['python', 'django'],
            owner=self.matching_owner,
            status='LOOKING_FOR_TEAMMATES',
            team_member_count=1,
            team_capacity=4,
        )
        self.weaker_project = Project.objects.create(
            title='React App',
            description='Less relevant project',
            tech_stack=['react'],
            owner=self.matching_owner,
            status='ACTIVE',
            team_member_count=2,
            team_capacity=2,
        )
        self.admin_project = Project.objects.create(
            title='Admin Project',
            description='Should still be recommended like any other user project',
            tech_stack=['python'],
            owner=self.admin_owner,
            status='ACTIVE',
            team_member_count=1,
            team_capacity=3,
        )

        access_token, _ = generate_tokens(str(self.student.id))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    @patch('apps.core.student_utils.timezone.now')
    def test_recommendations_rank_matching_projects_and_include_admin_projects(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 10, 12, 0, 0))

        response = self.client.get('/api/projects/recommended/')

        self.assertEqual(response.status_code, 200)
        returned_ids = [item['id'] for item in response.data['data']]
        self.assertIn(str(self.best_project.id), returned_ids)
        self.assertIn(str(self.weaker_project.id), returned_ids)
        self.assertIn(str(self.admin_project.id), returned_ids)
        self.assertEqual(returned_ids[0], str(self.best_project.id))
