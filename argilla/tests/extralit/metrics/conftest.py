import os

import pandas as pd
import pytest

from extralit.extraction.models.paper import PaperExtraction
from extralit.extraction.models.schema import SchemaStructure
from extralit.schema.checks import register_check_methods

register_check_methods()

@pytest.fixture
def mock_schema_structure() -> SchemaStructure:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    relative_path = os.path.join(current_dir, '..', 'assets', 'schemas')
    directory_path = os.path.normpath(relative_path)

    return SchemaStructure.from_dir(directory_path)


@pytest.fixture
def mock_observation_df(mock_schema_structure, schema_name="Observation") -> pd.DataFrame:
    df = pd.DataFrame({
        'Study_type': ['Hut trial', 'Lab based bioassay'],
        'Country': ['Country1', 'Country2'],
        'Site': ['Site1', 'Site2'],
        'Start_month': [1, 2],
        'Start_year': [2000, 2001],
        'End_month': [3, 1],
        'End_year': [2001, 2002],
        'Time_elapsed': [14.0, 11.0]
    }, index=pd.Index(['ref1', 'ref2'], name='reference'))
    schema = mock_schema_structure[schema_name]
    # validated_df = schema.validate(df)
    return df


@pytest.fixture
def mock_paper_extraction_true(mock_schema_structure, mock_observation_df) -> PaperExtraction:
    mock_data = {
        "Observation": mock_observation_df,
        "ITNCondition": pd.DataFrame(),
        # "EntomologicalOutcome": pd.DataFrame(),
        # "ClinicalOutcome": pd.DataFrame()
    }
    return PaperExtraction(extractions=mock_data, schemas=mock_schema_structure)


@pytest.fixture
def mock_paper_extraction_pred(mock_schema_structure) -> PaperExtraction:
    df = pd.DataFrame({
        'Study_type': ['Hut trial', 'Lab based bioassay'],
        'Country': ['Country1', 'Country2'],
        'Site': ['Site1', 'Site2'],
        'Start_month': [1, 2],
        'Start_year': [2000, 2001],
        'End_month': [3, 1],
        'End_year': [2001, 2002],
        # 'Time_elapsed': [16.0, 13.0]
    }, index=pd.Index(['ref3', 'ref4'], name='reference'))

    mock_data = {
        "Observation": df,
        "ITNCondition": pd.DataFrame(),
    }
    return PaperExtraction(extractions=mock_data, schemas=mock_schema_structure)
