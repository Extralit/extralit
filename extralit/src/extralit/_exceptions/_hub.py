from extralit._exceptions import ExtralitError

__all__ = [
    "DatasetsServerException",
    "ImportDatasetError",
]


class ImportDatasetError(ExtralitError):
    def __init__(self, message: str = "Error importing dataset") -> None:
        super().__init__(message)


class DatasetsServerException(ExtralitError):
    def __init__(self, message: str = "Error connecting to Hugging Face Hub datasets-server API") -> None:
        super().__init__(message)
