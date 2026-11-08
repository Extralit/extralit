import pytest
from pydantic import ValidationError

from extralit_server.contexts.retrieval.settings import RetrievalSettings


def test_defaults_mean_full_text_only(monkeypatch):
    for key in ("EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS", "EMBEDDING_SETTINGS"):
        monkeypatch.delenv(f"EXTRALIT_RETRIEVAL_{key}", raising=False)

    settings = RetrievalSettings()

    assert settings.embedding_model == ""
    assert settings.embedding_dimensions is None
    assert settings.embedding_settings == {}
    assert (settings.embedding_batch_size, settings.rrf_k, settings.candidate_k) == (64, 60, 50)


def test_environment_overrides_with_json_settings(monkeypatch):
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_MODEL", "bedrock:amazon.nova-2-multimodal-embeddings-v1:0")
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_DIMENSIONS", "1024")
    monkeypatch.setenv("EXTRALIT_RETRIEVAL_EMBEDDING_SETTINGS", '{"bedrock_max_concurrency": 2}')

    settings = RetrievalSettings()

    assert settings.embedding_model.startswith("bedrock:")
    assert settings.embedding_dimensions == 1024
    assert settings.embedding_settings == {"bedrock_max_concurrency": 2}


@pytest.mark.parametrize("field", ["embedding_dimensions", "embedding_batch_size", "rrf_k", "candidate_k"])
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_numbers_are_rejected(field, value):
    with pytest.raises(ValidationError):
        RetrievalSettings(**{field: value})


def test_there_is_no_chunk_size_or_provider():
    assert "chunk_size" not in RetrievalSettings.model_fields
    assert "embedding_provider" not in RetrievalSettings.model_fields
