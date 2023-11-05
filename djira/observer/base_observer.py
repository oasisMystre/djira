import asyncio
from enum import Enum
from functools import partial
from threading import Thread
from typing import Callable, Dict, Generator, List, Literal

from rest_framework.exceptions import NotFound

from django.db.models import QuerySet

from djira.scope import Scope
from djira.settings import jira_settings

from .manager import PubSubManager, Manager


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
    ] = {}  # all subscribing room scopes, used as context in serializing data

    @classmethod
    def listen_to_message(cls):
        if hasattr(cls, "manager"):
            return

        Manager: PubSubManager = jira_settings.DEFAULT_MANAGER

        if callable(Manager):
            cls.manager = Manager()
        else:
            cls.manager = Manager

        if cls.manager is None:
            cls.manager = Manager()

        cls.manager.subscribe(
            partial(cls._on_message, "subscribe"),
            lambda data: data.get("type") == "subscribe",
        )

        cls.manager.subscribe(
            partial(cls._on_message, "unsubscribe"),
            lambda data: data.get("type") == "unsubscribe",
        )

    @classmethod
    def _on_message(
        cls,
        type: Literal["subscribe", "unsubscribe"],
        data: dict,
    ):
        async def inner():
            try:
                room_name = data["room_name"]
                encode_scope = data["scope"]

                scope = await Scope.from_json(encode_scope)
                method = (
                    cls.subscribe_scope_to_room
                    if type == "subscribe"
                    else cls.unsubscribe_scope_from_room
                )
                method(scope, room_name)
            except Exception as e:
                pass  # no exception should be thrown

        thread = Thread(target=asyncio.run, args=(inner(),))
        thread.start()

    def serialize(self, action: Action, instance: QuerySet, context: dict):
        if hasattr(self, "_serializer"):
            return self._serializer(
                self,
                instance=instance,
                action=action,
                context=context,
            )
        elif self.serializer_class:
            return self.serializer_class(instance, context=context).data

        return {"pk": instance.pk}

    def serializer(self, func: Callable[[QuerySet, Action, Dict], dict | None]):
        """
        The result of this method is what is sent over the socket.
        """

        self._serializer = func
        return self

    def participants(self, func: Callable[[List[Scope], QuerySet], List[Scope]]):
        """
        a wrapper to get room participants do exclude here
        """

        self._participants = partial(func, self)

        return self

    def rooms(self, func: Callable[["BaseObserver", Action, QuerySet], Generator]):
        """ """

        self._rooms = partial(func, self)

        return self

    def subscribing_rooms(self, func: Callable[["BaseObserver", Scope], Generator]):
        """ """

        self._subscribing_rooms = partial(func, self)

        return self

    @classmethod
    def subscribe_scope_to_room(cls, scope: Scope, room_name: str):
        """
        Subscribe client to a room,
        Todo make subscription unique to a room by `namespace`, `sid`
        """

        if room_name not in cls.subscribing_scopes:
            cls.subscribing_scopes[room_name] = []

        cls.subscribing_scopes[room_name].append(scope)

    @classmethod
    def unsubscribe_scope_from_room(cls, scope: Scope, room_name: str):
        """
        unsubscribe a scope from a room
        """

        if room_name not in cls.subscribing_scopes:
            raise NotFound("can't unsubscribe, subscriber not found")

        scopes = cls.subscribing_scopes[room_name]

        indexes = [
            index
            for index, element in enumerate(scopes)
            if element.request_id == scope.request_id
        ]

        for index in indexes:
            scopes.remove(scopes[index])

        return scopes

    def get_participants(self, room_name):
        """
        Get all room participants
        """

        return self.subscribing_scopes.get(room_name, [])

    def _send_data(
        self,
        scope: Scope,
        room_name: str,
        type: Literal["subscribe", "unsubscribe"],
    ):
        return self.manager.send_data(
            {
                "scope": scope.to_json(),
                "room_name": room_name,
            },
            {"type": type},
        )

    def subscribe(self, scope: Scope):
        """
        This should be called to subscribe the current hook.
        """

        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(scope)

            for subscribing_room in subscribing_rooms:
                return self._send_data(scope, subscribing_room, "subscribe")
        else:
            return self._send_data(scope, self.model_name, "subscribe")

    def unsubscribe(self, scope: Scope):
        """
        This should be called to unsubscribe the current hook.
        """

        if hasattr(self, "_subscribing_rooms"):
            subscribing_rooms = self._subscribing_rooms(scope)

            for subscribing_room in subscribing_rooms:
                return self._send_data(scope, subscribing_room, "unsubscribe")
        else:
            return self._send_data(scope, self.model_name, "unsubscribe")

    @classmethod
    def disconnect(cls, predicate: Callable[[Scope], bool]):
        """
        unsubscribe using a predicate
        ```
        sid = "..."
        BaseObserver.disconnect(lambda scope: scope.sid == sid)
        ```
        return rooms user is disconnected from
        """
        rooms = set()
        for room, scopes in cls.subscribing_scopes.items():
            scopes_to_remove = []
            for scope in scopes:
                if predicate(scope):
                    scopes_to_remove.append(scope)
                    rooms.add(room)

            # Remove the scopes that match the predicate
            for scope in scopes_to_remove:
                scopes.remove(scope)

        return rooms
