"""Swappable PDF→`DoclingDocument` parsers.

Each parser normalizes its backend into `LayoutBlock`s and hands them to the shared builder,
so the document that comes out is the same shape regardless of which one ran.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Optional, Protocol

from docling_core.types.doc import DoclingDocument

from extralit_server.contexts.ocr.parsers.pdf_inspector import parse as _parse_pdf_inspector

try:
    from extralit_server.contexts.ocr.parsers.pymupdf import parse as _parse_pymupdf
except ImportError as e:  # AGPL extra, deliberately optional
    _parse_pymupdf = None
    logging.getLogger(__name__).debug(f"pymupdf layout parser unavailable: {e}")


class LayoutParser(Protocol):
    """Parse PDF bytes into a `DoclingDocument`."""

    def __call__(
        self,
        pdf_bytes: bytes,
        *,
        name: str,
        pages: Optional[Sequence[int]] = None,
        filename: Optional[str] = None,
    ) -> DoclingDocument: ...


_PARSERS: dict[str, LayoutParser] = {"pdf_inspector": _parse_pdf_inspector}
if _parse_pymupdf is not None:
    _PARSERS["pymupdf"] = _parse_pymupdf


def list_parsers() -> list[str]:
    """Names of every parser installed in this environment."""
    return sorted(_PARSERS)


def get_parser(name: str) -> LayoutParser:
    """Look up a parser by name."""
    try:
        return _PARSERS[name]
    except KeyError:
        raise ValueError(f"unknown layout parser {name!r}; available: {list_parsers()}") from None


def default_parser_name() -> str:
    """Prefer pymupdf's higher-fidelity geometry when the extra is installed."""
    return "pymupdf" if "pymupdf" in _PARSERS else "pdf_inspector"


__all__ = ["LayoutParser", "default_parser_name", "get_parser", "list_parsers"]
