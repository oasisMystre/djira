from django.db.models import Model
from django.db.models.signals import post_save, post_delete
from rest_framework.serializers import Serializer
from socketio import AsyncServer

from .base_observer import Action
from .signal_observer import SignalObserver


class ModelObserver(SignalObserver):
    def __init__(
        self,
        sender: Model,
        serializer_class: Serializer = None,
        server: AsyncServer = None,
    ):
        super().__init__(sender, serializer_class, server)

    def connect(self):
        post_save.connect(
            self.post_save_receiver,
            self.sender,
            dispatch_uid=id(self),
        )

        post_delete.connect(
            self.post_delete_receiver,
            self.sender,
            dispatch_uid=id(self),
        )

        return self

    def post_save_receiver(self, created: bool, **kwargs):
        if created:
            action = Action.CREATE
        else:
            action = Action.UPDATE

        self.dispatcher(action=action, created=created, **kwargs)

    def post_delete_receiver(self, **kwargs):
        self.dispatcher(action=Action.DELETE, **kwargs)
