from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication


class LocalDevAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if not settings.DISABLE_AUTH_FOR_LOCAL_DEV:
            return None

        user = self.get_user()
        if not user:
            return None
        return user, None

    def get_user(self):
        User = get_user_model()
        dev_email = settings.LOCAL_DEV_AUTH_EMAIL

        if dev_email:
            user = User.objects.filter(email__iexact=dev_email, is_active=True).first()
            if user:
                return user

        return User.objects.filter(is_superuser=True, is_active=True).first()
