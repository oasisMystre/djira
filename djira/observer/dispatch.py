from typing import Callable, List

from django.db.models import Model
from django.db.models.signals import ModelSignal
from django.dispatch import receiver as django_receiver
from django.utils.inspect import func_accepts_kwargs


from socketio import AsyncServer

from rest_framework.serializers import Serializer

from djira.settings import jira_settings


def receiver(
    signal: ModelSignal | List[ModelSignal],
    sender: Model = None,
    serializer: Serializer | Callable[[Model], dict] = None,
    dispatch_uid: str = None,
    server: AsyncServer = None,
):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal (or list of signals) and keyword arguments to connect.
    """

    def _decorator(func):
        # Check for **kwargs
        if not func_accepts_kwargs(receiver):
            raise ValueError(
                "Signal receivers must accept keyword arguments (**kwargs)."
            )

        @django_receiver(signal, sender=sender, dispatch_uid=dispatch_uid or id(func))
        def dispatcher(**kwargs):
            func(
                serializer=serializer,
                server=server or jira_settings.SERVER_INSTANCE,
                **kwargs,
            )

        return dispatcher

    return _decorator
