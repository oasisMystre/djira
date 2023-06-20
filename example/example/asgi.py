import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

application = get_asgi_application()

from socketio import ASGIApp

from djira.consumer import Consumer
from djira.settings import jira_settings

from .hooks import UserAPIHook

application = ASGIApp(
    jira_settings.SOCKET_INSTANCE,
    static_files={"/static": "/static"},
)

consumer = Consumer(jira_settings.SOCKET_INSTANCE)

consumer.register("users", UserAPIHook)

consumer.start()
