from django.db.models import QuerySet

from djira.scope import Scope


class BasePermission:
    def can_connect(self, sid, environ, auth):
        raise NotImplemented(
            "override `.can_connect` method in %s class" % self.__class__.__name__
        )

    def has_permission(self, scope: Scope, hook):
        raise NotImplemented(
            "override `.has_permission` method in %s class" % self.__class__.__name__
        )

    def has_object_permission(self, scope: Scope, instance: QuerySet):
        raise NotImplemented(
            "override `.has_object_permission` method in %s class"
            % self.__class__.__name__
        )


class AllowAny(BasePermission):
    def can_connect(self, sid, environ, auth):
        return True

    def has_permission(self, scope: Scope, hook):
        return True

    def has_object_permission(self, scope: Scope, instance: QuerySet):
        return True
