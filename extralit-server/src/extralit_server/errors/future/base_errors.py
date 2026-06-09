__all__ = [
    "AuthenticationError",
    "MissingVectorError",
    "NotFoundError",
    "NotUniqueError",
    "UnprocessableEntityError",
    "UpdateDistributionWithExistingResponsesError",
]

NOT_FOUND_ERROR = "not_found"
NOT_UNIQUE_ERROR = "not_unique"
UNPROCESSABLE_ENTITY_ERROR_CODE = "unprocessable_entity"
MISSING_VECTOR_ERROR_CODE = "missing_vector"
UPDATE_DISTRIBUTION_WITH_EXISTING_RESPONSES_ERROR_CODE = "update_distribution_with_existing_responses"


class NotFoundError(Exception):
    """Custom Extralit not found error. Use it for situations where an Extralit domain entity has not be found on the system."""

    def __init__(self, message, code=NOT_FOUND_ERROR):
        self.message = message
        self.code = code


class NotUniqueError(Exception):
    """Custom Extralit not unique error. Use it for situations where an Extralit domain entity already exists violating a constraint."""

    def __init__(self, message, code=NOT_UNIQUE_ERROR):
        self.message = message
        self.code = code


class UnprocessableEntityError(Exception):
    """Custom Extralit unprocessable entity error. Use it for situations where an Extralit domain entity can not be processed."""

    def __init__(self, message, code=UNPROCESSABLE_ENTITY_ERROR_CODE):
        self.message = message
        self.code = code


# TODO: Once we move to v2.0 we can remove this error and use UnprocessableEntityError
class MissingVectorError(UnprocessableEntityError):
    pass


class UpdateDistributionWithExistingResponsesError(UnprocessableEntityError):
    def __init__(self, message: str):
        super().__init__(message, code=UPDATE_DISTRIBUTION_WITH_EXISTING_RESPONSES_ERROR_CODE)


class AuthenticationError(Exception):
    """Custom Extralit unauthorized error. Use it for situations where an request is not authorized to perform an action."""
