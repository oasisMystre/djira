from typing import Callable, Iterator, TypeVar

from functools import partial

from asgiref.sync import async_to_sync

from django.db.models import Model, QuerySet
from django.db.models.signals import post_save, post_delete

from rest_framework.serializers import Serializer
from socketio import AsyncServer

from djira.settings import jira_settings

from .base_observer import Action, BaseObserver

T = TypeVar("T")


class ModelObserver(BaseObserver):
    def __init__(
        self,
        sender: Model,
        serializer_class: Serializer | None = None,
        server: AsyncServer | None = None,
    ):
        self._sender = sender
        self._serializer_class = serializer_class
        self._server = server or jira_settings.SOCKET_INSTANCE

    def connect(self):
        post_save.connect(
            self._post_save_receiver,
            self._sender,
            dispatch_uid=id(self),
        )

        post_delete.connect(
            self._post_delete_receiver,
            self._sender,
            dispatch_uid=id(self),
        )

    def _dispatcher(self, data, rooms: Iterator[str] | None):
        if hasattr(self, "_func"):
            return self._func(data, rooms)
            
        for room in rooms:
            async_to_sync(self._server.emit)(
                self.namespace,
                data,
                room=room,
            )  # emit to certain rooms subscribe

    def _post_save_receiver(self, instance: T, created: bool, **kwargs):
        if created:
            action = Action.CREATE
        else:
            action = Action.UPDATE

        self._dispatcher(
            self._serialize(action, instance),
            self._rooms(instance, action),
        )

    def _post_delete_receiver(self, instance: T, **kwargs):
        self._dispatcher(
            self._serialize(Action.DELETE, instance),
            self._rooms(instance, Action.DELETE),
        )

    def rooms(self, func: Callable[[QuerySet, Action], Iterator]):
        self._rooms = partial(func, self)
        return self

    @property
    def model_name(self):
        return self._sender._meta.model_name


def observer(
    sender: Model,
    override: bool = False,
    serializer_class: Serializer = None,
    server: AsyncServer = None,
):
    def _decorator(func):
        model_observer = ModelObserver(sender, serializer_class, server)

        if override:
            setattr(model_observer, "_func", func)

        model_observer.connect()

        return model_observer

    return _decorator
