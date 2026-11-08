"""Jobs run by real workers in `test_embed_queue_concurrency`."""

import time

from extralit_server.jobs.queues import REDIS_CONNECTION


def hold(prefix: str, seconds: float) -> None:
    running = REDIS_CONNECTION.incr(f"{prefix}:running")
    REDIS_CONNECTION.set(f"{prefix}:max", max(running, int(REDIS_CONNECTION.get(f"{prefix}:max") or 0)))
    time.sleep(seconds)
    REDIS_CONNECTION.decr(f"{prefix}:running")
    REDIS_CONNECTION.incr(f"{prefix}:done")
