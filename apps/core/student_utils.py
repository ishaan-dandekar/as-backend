from django.utils import timezone


DEPARTMENT_CODE_MAP = {
    '1': 'Civil',
    '2': 'Computer Engineering',
    '3': 'EXTC (Discontinued)',
    '4': 'IT',
    '5': 'Mechanical',
    '6': 'AIML',
    '7': 'Data Science',
}

ACADEMIC_STATUS_MAP = {
    1: 'FE',
    2: 'SE',
    3: 'TE',
    4: 'BE',
}


def derive_student_details_from_uid(uid: str):
    normalized_uid = str(uid or '').strip()
    if not normalized_uid.isdigit() or len(normalized_uid) < 5:
        return None

    try:
        admission_year = 2000 + int(normalized_uid[:2])
    except ValueError:
        return None

    department = DEPARTMENT_CODE_MAP.get(normalized_uid[4])

    return {
        'uid': normalized_uid,
        'admission_year': admission_year,
        'department': department,
    }


def calculate_academic_status(admission_year, current_time=None):
    if not admission_year:
        return None

    now = current_time or timezone.now()
    year_difference = now.year - int(admission_year)

    if now.month > 6:
        year_difference += 1

    if year_difference > 4:
        return 'Passout'

    if year_difference < 1:
        return 'FE'

    return ACADEMIC_STATUS_MAP.get(year_difference, 'FE')
