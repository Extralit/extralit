"""Named `PageParser`s available in this environment, and the default `ParserService` over them."""

from __future__ import annotations

import logging

from extralit_server.contexts.ocr.parsers.liteparse import LiteParseParser
from extralit_server.contexts.ocr.parsers.pdf_inspector import PdfInspectorParser
from extralit_server.contexts.ocr.parsers.service import DIGITAL_PARSER, OCR_PARSER, PageParser, ParserService

try:
    from extralit_server.contexts.ocr.parsers.pymupdf import PyMuPDFParser
except ImportError as e:  # AGPL extra, deliberately optional
    PyMuPDFParser = None
    logging.getLogger(__name__).debug(f"pymupdf layout parser unavailable: {e}")

_PARSERS: dict[str, PageParser] = {"pdf_inspector": PdfInspectorParser(), OCR_PARSER: LiteParseParser()}
if PyMuPDFParser is not None:
    _PARSERS[DIGITAL_PARSER] = PyMuPDFParser()


def list_parsers() -> list[str]:
    """Names of every parser installed in this environment."""
    return sorted(_PARSERS)


def get_parser(name: str) -> PageParser:
    """Look up a parser by name."""
    try:
        return _PARSERS[name]
    except KeyError:
        raise ValueError(f"unknown layout parser {name!r}; available: {list_parsers()}") from None


def default_service() -> ParserService:
    """Routing service over every installed parser; pdf_inspector is only used when named explicitly."""
    return ParserService(_PARSERS)


__all__ = ["default_service", "get_parser", "list_parsers"]
