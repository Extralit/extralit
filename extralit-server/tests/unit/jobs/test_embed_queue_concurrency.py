"""With 2 general workers and 1 embed worker, queued embed jobs run one at a time (real RQ workers)."""

import inspect
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from extralit_server.jobs.queues import DEFAULT_QUEUE, EMBED_QUEUE, REDIS_CONNECTION
from tests.unit.jobs.concurrency_jobs import hold

ROOT = Path(__file__).parents[3]


def worker(*args: str) -> subprocess.Popen:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.Popen(
        [sys.executable, "-m", "extralit_server", "worker", *args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def test_embed_queue_is_not_a_default_worker_queue():
    from extralit_server.cli.worker import worker as cli

    defaults = inspect.signature(cli).parameters["queues"].default.default
    assert EMBED_QUEUE.name not in defaults


def test_five_embed_jobs_never_run_concurrently():
    prefix = f"test-embed-concurrency:{uuid4().hex}"
    embed_prefix = f"{prefix}:embed"
    general_prefix = f"{prefix}:general"
    processes = [worker("--num-workers", "2"), worker("--queues", "embed", "--num-workers", "1")]
    try:
        for _ in range(5):
            EMBED_QUEUE.enqueue(hold, embed_prefix, 1.0)
        for _ in range(4):
            DEFAULT_QUEUE.enqueue(hold, general_prefix, 1.0)

        deadline = time.time() + 200
        while time.time() < deadline:
            if (
                int(REDIS_CONNECTION.get(f"{embed_prefix}:done") or 0) == 5
                and int(REDIS_CONNECTION.get(f"{general_prefix}:done") or 0) == 4
            ):
                break
            time.sleep(1)

        print(
            f"embed jobs done={REDIS_CONNECTION.get(f'{embed_prefix}:done')} max_concurrent={REDIS_CONNECTION.get(f'{embed_prefix}:max')}; general max_concurrent={REDIS_CONNECTION.get(f'{general_prefix}:max')}"
        )
        assert int(REDIS_CONNECTION.get(f"{embed_prefix}:done") or 0) == 5
        assert int(REDIS_CONNECTION.get(f"{embed_prefix}:max")) == 1
        assert int(REDIS_CONNECTION.get(f"{general_prefix}:max")) >= 1
    finally:
        for process in processes:
            try:
                os.killpg(process.pid, 15)
            except ProcessLookupError:
                pass
            process.wait(timeout=30)
        for name in ("running", "max", "done"):
            REDIS_CONNECTION.delete(f"{embed_prefix}:{name}", f"{general_prefix}:{name}")
