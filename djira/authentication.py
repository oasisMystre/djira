from django.contrib.auth.models import AbstractUser

from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed, NotFound

from djira.db import database_sync_to_async

class BaseAuthentication:
    def authenticate(self, sid: str, auth: dict) -> AbstractUser:
        raise NotImplemented(
            "override .authenticate in %s class" % self.__class__.__name__
        )


class TokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication.
    """
    @database_sync_to_async
    def authenticate(self, sid: str, auth):
        token = auth.get("token")

        if not token:
            raise AuthenticationFailed("token is required in auth dict")

        return self.authenticate_credential(token)

    def authenticate_credential(self, key: str) -> AbstractUser:
        try:
            token = Token.objects.get(key=key)

            return token.user
        except Token.DoesNotExist:
            raise NotFound("User not found")
        
