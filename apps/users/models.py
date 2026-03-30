from django.conf import settings
from django.db import models


class UserProfileMeta(models.Model):
	"""Stores profile fields not guaranteed to exist on the active auth user model."""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='profile_meta',
	)
	profile_picture_url = models.URLField(blank=True, null=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'User profile metadata'
		verbose_name_plural = 'User profile metadata'


def _has_concrete_profile_picture_field(user):
	return any(
		field.name == 'profile_picture_url' and getattr(field, 'concrete', False)
		for field in user._meta.get_fields()
	)


def get_user_profile_picture_url(user):
	if _has_concrete_profile_picture_field(user):
		return getattr(user, 'profile_picture_url', None)

	try:
		meta = user.profile_meta
	except UserProfileMeta.DoesNotExist:
		return None

	if meta:
		return meta.profile_picture_url
	return None


def set_user_profile_picture_url(user, picture_url):
	if _has_concrete_profile_picture_field(user):
		if getattr(user, 'profile_picture_url', None) != picture_url:
			user.profile_picture_url = picture_url
			user.save(update_fields=['profile_picture_url'])
		return

	profile_meta, _ = UserProfileMeta.objects.get_or_create(user=user)
	if profile_meta.profile_picture_url != picture_url:
		profile_meta.profile_picture_url = picture_url
		profile_meta.save(update_fields=['profile_picture_url', 'updated_at'])
