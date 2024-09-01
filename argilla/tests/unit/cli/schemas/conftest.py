# conftest.py

import pytest
import pandera as pa
from pandera.typing import Index, Series
from extralit.schema.checks import register_check_methods
from extralit.extraction.models.schema import SchemaStructure

register_check_methods()

class Publication(pa.DataFrameModel):
    """
    General information about the publication, extracted once per paper.
    """
    reference: Index[str] = pa.Field(check_name=True)
    title: Series[str] = pa.Field()
    authors: Series[str] = pa.Field()
    journal: Series[str] = pa.Field()
    publication_year: Series[int] = pa.Field(ge=1900, le=2100)
    doi: Series[str] = pa.Field(nullable=True)
    
    class Config:
        singleton = True


@pytest.fixture
def singleton_schema() -> pa.DataFrameModel:
    return Publication


@pytest.fixture
def schema_structure(singleton_schema: pa.DataFrameModel) -> SchemaStructure:
    return SchemaStructure(schemas=[singleton_schema])