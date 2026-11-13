"""Jobs run by real workers in `test_embed_queue_concurrency`."""

import time

from extralit_server.jobs.queues import REDIS_CONNECTION

_ENTER = """
local running = redis.call('INCR', KEYS[1])
if running > tonumber(redis.call('GET', KEYS[2]) or '0') then redis.call('SET', KEYS[2], running) end
return running
"""


def hold(prefix: str, seconds: float) -> None:
    REDIS_CONNECTION.eval(_ENTER, 2, f"{prefix}:running", f"{prefix}:max")
    time.sleep(seconds)
    REDIS_CONNECTION.decr(f"{prefix}:running")
    REDIS_CONNECTION.incr(f"{prefix}:done")
