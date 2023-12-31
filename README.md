# Djira 

Create a websocket api server quickly with ready made api consumer 

For javascript/typescript client check [jira](https://github.com/oasisMystre/jira)

## Getting started 

Install djira from pip

```bash
pip install drf-sio
```

update your `settings.py` config
```py
INSTALLED_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "djira.apps.DJiraConfig",
]
```

> drf-sio is django socket io for short

## Features

- [x] Custom features extendable 
- [x] Support Load balancer by default using pubsub techniques provide `RedisManager` interface by default you can implement yours by extending the `PubSubManager` class
- [x] Support listening to database changes using django-signals and publish to subscribing clients
- [x] Django permission extended using the `BasePermission` class with our default precode classes
- [x] Perform rest actions list, retrieve, update delete using socketio
- [x] Pagination supported when using our rest-socket-api


## Hooks 
Hooks are the api interface, which contains the actions methods 

This are like native DRF Viewsets but tailored for djira 

> Support use of mixins 

```py
from djira.hooks import ModelAPIHook 
from djira.decorators import action

class UserAPIHook(ModelAPIHook):
    """
    This implement the create, list, retrieve, update actions
    """
    queryset = User.objects.all()
    serializer = UserSerializer()

    # override the namespace by passing in namespace args
    # by default GET action is only allow for this namespace, to override pass in the actions args
    @action(actions=["GET"])
    def set_password(self, scope: Scope):
        data = scope.data 
        user = scope.user 

        user.set_password(data.get("password"))

        return self.emit("users", { self.get_serializer(user).data })
```

Using mixin method 

```py
from djira.hooks import APIHook
from djira.mixins import CreateModelMixin 

class UserAPIHook(APIHook, CreateModelMixin):
    ...
```

Or use a route with multiple actions 

```py
import djira.hooks import APIHook 

class UserAPIHook(APIHook):
    @action(actions=["GET", "POST"]):
    def users_route(self, scope: Scope):
        if scope.action === "GET":
            pass  
```

## Observers
Listen to database changes and emit data to subscribers

```py
from djira.decorators import action
from djira.hooks import ModelAPIHook 

class UserAPIHook(ModelAPIHook):
    queryset = User.objects.all()
    serializer = UserSerializer()

    @model_observer(User, UserSerializer) # serializer_class is optional. Note, no context is passed to serializer
    def user_subscriber(self, data: dict, rooms: Iterator[str]):
        return None # return None to automatically send events or manually send events 

    @user_subsriber.rooms 
    def create_rooms(self, instance: User):
        """
        Not required leave this to use the default which is the model instance name
        """
        yield f"{instance.model.model_name}__{instance.pk}" # All create, list, events will be sent client that subscribe to this room_id

    @user_subscriber.subscribing_rooms
    def subscribing_user_rooms(self, scope: Scope):
        """
        Required if you need user to subscribe to only a specific room for changes
        """
        yield f"user__{scope.user.pk}" # This is equivalent to object permission, since only user that loggedIn as this user can subscribe to this room
    
    # This is optional, defaults to serializer_class or {pk}
    # This is neccessary since signals don't provide a context to serializers
    @user_subscriber.serializer
    def user_serializer(self, action: Action, instance: User):
        """
        Return data to return to all subscribing user
        """
        return {
            "id": instance.id,
            "username": instance.name,
        }

    # raise exception if try to subscribe from an action that is not a subscription
    # send a request to subscribe_user actions to subscribe to user_subscriber 
    @action(methods=["POST"])
    async def subscribe_user(self, scope: Scope):
        await user_subscriber.subscribe(scope)

```

Another example using more concise implementation

```py
from typing import Dict, Set

from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed

from djira.decorators import action
from djira.hooks import APIHook
from djira.observer import observer, model_observer
from djira.observer.base_observer import Action
from djira.observer.model_observer import ModelObserver
from djira.scope import Scope

from .models import Publication

User = get_user_model()


class UserAPIHook(APIHook):
    user_observer = model_observer(User, UserSerializer)()

    @user_observer.rooms
    def user_rooms(cls: ModelObserver, action: Action, instance: User):
        yield f"user__{instance.id}"

    @user_observer.subscribing_rooms
    def subscribing_rooms(cls: ModelObserver, scope: Scope):
        yield f"user__{scope.user.id}"

    @action(methods=["SUBSCRIPTION"])
    def subscribe(self, scope: Scope):
        return self.user_observer.subscribe(scope)

    @action(methods=["SUBSCRIPTION"])
    def unsubscribe(self, scope: Scope):
        return self.user_observer.unsubscribe(scope)


class PublicationAPIHook(APIHook):
    @observer(m2m_changed, Publication.users.through)
    def publication_observer(
        self: ModelObserver, 
        action: str, 
        **kwargs
    ):
        """
        send event only when action is `post_add`
        """
        match action:
            "post_add":
                return self.dispatch(Action.UPDATE, **kwargs) 

    @publication_observer.serializer
    def publication_serializer(
        cls: ModelObserver, action: Action, instance: Publication
    ):
        return dict(id=instance.id, name=instance.name)
    

    @publication_observer.rooms
    def user_rooms(cls: ModelObserver, action: Action, instance: User):
        yield f"user__{instance.id}"

    @publication_observer.subscribing_rooms
    def subscribing_rooms(cls: ModelObserver, scope: Scope):
        yield f"user__{scope.user.id}"

    @action(methods=["SUBSCRIPTION"])
    def subscribe(self, scope: Scope):
        return self.publication_observer.subscribe(scope)

    @action(methods=["SUBSCRIPTION"])
    def unsubscribe(self, scope: Scope):
        return self.publication_observer.unsubscribe(scope)
```

## Dispatchers 

This is a wrapper to `django.dispatch` module to support `server.emit` from signals 

```py
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model 

from djira.observer.dispatch import receiver

User = get_user_model()

@receiver(
    post_save,
    User,
    serializer=lambda instance: {"id": instance.id } # can be rest_framework serializer
)
def on_user_created(instance: User, created: bool, server: AsyncServer, serializer, **kwargs):
    if created:
        server.emit("user", {
            "status": 201,
            "action": "subscription",
            "data": serializer(instance),
        })
```


## Consumer 

Register a hook with a event

```py
from socketio import ASGIApp

from djira.consumer import Consumer
from djira.settings import jira_settings

from .hooks import UserAPIHook

application = ASGIApp(jira_settings.SOCKET_INSTANCE)

consumer = Consumer(jira_settings.SOCKET_INSTANCE)

consumer.register("user", UserAPIHook) 

consumer.start() # this is important to start the socket server
```

## Settings 

Override jira default settings 

update your `settings.py` 
```
DJIRA_SETTINGS = {}
```

###  SOCKET_INSTANCE
This override the default socketio instance, import module string 

```py
DJIRA_SETTINGS = {
    "SOCKET_INSTANCE": "example.socket.sio",
}
```

### AUTHENTICATION_CLASSES
Authentication classes, this is run on every client connection.

Extend from djira `BaseAuthentication` Class to implement your own authentication logic

Jira has a extend authentication class from `rest_framework.authentication`

```py
DJIRA_SETTINGS = {
    "AUTHENTICATION_CLASSES": ["jira.authentication.TokenAuthentication"],
}
```

### DEFAULT_MANAGER
This is used to manage subscriptions when using multiple server process like a load balancer.
When a user subscribe or unsubscribe an event is sent to all processes using our pubsub mechanism.

```py
#manager.py
from djira.observer.manager import RedisManager 
manager = RedisManager.from_url(...)

#settings.py
DJIRA_SETTINGS = {
    "DEFAULT_MANAGER": "example.manager.manager"
}
```

> This is optional and uses a django signal callback. Note this callback can't be used for a load balancing mechanism

### PERMISSION_CLASSES

Permission classes, `can_connect` method is called on client connection
`has_permission` checks if a client can connect to a namespace or socketio `on_event` hook fired 
`has_object_permission` check if a client has permission to a model instance

> Defaults to `AllowAny` permission class if none provided 

```py
from djira.permissions import BasePermission 

class AllowAny(BasePermission):
    def can_connect(self, sid, environ, auth):
        return True 

    def has_permission(self, scope: Scope):
        return True 
        
    def has_object_permission(self, scope: Scope, instance: Model):
        return True

```

In your `settings.py` update or add your permission class

```py
DJIRA_SETTINGS = {
    "PERMISSION_CLASSES": ["jira.permissions.AllowAny"]
}
```

### MIDDLEWARE_CLASSES

Mutate scopes using middleware classes and perform custom mutation to response

```py
class ScopeInterceptorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response 

    def __call__(self, scope: Scope):
        # do somethind here e.g mutate scope 
        setattr(scope, "business", ...)

        return self.get_response(scope)
```

In your `settings.py` add or update your middleware class 

```py
DJIRA_SETTINGS = {
    "MIDDLEWARE_CLASSES": ["example.middlewares.ScopeInterceptorMiddleware"]
}
```

### DEFAULT_PAGINATION_CLASS
Don't update this if you don't know about paginations,

This default to jira default pagination class `PagePagination`,
To implement yours extend `BasePagination` class from djira

```py
from djira.pagination import BasePagination

class LimitOffsetPagination(BasePagination):
    ... 
```

In your `settings.py` add or update your default pagination class

```py
DJIRA_SETTINGS = {
    "DEFAULT_PAGINATION_CLASS": "example.pagination.LimitOffsetPagination",
}
```

### PAGE_SIZE

Set your page size 

```py
DJIRA_SETTINGS = {
    "PAGE_SIZE": 16,
} # default
```

## Develop and contribute

Library is still in development state contributors are welcome 

tools/

The tools directory contains scripts that makes developing easier for you 

tools/flush.py

A recursive script that clean and remove temp files from the project directory 


# PR Reviews and commit message

New features are suspended and added to new version roadmap
Make sure your commit message includes your fix and detail or new feature add, and steps 

Typo fix should not contain verbose commit messages 
