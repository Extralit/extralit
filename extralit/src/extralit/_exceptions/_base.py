from typing import Optional


class ExtralitError(Exception):
    message_stub = "Extralit SDK error"

    def __init__(self, message: Optional[str] = None):
        """Base class for all Extralit exceptions
        Args:
            message (str): The message to display when the exception is raised
        """
        super().__init__(message or self.message_stub)

    def __str__(self):
        return f"{self.message_stub}: {self.__class__.__name__}: {super().__str__()}"

    def __repr__(self):
        return f"{self.message_stub}: {self.__class__.__name__}: {super().__repr__()}"
