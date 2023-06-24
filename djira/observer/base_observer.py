from enum import Enum
from typing import Callable

from django.db.models import QuerySet

from djira.scope import Scope


class Action(Enum):
    CREATE = "added"
    UPDATE = "modified"
    DELETE = "removed"


class BaseObserver:
    """ """

    def _serialize(self, action: Action, instance: QuerySet):
        body = {}

        if hasattr(self, "_serializer"):
            body = self._serializer(instance, action)
        elif self._serializer_class:
            body = self._serializer_class(instance).data
        else:
            body = {"pk": instance.pk}

        return dict(
            method="SUBSCRIPTION",
            action=self.action,
            type=action.value,
            data=body,
        )

    def serializer(self, func: Callable[[QuerySet, Action], dict | None]):
        """
        The result of this method is what is sent over the socket.
        """

        self._serializer = func
        return self

    def subscribing_rooms(self, func):
        self._subscribing_rooms = func

        return self

    async def subscribe(self, scope: Scope):
        """
        This should be called to subscribe the current hook.
        """
        if not hasattr(self, "namespace"):
            setattr(self, "action", scope.action)
            setattr(self, "namespace", scope.namespace)

        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(self, scope)

            for subscribing_room in subscribing_rooms:
                return self._server.enter_room(scope.sid, subscribing_room)
        else:
            return self._server.enter_room(scope.sid, self.model_name)

    async def unsubscribe(self, scope: str = None):
        """
        This should be called to unsubscribe the current hook.
        """
        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(self, scope)

            for subscribing_room in subscribing_rooms:
                self._server.leave_room(subscribing_room)
        else:
            self._server.leave_room(self.model_name)
