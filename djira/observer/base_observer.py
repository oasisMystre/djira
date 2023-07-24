from enum import Enum
from functools import partial
from typing import Callable, Dict, Generator, List

from django.db.models import QuerySet

from djira.scope import Scope


class Action(Enum):
    CREATE = "added"
    UPDATE = "modified"
    DELETE = "removed"


class BaseObserver:
    """
    This the the generic implementation of all observers
    """

    model_name: str

    subscribing_scopes: Dict[
        str, List[Scope]
    ] = {} # all subscribing room scopes, used as context in serializing data

    def serialize(self, action: Action, instance: QuerySet, context: dict):
        if hasattr(self, "_serializer"):
            return self._serializer(self, instance, action, context)
        elif self._serializer_class:
            return self._serializer_class(instance, context=context).data

        return {"pk": instance.pk}

    def serializer(self, func: Callable[[QuerySet, Action, Dict], dict | None]):
        """
        The result of this method is what is sent over the socket.
        """

        self._serializer = func
        return self

    def rooms(self, func: Callable[["BaseObserver", Action, QuerySet], Generator]):
        """ """

        self._rooms = partial(func, self)

        return self

    def subscribing_rooms(self, func: Callable[["BaseObserver", Scope], Generator]):
        """ """

        self._subscribing_rooms = partial(func, self)

        return self

    def subscribe_scope_to_room(self, scope: Scope, room_name: str):
        """
        Subscribe client to a room,
        Todo make subscription unique to a room by `namespace`, `sid`
        """

        if room_name not in self.subscribing_scopes:
            self.subscribing_scopes[room_name] = {}

            self.subscribing_scopes[room_name].append(scope)

        return self._server.enter_room(scope.sid, room_name)

    def unsubscribe_scope_from_room(self, scope: Scope, room_name: str):
        """
        unsubscribe a scope from a room
        """

        if room_name not in self.subscribing_rooms:
            raise Exception

        scopes = self.subscribing_scopes[room_name]

        indexes = [
            index
            for index, element in enumerate(scopes)
            if element.sid == scope.sid and element.namespace == scope.namespace
        ]

        for index in indexes:
            scopes.remove(scopes[index])
            self._server.leave_room(scope.sid, room_name)

    def get_participants(self, room_name):
        """
        Get all room participants
        """
        print(self.subscribing_scopes)

        return self.subscribing_scopes.get(room_name, [])

    async def subscribe(self, scope: Scope):
        """
        This should be called to subscribe the current hook.
        """

        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(self, scope)

            for subscribing_room in subscribing_rooms:
                return self.subscribe_scope_to_room(scope, subscribing_room)
        else:
            return self.subscribe_scope_to_room(scope, self.model_name)

    async def unsubscribe(self, scope: Scope):
        """
        This should be called to unsubscribe the current hook.
        """

        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(self, scope)

            for subscribing_room in subscribing_rooms:
                self.unsubscribe_scope_from_room(scope, subscribing_room)
        else:
            self.unsubscribe_scope_from_room(scope, self.model_name)
