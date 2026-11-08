import redis
from redis.cluster import RedisCluster
from rq import Queue

from extralit_server.settings import settings

if settings.redis_use_cluster:
    REDIS_CONNECTION = RedisCluster.from_url(settings.redis_url)
else:
    REDIS_CONNECTION = redis.from_url(settings.redis_url)

DEFAULT_QUEUE = Queue("default", connection=REDIS_CONNECTION)
HIGH_QUEUE = Queue("high", connection=REDIS_CONNECTION)
OCR_QUEUE = Queue("ocr", connection=REDIS_CONNECTION)
# Not in the worker CLI default queues: a separate process serves it so provider limits hold.
EMBED_QUEUE = Queue("embed", connection=REDIS_CONNECTION)

JOB_TIMEOUT_DISABLED = -1
