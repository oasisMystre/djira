from threading import Thread
from typing import Generator
from .base_manager import BaseManager


class PubSubManager(BaseManager):
    def __init__(self):
        super().__init__()

        self.initialize()

    def send_data(
        self,
        data: dict,
        filter: dict | None,
    ):
        """
        Send data to all subscribing clients
        """
        payload = dict(
            data=data,
            filter=filter,
        )

        return self._publish(payload)

    def initialize(self):
        thread = Thread(target=self._thread)
        thread.start()

    def _publish(self, payload: dict):
        """
        publish message to all client
        """
        raise NotImplementedError()

    def _listen(self):
        """
        Listen for messages on channels this client has been subscribed to
        """
        raise NotImplementedError()

    def _unsubscribe(self) -> None:
        """
        Unsubscribe from channels
        """
        raise NotImplementedError()

    def _thread(self):
        for message in self._listen():
            self._on_data(message)

        self._unsubscribe()
