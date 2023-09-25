from datetime import time
from typing import Any, Dict, Literal

from urllib.parse import urljoin

from django.http import QueryDict
from django.contrib.auth.models import User, AnonymousUser
from .models import Realtime

from .typing import Method


class Scope:
    def __init__(
        self,
        sid: str,
        namespace: str,
        raw_data: dict,
        user: User = None,
        session=None,
    ):
        self._sid = sid
        self._namespace = namespace
        self._user = user
        self._raw_data = raw_data
        self._session = session

    def __getattr__(self, __name: str) -> Any:
        match __name:
            case "GET":
                return self.query
            
        # return None if not define    
        return self._raw_data.get(__name)

    @property
    def environ(self):
        return self._session["environ"]

    @property
    def request_id(self):
        return self._raw_data.get("requestId", time().isoformat())

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
    def action(self) -> str:
        return self._raw_data.get("action")

    @property
    def method(self) -> Method:
        return self._raw_data.get("method", "GET")

    @property
    def data(self):
        return self._raw_data.get("data", {})

    @property
    def query(self):
        filter = self._raw_data.get("query", {})
        query = QueryDict(None, mutable=True)
        query.update(filter)

        return query

    def build_absolute_uri(self, url: str):
        return urljoin(
            f"{self.environ['wsgi.url_scheme']}://{self.environ['HTTP_HOST']}",
            url,
        )
