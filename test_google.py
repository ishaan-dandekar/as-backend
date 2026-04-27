import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.users.views import _safe_user_payload
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(email__contains='24102115').first()
print(_safe_user_payload(u))
