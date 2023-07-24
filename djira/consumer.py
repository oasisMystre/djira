from typing import Any, Dict, List

from asgiref.sync import sync_to_async

from socketio import Server
from socketio.exceptions import ConnectionRefusedError

from django.http import Http404
from django.contrib.auth.models import User, AnonymousUser

from rest_framework import status
from rest_framework.exceptions import APIException

from djira.authentication import BaseAuthentication

from .scope import Scope
from .settings import jira_settings

from .models import Realtime


class Consumer:
    from djira.hooks import APIHook

    _sids: Dict[int, str] = {}
    _hooks: Dict[str, "APIHook"] = {}
    _realtimes: Dict[str, Realtime] = {}

    authentication_classes = jira_settings.AUTHENTICATION_CLASSES
    middleware_classes = jira_settings.MIDDLEWARE_CLASSES

    def __init__(self, server: Server):
        self.server = server

    def register(self, namespace: str, api_hook: Any):
        setattr(api_hook, "namespace", namespace)
        self._hooks[namespace] = api_hook

    @property
    def sids(self):
        return self._sids

    @property
    def users(self) -> List[User | AnonymousUser]:
        return list(map(lambda realtime: realtime.user, self._realtimes))

    @property
    def realtime_users(self):
        return self._realtimes

    def get_realtime_user(self, sid: str):
        return self._realtimes.get(sid)

    def get_user(self, id: int):
        sid = self._sids.get(id)

        realtime = self._realtimes.get(sid)

        return realtime.user if realtime else None

    @property
    def namespaces(self):
        return dict.keys(self._hooks)

    def get_authentication_classes(self) -> List[BaseAuthentication]:
        return [
            authentication_class()
            for authentication_class in self.authentication_classes
        ]

    def get_middleware_classes(self):
        return [middleware_class() for middleware_class in self.middleware_classes]

    @property
    def authenticators(self):
        if not hasattr(self, "_authenticators"):
            self._authenticators = self.get_authentication_classes()

        return self._authenticators

    @property
    def middlewares(self):
        if not hasattr(self, "_middlewares"):
            self._middlewares = self.get_middleware_classes()

        return self._middlewares

    def start(self):
        @self.server.event
        async def connect(sid: str, environ: dict, auth: dict):
            for authenticator in self.authenticators:
                if not auth:
                    raise ConnectionRefusedError("auth required in client request")

                user = await authenticator.authenticate(sid, auth)

                if user:
                    realtime, created = Realtime.objects.get_or_create(user=user)
                    realtime.sid = sid
                    realtime.is_online = True
                    realtime.save(update_fields=["sid", "is_online"])

                    self._realtimes[sid] = realtime

                else:
                    raise ConnectionRefusedError()

        for event in self.namespaces:
            # To prevent closure assign namespace=event
            @self.server.on(event)
            async def on_event(sid: str, data: dict, namespace=event):
                scope = Scope(
                    sid,
                    namespace,
                    data,
                    self._users[sid],
                )

                for middleware in self.middlewares:
                    await sync_to_async(middleware)(scope)

                hook = self._hooks[namespace](self)(scope)

                try:
                    await hook.handle_action()
                except APIException as error:
                    await hook.emit(
                        error.get_full_details(),
                        status=error.status_code,
                    )
                except Http404 as error:
                    await hook.emit("Not found", status.HTTP_404_NOT_FOUND)

        @self.server.event
        def disconnect(sid: str):
            if sid in self._users:
                # broadcast user leave to subscriing listeners to this event
                user = self._users[sid]
                self.server.emit(
                    f"user_data_{user.id}", {"online": False}, skip_sid=sid
                )

                try:
                    del self._sids[user.id]
                    del self._users[sid]
                except KeyError as error:
                    pass
