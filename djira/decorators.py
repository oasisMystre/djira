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

    def _wrapper(func: Callable | Coroutine):
        if not iscoroutinefunction(func):
            func = sync_to_async(func)

        setattr(func, "action", True)

        if name:
            func.__name__ = name

        # kwargs
        setattr(
            func,
            "kwargs",
            {
                "methods": methods,
            },
        )

        return func

    return _wrapper
