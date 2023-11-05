from djira.observer.manager.redis_manager import RedisManager

manager = RedisManager.connect_from_url("redis://127.0.0.1:6379")
manager.subscribe(print)
