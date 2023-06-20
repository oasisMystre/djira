from datetime import time
from typing import Any, Dict, Literal

from django.http import QueryDict
from django.contrib.auth.models import User, AnonymousUser


class Scope:
    def __init__(
        self,
        sid: str,
        namespace: str,
        raw_data: dict,
        user: User | AnonymousUser = None,
    ):
        self._sid = sid
        self._namespace = namespace
        self._user = user or AnonymousUser()
        self._raw_data = raw_data

    @property
    def request_id(self):
        return self._raw_data.get("requestId", time().isoformat)

    @property
    def sid(self):
        return self._sid

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def headers(self) -> Dict[str, Any]:
        return self._raw_data.get("headers", {})

    @property
    def user(self):
        return self._user

    @property
    def action(self) -> Literal["list", "retrieve", "update"]:
        return self._raw_data.get("action")

    @property
    def method(self) -> Literal["request", "subcribe", "stream"]:
        return self._raw_data.get("method", "request")

    @property
    def data(self):
        return self._raw_data.get("data", {})

    @property
    def query(self):
        filter = self._raw_data.get("query", {})
        query = QueryDict(None, mutable=True)
        query.update(filter)

        return query
