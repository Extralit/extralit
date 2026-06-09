from extralit_server.models import VectorSettings


class VectorValidator:
    @classmethod
    def validate(cls, value: list[float], vector_settings: VectorSettings):
        if len(value) != vector_settings.dimensions:
            raise ValueError(
                f"vector value for vector name={vector_settings.name} must have {vector_settings.dimensions} elements, "
                f"got {len(value)} elements"
            )
