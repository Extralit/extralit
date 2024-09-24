import os
import glob
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from extralit.preprocessing.document import create_or_load_deepdoctection_segments
from extralit.storage.files import FileHandler, StorageType
from extralit.preprocessing.segment import Segments

@pytest.fixture
def mock_paper():
    return pd.Series({"name": "test-paper", "file_path": "test-path/test-paper.pdf"})

@pytest.fixture
def mock_file_handler():
    return MagicMock(spec=FileHandler)

@pytest.fixture
def mock_deepdoctection():
    with patch("extralit.preprocessing.document.dd") as mock_dd:
        yield mock_dd

def test_create_or_load_deepdoctection_segments_load_only(mock_paper, mock_file_handler):
    mock_file_handler.exists.return_value = True
    mock_file_handler.read_text.side_effect = [
        Segments().json(), Segments().json(), Segments().json()
    ]

    texts, tables, figures = create_or_load_deepdoctection_segments(
        paper=mock_paper,
        preprocessing_path='data/preprocessing/',
        load_only=True,
        storage_type=StorageType.LOCAL,
        bucket_name=None
    )

    assert texts is not None
    assert tables is not None
    assert figures is None
    mock_file_handler.exists.assert_called_with('data/preprocessing/deepdoctection/test-paper')
    mock_file_handler.read_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json')

def test_create_or_load_deepdoctection_segments_redo(mock_paper, mock_file_handler, mock_deepdoctection):
    mock_file_handler.exists.return_value = False
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value = MagicMock()
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value.reset_state.return_value = None

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            preprocessing_path='data/preprocessing/',
            load_only=False,
            redo=True,
            storage_type=StorageType.LOCAL,
            bucket_name=None
        )

    assert texts is None
    assert tables is not None
    assert figures is None
    mock_makedirs.assert_called_with('data/preprocessing/deepdoctection/test-paper', exist_ok=True)
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.assert_called_with(path='test-path/test-paper.pdf')

def test_create_or_load_deepdoctection_segments_save(mock_paper, mock_file_handler, mock_deepdoctection):
    mock_file_handler.exists.return_value = False
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value = MagicMock()
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value.reset_state.return_value = None

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            preprocessing_path='data/preprocessing/',
            load_only=False,
            redo=False,
            save=True,
            storage_type=StorageType.LOCAL,
            bucket_name=None
        )

    assert texts is None
    assert tables is not None
    assert figures is None
    mock_makedirs.assert_called_with('data/preprocessing/deepdoctection/test-paper', exist_ok=True)
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.assert_called_with(path='test-path/test-paper.pdf')
    mock_file_handler.write_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json', tables.json())

def test_create_or_load_deepdoctection_segments_load_from_cache(mock_paper, mock_file_handler, mock_deepdoctection):
    mock_file_handler.exists.side_effect = lambda path: path.endswith('page_1.json')
    mock_file_handler.read_text.side_effect = [
        Segments().json(), Segments().json(), Segments().json()
    ]

    with patch("glob.glob", return_value=['data/preprocessing/deepdoctection/test-paper/page_1.json']):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            preprocessing_path='data/preprocessing/',
            load_only=True,
            storage_type=StorageType.LOCAL,
            bucket_name=None
        )

    assert texts is None
    assert tables is not None
    assert figures is None
    mock_file_handler.exists.assert_any_call('data/preprocessing/deepdoctection/test-paper/page_1.json')
    mock_file_handler.read_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json')