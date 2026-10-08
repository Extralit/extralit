"""
This module centralizes all configuration and logging management
"""

# TODO: Remove this and provide a file to configure logging

import logging
from logging import Logger, StreamHandler

try:
    from rich.logging import RichHandler as ExtralitHandler
except ModuleNotFoundError:
    ExtralitHandler = StreamHandler


def full_qualified_class_name(_class: type) -> str:
    """Calculates the full qualified name (module + class) of a class"""
    class_module = _class.__module__
    if class_module is None or class_module == str.__class__.__module__:
        return _class.__name__  # Avoid reporting __builtin__
    else:
        return f"{class_module}.{_class.__name__}"


def get_logger_for_class(_class: type) -> Logger:
    """Return the logger for a given class"""
    return logging.getLogger(full_qualified_class_name(_class))


class LoggingMixin:
    """
    Main logging class methods. Classes that inherit from this, have
    available a `logger` properly configured property

    """

    __logger__: Logger = None

    def __new__(cls, *args, **kwargs):
        cls.__logger__ = get_logger_for_class(cls)
        return super().__new__(cls)

    @property
    def logger(self) -> logging.Logger:
        """Return the logger configured for the class"""
        return self.__logger__


def configure_logging():
    """Normalizes logging configuration for extralit and its dependencies"""
    handler = ExtralitHandler(show_time=False, show_level=False)

    if hasattr(handler, "set_formatter"):
        # For RichHandler, use its own formatter
        handler.set_formatter(None)
    else:
        # For StreamHandler, use a minimal formatter
        handler.setFormatter(logging.Formatter("%(message)s"))

    # See the note here: https://docs.python.org/3/library/logging.html#logging.Logger.propagate
    # We only attach our handler to the root logger and let propagation take care of the rest
    logging.basicConfig(handlers=[handler], level=logging.WARNING)

    # Suppress pdfminer warnings about invalid color values
    logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
