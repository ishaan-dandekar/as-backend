from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.authentication import generate_tokens


User = get_user_model()


class UserProfileBranchYearTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student1',
            email='student1@apsit.edu.in',
            password='testpass123',
            role='STUDENT',
        )
        access_token, _ = generate_tokens(str(self.user.id))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_student_can_update_branch_and_year(self):
        response = self.client.patch(
            '/api/user/profile',
            {'branch': 'CE', 'year': 'TE'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.branch, 'CE')
        self.assertEqual(self.user.year, 'TE')

    def test_invalid_branch_is_rejected(self):
        response = self.client.patch(
            '/api/user/profile',
            {'branch': 'Unknown'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('branch must be one of', response.data['message'])


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
