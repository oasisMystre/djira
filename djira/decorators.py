from typing import Callable, Coroutine, List

from asgiref.sync import iscoroutinefunction, sync_to_async

from djira.typing import Method


def action(
    name: str = None,
    methods: List[Method] = ["GET"],
):
    """
    args:
        namespace (str): override function name to map request
        methods (list): allowed method list
    """

    def wrapper(func: Callable | Coroutine):
        func.action = True
        func.methods = methods
        func.__name__ = name if name else func.__name__

        if not iscoroutinefunction(func):
            func = sync_to_async(func)

        return func

    return wrapper
