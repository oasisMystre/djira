from typing import Callable, Coroutine, List, Literal

from asgiref.sync import iscoroutinefunction, sync_to_async


def action(
    name: str = None,
    actions: List[Literal["get", "post", "put", "patch", "subscription"]] = ["get"],
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
            "kwargs",
            {
                "methods": actions,
            },
        )

        return func

    return _wrapper
