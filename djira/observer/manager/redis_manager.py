from typing import Callable 

from time import sleep
from functools import partial

from redis import Redis, ConnectionError
from redis.execeptions import RedisError 

from .base_manager import BaseManager

class RedisManager(BaseManager):
    """
    def on_scope_subscribe_to_room(self, payload):
      scope = Scope.from_json(payload)
      ....
      
    manager = RedisManager.connect_from_url(url)
    manager.listen(on_scope_subscribe_to_room)
    # add optional filter to reduce listen to data from pub 
    """
    def __init__(self, connect: Callable):
        self._connect = partial(connect, self) 
        
    @classmethod
    def connect_from_url(cls, url: str):
        def connect(self: "RedisManager"):
             self.redis = redis
             self.pubsub = redis.pubsub(ignore_subscribe_messages=True)
              
        return cls(connect)
        
    def _publish(self, data: dict):
        retry = False
    
        while True:
            try:
                if retry:
                    self._connect()
                return self.redis.publish(self.channel_key, json.dumps(data))
            except RedisError as error:
                if not retry:
                     retry = True
                     continue 
          
                 raise RedisError() from error
    
    def send_data(
        self,
        data: dict,
        filter: dict | None,
    ):
        payload = dict(
            data=data,
            filter=filter,
        )

        return self._publish(payload)

    def _subscribe(self): 
         retry_sleep = 1 
         connect = False 
         
         while True: 
             try: 
                 if connect: 
                     self._connect()
                     retry_sleep = 1 
                 for message in self.pubsub.listen(): 
                     yield self._on_data(message)
             except RedisError: 
                 connect = True 
                 sleep(retry_sleep) 
                 retry_sleep *= 2 
               
                 if retry_sleep > 60: 
                     retry_sleep = 60
         
         self.pubsub.unsubscribe(self.channel_key)
