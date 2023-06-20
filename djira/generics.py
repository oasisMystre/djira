from typing import Any, Dict, List

from socketio import AsyncServer

from django.db.models import QuerySet, Model
from django.shortcuts import get_object_or_404

from url_filter.filtersets import ModelFilterSet

from rest_framework.serializers import Serializer
from rest_framework.exceptions import (
    NotFound,
    MethodNotAllowed,
    PermissionDenied,
)

from djira.scope import Scope
from djira.settings import jira_settings


class APIHookMetaclass(type):
    """
    Metaclass that records action methods
    """

    def __new__(mcs, name, bases, body):
        cls = type.__new__(mcs, name, bases, body)

        cls.available_actions = {}

        for method_name in dir(cls):
            attr = getattr(cls, method_name)
            kwargs = getattr(attr, "kwargs", {})
            is_action = kwargs.get("action", False)

            actions = kwargs.pop("actions", [])
            name = kwargs.pop("name", method_name)

            if is_action:
                cls.available_actions[name] = actions

        return cls


class BaseAPIHook(metaclass=APIHookMetaclass):
    """ """

    def __init__(self, server: AsyncServer | None = None, **kwargs):
        self.kwargs = kwargs
        self.server = server or jira_settings.SOCKET_INSTANCE

    def __call__(self, scope: Scope):
        self.scope = scope
        self.check_permissions()

        return self

    @property
    def permissions(self):
        """
        Instantiates and returns the list of permissions that this hook requires.
        """
        if not hasattr(self, "_permissions"):
            self._permissions = [permission() for permission in self.permission_classes]

        return self._permissions

    def check_permissions(self):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the scope is not permitted.
        """

        for permission in self.permissions:
            if not permission.has_permission(self.scope, self):
                self.permission_denied(
                    self.scope,
                    message=getattr(permission, "message", None),
                    code=getattr(permission, "code", None),
                )

    def check_object_permissions(self, instance: Model):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """

        for permission in self.permissions:
            if not permission.has_object_permission(self.scope, instance):
                self.permission_denied(
                    message=getattr(permission, "message", None),
                    code=getattr(permission, "code", None),
                )

    async def handle_action(self):
        action = self.scope.action
        namespace = self.scope.namespace

        if namespace in self.available_actions:
            actions = self.available_actions[namespace]

            if action in actions:
                if hasattr(self, self.scope.action):
                    await getattr(self, namespace)()
            else:
                self.action_not_allowed()
        else:
            return NotFound(
                "%s event don't have a namespace named %s" % (action, namespace)
            )

    def action_not_allowed(self):
        """
        If `scope.action` does not correspond to a handler actions,
        determine what kind of exception to raise.
        """
        raise MethodNotAllowed(self.scope.action)

    def permission_denied(self, message: str = None, code: int = None):
        """
        If scope is  permitted, determine what kind of exception to raise.
        """

        raise PermissionDenied(detail=message, code=code)


class GenericAPIHook(BaseAPIHook):
    """
    Base class for all other generic hooks.
    """

    filter_fields: List[str] = None
    queryset: QuerySet | List[Any] = None

    serializer_class: Serializer = None

    lookup_field = "pk"
    lookup_query_kwarg: str = None

    permission_classes = jira_settings.PERMISSION_CLASSES

    def get_filter_class(self):
        """
        build api class from hook
        """
        assert isinstance(
            self.queryset, QuerySet
        ), "`.queryset` must be a instance of `Queryset`"

        class FilterClass(ModelFilterSet):
            class Meta:
                fields = "__all__"
                model = self.queryset.model

        return FilterClass

    def filter_queryset(self, queryset: QuerySet):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default URL filter.
        """

        queryset = self.get_queryset()
        filter_set = self.get_filter_class()(data=self.scope.query, queryset=queryset)

        queryset = filter_set.filter()

        return queryset

    def get_serializer(
        self,
        instance: QuerySet | None = None,
        *args,
        **kwargs,
    ) -> Serializer:
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()

        return serializer_class(instance=instance, *args, **kwargs)

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.
        """

        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method." % self.__class__.__name__
        )

        return self.serializer_class

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Extra context provided to the serializer class.
        """

        return {"scope": self.scope, "hook": self}

    def get_object(self) -> Model:
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """

        queryset = self.filter_queryset(queryset=self.get_queryset())

        # Perform the lookup filtering.
        lookup_query_kwarg = self.lookup_query_kwarg or self.lookup_field

        assert lookup_query_kwarg in self.scope.query, (
            "Expected hook %s to be called with a Query keyword argument "
            'named "%s". Fix your Query conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_query_kwarg)
        )

        instance = get_object_or_404(
            queryset,
            **{self.lookup_field: self.scope.query[lookup_query_kwarg]},
        )

        self.check_object_permissions(instance)

        return instance

    def get_queryset(self):
        """
        This can be an iterator or queryset, defaults to `self.queryset`,
        """
        assert self.queryset is not None, (
            "%s should include a  .queryset attribute or override the get_queryset method"
            % self.__class__.__name__
        )

        queryset = self.queryset

        # Ensure querset is re-eveluate on each request
        return queryset.all() if isinstance(queryset, QuerySet) else queryset

