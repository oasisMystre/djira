from djira.observer.manager.redis_manager import RedisManager


manager = RedisManager.connect_from_url("redis://127.0.0.1:6379")
manager._connect()
manager.send_data({"scope": "FUCKing MEan I mean you ahhhh!!!"}, {})
