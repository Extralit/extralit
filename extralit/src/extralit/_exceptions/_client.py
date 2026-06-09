from extralit._exceptions._base import ExtralitError


class ExtralitCredentialsError(ExtralitError):
    def __init__(self, message: str = "Credentials (api_key and/or api_url) are invalid") -> None:
        super().__init__(message)
