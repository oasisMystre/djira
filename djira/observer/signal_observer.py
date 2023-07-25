from functools import partial
from typing import Any, Callable, TypeVar

from asgiref.sync import async_to_sync

from django.dispatch import Signal

from socketio import AsyncServer

from django.db.models import Model

from rest_framework.serializers import Serializer

from djira.scope import Scope
from djira.settings import jira_settings
from djira._utils import build_context_from_scope

from .base_observer import Action, BaseObserver

T = TypeVar("T")


class SignalObserver(BaseObserver):
    """
    Generic signal observer
    """

    def __init__(
        self,
        sender: Model,
        serializer_class: Serializer = None,
        server: AsyncServer = None,
    ):
        self.sender = sender
        self.serializer_class = serializer_class
        self.server = server or jira_settings.SOCKET_INSTANCE

    def connect(self, signal: Signal, sender: Any = None):
        """
        Connect receiver to sender for signal.
        """

        def _decorator(func: Callable):
            signal.connect(
                partial(func, self),
                sender=sender,
                dispatch_uid=id(self),
            )

            return self

        return _decorator

    def dispatch(self, action: Action, instance: T, **kwargs):
        """
        Dipatch event to all subscribing clients
        """

        rooms = self._rooms(action=action, instance=instance, **kwargs)

        for room in rooms:
            scopes = self.get_participants(room)
            for scope in scopes:
                self.emitter(
                    action=action,
                    instance=instance,
                    scope=scope,
                    data=self.serialize(
                        action=action,
                        instance=instance,
                        context=build_context_from_scope(scope),
                    )
                    ** kwargs,
                )

    def emitter(self, action: Action, scope: Scope, data: dict, **kwargs):
        """
        Send message to clients
        """

        return async_to_sync(self.server.emit)(
            scope.namespace,
            data=dict(
                method="SUBSCRIPTION",
                action=scope.action,
                type=action.value,
                requestId=scope.request_id,
                data=data,
            ),
            to=scope.sid,
        )

    @property
    def model_name(self):
        return self.sender._meta.model_name
