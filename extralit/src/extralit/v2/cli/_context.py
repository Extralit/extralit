from __future__ import annotations

from extralit.v2._sync import Client
from extralit.v2.cli._output import fail


def get_client() -> Client:
    """Non-interactive by construction: args come from env or the credentials file;
    a missing configuration is a structured error, never a prompt."""
    try:
        return Client()
    except ValueError as error:
        fail(error)
        raise  # unreachable; keeps type-checkers happy
