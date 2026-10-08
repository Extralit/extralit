import os

import psutil

from extralit_server._version import __version__


def extralit_version() -> str:
    return __version__


def memory_status() -> dict:
    process = psutil.Process(os.getpid())

    return {k: _memory_size(v) for k, v in process.memory_info()._asdict().items()}


def _memory_size(bytes) -> str:
    system = [
        (1024**5, "P"),
        (1024**4, "T"),
        (1024**3, "G"),
        (1024**2, "M"),
        (1024**1, "K"),
        (1024**0, "B"),
    ]

    factor, suffix = None, None
    for factor, suffix in system:  # noqa: B007
        if bytes >= factor:
            break

    amount = int(bytes / factor)
    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple

    return str(amount) + suffix
