from typing import List
from django.dispatch import Signal

from socketio import AsyncServer

from django.db.models import Model

from rest_framework.serializers import Serializer

from djira.observer.signal_observer import SignalObserver

from .model_observer import ModelObserver


def model_observer(
    sender: Model,
    serializer_class: Serializer = None,
    server: AsyncServer = None,
):
    return ModelObserver(sender, serializer_class, server).connect()


def observer(
    signal: List[Signal] | Signal,
    sender: Model,
    serializer_class: Serializer = None,
    server: AsyncServer = None,
):
    model_observer = SignalObserver(sender, serializer_class, server)

    return model_observer.connect(signal, sender)
