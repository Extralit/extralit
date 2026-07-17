from __future__ import annotations

import asyncio
import functools
import inspect
import threading

from extralit.v2.client import AsyncClient
from extralit.v2.resources._base import ResourceBase

_RESOURCE_NAMES = ("schemas", "questions", "records", "suggestions", "projections", "responses")


class _Portal:
    """A background-thread event loop. Sync mirrors submit coroutines here, so they
    work even when the calling thread already runs a loop (Jupyter)."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="extralit-v2-portal", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()


class _SyncProxy:
    """Wraps a resource: coroutine methods become sync calls through the portal;
    everything else passes through unchanged. Mirrors are mechanical — never hand-written."""

    def __init__(self, target: ResourceBase, portal: _Portal):
        self._target = target
        self._portal = portal

    def __getattr__(self, name: str):
        attribute = getattr(self._target, name)
        if inspect.iscoroutinefunction(attribute):

            @functools.wraps(attribute)
            def call(*args, **kwargs):
                return self._portal.run(attribute(*args, **kwargs))

            return call
        return attribute


class Client:
    """Sync facade over AsyncClient — same constructor, same resource surface."""

    def __init__(self, *args, **kwargs):
        self._portal = _Portal()
        self._async = AsyncClient(*args, **kwargs)
        for name in _RESOURCE_NAMES:
            setattr(self, name, _SyncProxy(getattr(self._async, name), self._portal))

    def close(self) -> None:
        self._portal.run(self._async.aclose())
        self._portal.stop()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
