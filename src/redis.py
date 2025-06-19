import redis
import json

class RedisService:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    
    async def store_github_code(self, code: str, data: dict, expire: int = 300):
        self.redis.hset(f"github:code:{code}", mapping=data)
        self.redis.expire(f"github:code:{code}", expire)
    
    async def get_github_code_data(self, code: str) -> dict | None:
        data = self.redis.hgetall(f"github:code:{code}")
        return data if data else None
    
    async def delete_github_code(self, code: str):
        self.redis.delete(f"github:code:{code}")
        
    async def set_key(self, key: str, value, expire: int = None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis.set(key, value, ex=expire)

    async def get_key(self, key: str):
        value = self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def delete_key(self, key: str):
        self.redis.delete(key)
        
    async def publish(self, channel: str, message: str):
        self.redis.publish(channel, message)
        
    async def subscribe(self, channel: str):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)
        return pubsub

redis_service = RedisService()