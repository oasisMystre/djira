from rest_framework import status
from rest_framework.serializers import Serializer

from djira.decorators import action


class CreateModelMixin:
    @action()
    def create(self):
        """
        Create action.
        """

        serializer = self.get_serializer(data=self.scope.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return self.emit(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer: Serializer):
        serializer.save()


class ListModelMixin:
    """
    List a queryset.
    """

    @action()
    def list(self):
        """
        List action.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(queryset, many=True)

            return self.emit(self.paginate_response(serializer.data))

        serializer = self.get_serializer(queryset, many=True)

        return self.emit(serializer.data)


class RetrieveModelMixin:
    @action()
    def retrieve(self):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return self.emit(serializer.data)


class UpdateModelMixin:
    """
    Update model mixin
    """

    @action()
    def update(self):
        """
        Retrieve action.
        """

        data = self.scope.data

        instance = self.get_object()

        serializer = self.get_serializer(
            instance=instance,
            data=data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return self.emit(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save()


class DestroyModelMixin:
    """Delete model mixin"""

    @action()
    def delete(self):
        """Retrieve action."""

        instance = self.get_object()

        self.perform_delete(instance)
        return self.emit(None, status.HTTP_204_NO_CONTENT)

    def perform_delete(self, instance):
        instance.delete()
