from django.contrib.auth.models import User
from .models import Profile, PersDict

class EmailAuthBackend:
    """
    Аутентифицировать посредством адреса электронной почты.
    """

    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
            return None
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def create_profile(backend, user, *args, **kwargs):
    """
    Создать профиль пользователя для социальной аутентификации
    """
    # Profile.objects.get_or_create(user=user)
    profile, created = Profile.objects.get_or_create(user=user)

    # Создание персонального словаря, если профиль был создан
    if created:
        PersDict.objects.get_or_create(user=user)

    return {'profile': profile, 'created': created}
