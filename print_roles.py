import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(email__contains='24102115').first()
if u:
    u.role = 'DEPARTMENT'
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print(f"Updated User: {u.email}, Role: {u.role}")
else:
    print("User not found")
