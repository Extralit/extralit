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

import sys
from collections.abc import Coroutine
from functools import wraps
from typing import Any, Callable, TypeVar

import typer

# Monkey-patch click to make ctx optional in Parameter.make_metavar for compatibility
try:
    import click

    # Save original method
    _orig_make_metavar = click.core.Parameter.make_metavar

    # Define wrapper to make ctx optional
    def make_metavar(self, ctx=None):
        return _orig_make_metavar(self, ctx)

    click.core.Parameter.make_metavar = make_metavar
except ImportError:
    pass

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

HandleErrorFunc = Callable[[Exception], None]


class ExtralitTyper(typer.Typer):
    error_handlers: dict[type[Exception], HandleErrorFunc] = {}

    def command(
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
        import asyncio

        super_command = super().command(*args, **kwargs)

        def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
            @wraps(func)
            def sync_func(*_args: P.args, **_kwargs: P.kwargs) -> R:
                return asyncio.run(func(*_args, **_kwargs))

            if asyncio.iscoroutinefunction(func):
                super_command(sync_func)
            else:
                super_command(func)

            return func

        return decorator

    def error_handler(self, exc: type[Exception]) -> Callable[[HandleErrorFunc], None]:
        def decorator(func: HandleErrorFunc) -> None:
            self.error_handlers[exc] = func

        return decorator

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return super().__call__(*args, **kwargs)
        except typer.Exit as e:
            raise e
        except Exception as e:
            handler = self.error_handlers.get(type(e))
            if handler is None:
                raise e
            handler(e)


def run(function: Callable[..., Coroutine[Any, Any, Any]]) -> None:
    app = ExtralitTyper(add_completion=False)
    app.command()(function)
    app()
