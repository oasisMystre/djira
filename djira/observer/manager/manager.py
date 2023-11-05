from django.dispatch import Signal

from .pubsub_manager import PubSubManager


signal = Signal(use_caching=True)


class Manager(PubSubManager):
    def initialize(self):
        signal.connect(self._listen)

    def _listen(self, payload: dict, **kwargs):
        self._on_data(payload)

    def send_data(self, data: dict, filter: dict | None = None):
        """
        Send data to all subscribing clients
        """
        payload = dict(data=data, filter=filter)

        return signal.send(
            Manager,
            payload=payload,
            instance=self,
            created=True,
        )
