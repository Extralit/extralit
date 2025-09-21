# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import platform

import typer

from extralit_server.jobs.queues import DEFAULT_QUEUE, HIGH_QUEUE, OCR_QUEUE

DEFAULT_NUM_WORKERS = 2


def worker(
    queues: str = typer.Option("", help="Comma-separated list of queue names to listen to"),
    num_workers: int = typer.Option(DEFAULT_NUM_WORKERS, help="Number of workers to start"),
) -> None:
    # Handle default value and parse queues
    if not queues:
        queue_list = [DEFAULT_QUEUE.name, HIGH_QUEUE.name, OCR_QUEUE.name]
    else:
        queue_list = [q.strip() for q in queues.split(",")]

    # Preload heavy modules before forking worker processes
    from rq import Worker
    from rq.worker_pool import WorkerPool

    from extralit_server.jobs import preload  # noqa: F401
    from extralit_server.jobs.queues import REDIS_CONNECTION

    worker_class = Worker

    if platform.system() == "Windows":
        # Use SimpleWorker on Windows due to multiprocessing limitations
        from rq import SimpleWorker

        worker_class = SimpleWorker

    worker_pool = WorkerPool(
        connection=REDIS_CONNECTION, queues=queue_list, num_workers=num_workers, worker_class=worker_class
    )
    worker_pool.start()
