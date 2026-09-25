from redis import Redis
from rq import Queue

from app.core.config import settings

__QUEUE_NAME = "api_monitor"

client = Redis.from_url(settings.redis_url)
queue = Queue(name=__QUEUE_NAME, connection=client)
