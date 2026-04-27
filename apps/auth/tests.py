from django.test import TestCase
from unittest.mock import patch
from datetime import datetime
from django.utils import timezone

from apps.core.student_utils import calculate_academic_status, derive_student_details_from_uid


class StudentUidDerivationTests(TestCase):
    def test_uid_derivation_extracts_permanent_student_fields(self):
        details = derive_student_details_from_uid('24102115')

        self.assertEqual(
            details,
            {
                'uid': '24102115',
                'admission_year': 2024,
                'department': 'Computer Engineering',
            },
        )

    @patch('apps.core.student_utils.timezone.now')
    def test_academic_status_advances_after_june(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 5, 20, 12, 0, 0))
        self.assertEqual(calculate_academic_status(2024), 'SE')

        mock_now.return_value = timezone.make_aware(datetime(2026, 7, 20, 12, 0, 0))
        self.assertEqual(calculate_academic_status(2024), 'TE')
