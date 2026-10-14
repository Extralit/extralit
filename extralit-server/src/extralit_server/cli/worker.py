import platform

import typer

from extralit_server.jobs.queues import DEFAULT_QUEUE, HIGH_QUEUE, OCR_QUEUE

DEFAULT_NUM_WORKERS = 2


def worker(
    queues: list[str] = typer.Option(
        [HIGH_QUEUE.name, DEFAULT_QUEUE.name, OCR_QUEUE.name], help="Queues to listen on, highest priority first"
    ),
    num_workers: int = typer.Option(DEFAULT_NUM_WORKERS, help="Number of workers to start"),
) -> None:
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
        connection=REDIS_CONNECTION, queues=queues, num_workers=num_workers, worker_class=worker_class, reload=True
    )
    worker_pool.start()
