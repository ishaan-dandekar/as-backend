from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.authentication import generate_tokens

from .models import Project


User = get_user_model()


class RecommendedProjectsViewTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student2',
            email='student2@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
            branch='CE',
            year='TE',
            skills=['python', 'django'],
        )
        self.matching_owner = User.objects.create_user(
            username='owner1',
            email='owner1@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
            branch='CE',
            year='TE',
        )
        self.department_owner = User.objects.create_user(
            username='dept1',
            email='dept1@apsit.edu.in',
            password='testpass123',
            role='DEPARTMENT',
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
        self.department_project = Project.objects.create(
            title='Department Project',
            description='Should be excluded',
            tech_stack=['python'],
            owner=self.department_owner,
            status='ACTIVE',
            team_member_count=1,
            team_capacity=3,
        )

        access_token, _ = generate_tokens(str(self.student.id))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_recommendations_rank_matching_projects_and_exclude_department(self):
        response = self.client.get('/api/projects/recommended/')

        self.assertEqual(response.status_code, 200)
        returned_ids = [item['id'] for item in response.data['data']]
        self.assertIn(str(self.best_project.id), returned_ids)
        self.assertIn(str(self.weaker_project.id), returned_ids)
        self.assertNotIn(str(self.department_project.id), returned_ids)
        self.assertEqual(returned_ids[0], str(self.best_project.id))
