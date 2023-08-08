from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Realtime(models.Model):
    """
    User realtime connection database cache instance
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )
    is_online = models.BooleanField(
        default=False,
    )
    sid = models.TextField(
        null=True,
        blank=False,
    )

    def __str__(self):
        return self.user.email
