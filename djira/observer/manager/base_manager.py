from time import sleep
from django.db.models.signals import ModelSignal
from django.dispatch import Signal, receiver
from typing import Callable, List, Optional, Tuple


class UniqueError(Exception):
    pass


base_manager_signal = Signal(use_caching=True)


class BaseManager:
    channel_key = "DJIRA_SOCKET_MANAGER"

    def __init__(self):
        self._listeners: Tuple[
            Callable[[dict], None],
            Optional[Callable[[dict], bool]],
        ] = []

    def _on_data(self, payload: dict) -> Optional[List[Exception]]:
        """
        ondata listener that trigger all registered listeners
        """

        data = payload["data"]
        errors: List[Exception] = []
        filter_data = payload["filter"]

        for callback, filter in self._listeners:
            if filter and filter_data and not filter(filter_data):
                continue
            try:
                callback(data)
            except Exception as error:
                errors.append(error)

        return errors if len(errors) > 0 else None

    def listen(
        self,
        callback: Callable[[dict], None],
        filter: Optional[Callable[[dict], bool]] = None,
        unique_listeners=True,
    ):
        """
        subscribe to data updates, trigger callback with optional custom filter when new data is pushed
        """
        if unique_listeners and (callback, filter) in self._listeners:
            raise UniqueError("listener with  callback already exist")

        self._listeners.append((callback, filter))

    def _pull_data(self) -> List[dict]:
        return NotImplementedError("BaseManager does not support pulling")

    def pull(self) -> Optional[List[Exception]]:
        """
        pull data when data has not been acknowledged, this triggers all registered listeners.
        `Note: To make sure all listener receive data, call this only after all listeners have been registered.`
        """
        errors = []
        payloads = self._pull_data()

        for payload in payloads:
            errors += self._on_data(payload) or []

        return errors if len(errors) > 0 else None

    def send_data(self, data: dict, filter: dict | None = None):
        """
        Send data to all subscribing clients
        """
        payload = dict(data=data, filter=filter)

        return base_manager_signal.send(
            BaseManager,
            payload=payload,
            instance=self,
            created=True,
        )
