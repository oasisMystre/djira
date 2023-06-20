from asgiref.sync import async_to_sync

from django.db.models.query import QuerySet

from rest_framework.serializers import ModelSerializer

from djira.settings import jira_settings
from djira.pagination import BasePagination

from .generics import GenericAPIHook

from .mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)


class APIHook(GenericAPIHook):
    pagination_class: BasePagination = jira_settings.DEFAULT_PAGINATION_CLASS

    @property
    def paginator(self):
        """
        The paginator instance associated with the hook, or `None`.
        """

        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()

        return self._paginator

    def paginate_queryset(self, queryset: QuerySet):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """

        if self.paginator is None:
            return None

        return self.paginator.paginate_queryset(queryset, self.scope)

    def paginate_response(self, data):
        return self.paginator.paginate_response(data)

    def emit(self, data: dict, status=200, room_id: str | None = None):
        scope = self.scope
        room_id = room_id or scope.sid

        return async_to_sync(self.server.emit)(
            self.scope.namespace,
            {
                "status": status,
                "action": scope.action,
                "requestId": scope.request_id,
                "data": data,
            },
        )


class ReadOnlyAPIHook(
    APIHook,
    ListModelMixin,
    RetrieveModelMixin,
):
    serializer_class: ModelSerializer = None


class ModelAPIHook(
    APIHook,
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
):
    serializer_class: ModelSerializer = None
