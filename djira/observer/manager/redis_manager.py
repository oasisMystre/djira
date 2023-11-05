from typing import Callable, List, Optional

import json
from time import sleep
from functools import partial

from redis import Redis
from redis.client import PubSub
from redis.exceptions import RedisError

from .pubsub_manager import PubSubManager


class RedisManager(PubSubManager):
    """
    def on_scope_subscribe_to_room(self, payload):
      scope = Scope.from_json(payload)
      ....

    manager = RedisManager.connect_from_url(url)
    manager.listen(on_scope_subscribe_to_room)
    # add optional filter to reduce listen to data from pub
    """

    redis: Redis
    pubsub: PubSub

    def __init__(self, connect: Callable):
        self._connect = partial(connect, self)
        self._connect()

        super().__init__()

    @classmethod
    def connect_from_url(cls, url: str):
        def connect(self: "RedisManager"):
            self.redis = Redis.from_url(url)
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
            self.pubsub.subscribe(self.channel_key)

        return cls(connect)

    def _unsubscribe(self):
        return self.pubsub.unsubscribe()

    def _publish(self, data: dict):
        retry = False

        while True:
            try:
                if retry:
                    self._connect()
                return self.redis.publish(self.channel_key, json.dumps(data))
            except RedisError as error:
                if not retry:
                    retry = True
                    continue

                raise RedisError() from error

    def _listen(self):
        retry_sleep = 1
        connect = False

        while True:
            try:
                if connect:
                    self._connect()
                    retry_sleep = 1
                for message in self.pubsub.listen():
                    yield message
            except RedisError:
                connect = True
                sleep(retry_sleep)
                retry_sleep *= 2

                if retry_sleep > 60:
                    retry_sleep = 60

    def _on_data(self, payload: dict):
        return super()._on_data(
            json.loads(payload["data"]),
        )
