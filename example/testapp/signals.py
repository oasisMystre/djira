from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from rest_framework.authtoken.models import Token

User = get_user_model()


@receiver(post_save, sender=User)
def create_token(instance: User, created: bool, **kwargs):
    if created:
        token = Token.objects.create(user=instance)

        print(token.key)
