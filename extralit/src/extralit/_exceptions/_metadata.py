from extralit._exceptions._base import ExtralitError


class MetadataError(ExtralitError):
    message: str = "Error defining dataset metadata settings"
