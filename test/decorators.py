def action(methods):
    def _decorator(func):
        setattr(func, "methods", methods)

        return func
    
    return _decorator


def subscribe():
    def _decorator(func):
        print(func.__name__)

        return func
    
    return _decorator

@action(["SUBSCRIBE"])
@subscribe()
def name():
    return 2 + 2 

print(name())

