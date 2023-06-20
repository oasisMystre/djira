from typing import Any, Dict, List

from socketio import Server
from socketio.exceptions import ConnectionRefusedError

from django.contrib.auth.models import User, AnonymousUser

from djira.authentication import BaseAuthentication

from .scope import Scope
from .settings import jira_settings


class Consumer:
    from djira.hooks import APIHook

    _hooks: Dict[str, "APIHook"] = {}
    _user: Dict[str, User or AnonymousUser] = {}

    authentication_classes = jira_settings.AUTHENTICATION_CLASSES

    def __init__(self, server: Server):
        self.server = server

    def register(self, namespace: str, api_hook: Any):
        self._hooks[namespace] = api_hook

    @property
    def namespaces(self):
        return dict.keys(self._hooks)

    def get_authentication_classes(self) -> List[BaseAuthentication]:
        return [
            authentication_class()
            for authentication_class in self.authentication_classes
        ]

    @property
    def authenticators(self):
        if not hasattr(self, "_authenticators"):
            self._authenticators = self.get_authentication_classes()

        return self._authenticators

    def start(self):
        @self.server.event
        async def connect(sid: str, environ: dict, auth: dict):
            self._user[sid] = AnonymousUser()

            for authenticator in self.authenticators:
                if not auth:
                    raise ConnectionRefusedError("auth required in client request")

                user = await authenticator.authenticate(sid, auth)

                if user:
                    self._user[sid] = user
                else:
                    raise ConnectionRefusedError()

        for namespace in self.namespaces:

            @self.server.on(namespace)
            async def on_event(sid: str, data: dict):
                print(data)
                scope = Scope(
                    sid,
                    namespace,
                    data,
                    self._user[sid],
                )

                await self._hooks[namespace]()(scope).handle_action()

        @self.server.event
        def disconnect(sid: str):
            if sid in self._user:
                del self._user[sid]
