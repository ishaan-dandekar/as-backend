import os

import django
from django.contrib.auth import get_user_model


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    from apps.users.views import _safe_user_payload

    User = get_user_model()
    user = User.objects.filter(email__contains="24102115").first()
    print(_safe_user_payload(user))


if __name__ == "__main__":
    main()
