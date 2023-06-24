from django.contrib.auth import get_user_model

from rest_framework import status

from djira.hooks import ModelAPIHook

from djira.decorators import action

from djira.observer import observer
from djira.observer.base_observer import Action

from djira.scope import Scope

from .serializers import UserSerializer

User = get_user_model()


class UserAPIHook(ModelAPIHook):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @observer(User, serializer=UserSerializer)
    def user_observer(self, **kwargs):
        pass

    @user_observer.rooms
    def user_rooms(self, instance: User, action: Action):
        yield "%s_%d" % (self.model_name, instance.pk)

    @user_observer.subscribing_rooms
    def user_subsribing_rooms(self, scope: Scope):
        yield "%s_%s" % (self.model_name, scope.user.id)

    @action(methods=["SUBSCRIPTION"])
    async def subscribe_user(self):
        """
        check permission here
        """
        await self.user_observer.subscribe(self.scope)

        return self.emit({})