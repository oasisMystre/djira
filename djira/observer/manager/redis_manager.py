from redis import Redis

from .base_manager import BaseManager


class RedisManager(BaseManager):
    def __init__(self, connection: Redis) -> None:
        self.connection = connection
    
    def send_data(
        self,
        data: dict,
        filter: dict | None,
    ):
        payload = dict(
            data=data,
            filter=filter,
        )

        return self.connection.publish(self.key, payload)

    
    def listen(self):
        """
        Todo Redis listen application
        """
        