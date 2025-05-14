

class BaseError(Exception):
    """Base class for custom errors with a message and a globally unique error code."""
    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self):
        return f"[Error {self.code}]: {self.message}"


class DependencyNotFoundError(BaseError):
    """Error raised when a required dependency is not found."""
    def __init__(self, dependency_name: str):
        message = f"Dependency '{dependency_name}' not found in extractions."
        code = 1001
        super().__init__(message, code)


class ExtractionError(BaseError):
    """Error raised during the extraction process."""
    def __init__(self, detail: str):
        message = f"Extraction error: {detail}"
        code = 1002
        super().__init__(message, code)


class CompletionError(BaseError):
    """Error raised during the completion process."""
    def __init__(self, detail: str):
        message = f"Completion error: {detail}"
        code = 1003
        super().__init__(message, code)

