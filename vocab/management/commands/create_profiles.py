from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.apps import apps

Profile = apps.get_model('vocab', 'Profile')


class Command(BaseCommand):
    help = 'Create profiles for users without profiles'

    def handle(self, *args, **kwargs):
        users_without_profiles = User.objects.filter(profile__isnull=True)

        for user in users_without_profiles:
            Profile.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(f"Создан профиль для пользователя: {user}"))
