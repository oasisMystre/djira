from .scope import Scope


def build_context_from_scope(scope: Scope):
    return dict(scope=scope, request=scope)
