import pandas as pd
from unittest.mock import MagicMock, patch
from extralit.preprocessing.document import create_or_load_deepdoctection_segments, create_or_load_nougat_segments
from extralit.preprocessing.segment import Segments
from extralit.storage.files import FileHandler


def test_create_or_load_deepdoctection_segments_load_only(mock_paper: 'pd.Series', local_file_handler: 'MagicMock', mock_deepdoctection: 'MagicMock'):
    local_file_handler.exists.return_value = True
    local_file_handler.read_text.return_value = Segments().json()

    texts, tables, figures = create_or_load_deepdoctection_segments(
        paper=mock_paper,
        load_only=True,
        file_handler=local_file_handler,
    )

    assert texts is not None
    assert tables is not None
    assert figures is not None
    local_file_handler.read_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json')

def test_create_or_load_deepdoctection_segments_redo(mock_paper: 'pd.Series', local_file_handler: 'MagicMock', mock_deepdoctection: 'MagicMock'):
    local_file_handler.exists.return_value = False
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value = MagicMock()
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value.reset_state.return_value = None

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            load_only=False,
            redo=True,
            file_handler=local_file_handler,
        )

    assert texts is None
    assert tables is not None
    assert figures is None
    mock_makedirs.assert_called_with('data/preprocessing/deepdoctection/test-paper/tables', exist_ok=True)
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.assert_called_with(path='/tmp/test_pdf.pdf')

def test_create_or_load_deepdoctection_segments_save(mock_paper: 'pd.Series', local_file_handler: 'MagicMock', mock_deepdoctection: 'MagicMock'):
    local_file_handler.exists.return_value = False
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value = MagicMock()
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.return_value.reset_state.return_value = None

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            load_only=False,
            redo=False,
            save=True,
            file_handler=local_file_handler,
        )

    assert texts is None
    assert tables is not None
    assert figures is None
    mock_makedirs.assert_called_with('data/preprocessing/deepdoctection/test-paper/tables', exist_ok=True)
    mock_deepdoctection.get_dd_analyzer.return_value.analyze.assert_called_with(path='/tmp/test_pdf.pdf')
    local_file_handler.write_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json', tables.json())

def test_create_or_load_deepdoctection_segments_load_from_s3(mock_paper: 'pd.Series', s3_file_handler: 'FileHandler', mock_deepdoctection: 'MagicMock'):
    # Mock the minio client methods
    s3_file_handler.client.stat_object.side_effect = lambda bucket, path: None if path.endswith('page_1.json') else Exception()
    s3_file_handler.client.get_object.side_effect = lambda bucket, path: MagicMock(read=lambda: Segments().json().encode('utf-8'))

    # Mock the file handler methods
    s3_file_handler.read_text = MagicMock(side_effect=[
        Segments().json(), Segments().json(), Segments().json()
    ])

    with patch("glob.glob", return_value=['data/preprocessing/deepdoctection/test-paper/page_1.json']):
        texts, tables, figures = create_or_load_deepdoctection_segments(
            paper=mock_paper,
            load_only=True,
            file_handler=s3_file_handler,
        )

    assert texts is not None
    assert tables is not None
    assert figures is not None
    s3_file_handler.read_text.assert_any_call('data/preprocessing/deepdoctection/test-paper/tables.json')


def test_create_or_load_nougat_segments_load_only(mock_paper: 'pd.Series', local_file_handler: 'MagicMock'):
    local_file_handler.exists.return_value = True
    local_file_handler.read_text.return_value = Segments().json()

    texts, tables, figures = create_or_load_nougat_segments(
        paper=mock_paper,
        load_only=True,
        file_handler=local_file_handler,
    )

    assert texts is not None
    assert tables is not None
    assert figures is not None
    local_file_handler.read_text.assert_any_call('data/preprocessing/nougat/test-paper/tables.json')


def test_create_or_load_nougat_segments_redo(mock_paper: 'pd.Series', local_file_handler: 'MagicMock', mock_nougat: MagicMock):
    local_file_handler.exists.return_value = False
    mock_nougat.NougatOCR.return_value.predict.return_value = MagicMock()

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}), patch("extralit.preprocessing.document.isinstance", return_value=True):
        texts, tables, figures = create_or_load_nougat_segments(
            paper=mock_paper,
            load_only=False,
            redo=True,
            file_handler=local_file_handler,
            nougat_model=mock_nougat.NougatOCR()
        )

    assert texts is not None
    assert tables is not None
    assert figures is None
    # mock_makedirs.assert_called_with('data/preprocessing/nougat/test-paper', exist_ok=True)
    mock_nougat.NougatOCR.return_value.predict.assert_called_with('/tmp/test_pdf.pdf')


def test_create_or_load_nougat_segments_save(mock_paper: 'pd.Series', local_file_handler: 'MagicMock', mock_nougat: 'MagicMock'):
    local_file_handler.exists.return_value = False
    mock_nougat.NougatOCR.return_value.predict.return_value = MagicMock()

    with patch("os.makedirs") as mock_makedirs, patch("os.environ", {}), patch("extralit.preprocessing.document.isinstance", return_value=True):
        texts, tables, figures = create_or_load_nougat_segments(
            paper=mock_paper,
            load_only=False,
            redo=False,
            save=True,
            file_handler=local_file_handler,
            nougat_model=mock_nougat.NougatOCR()
        )

    assert texts is not None
    assert tables is not None
    assert figures is None
    # mock_makedirs.assert_called_with('data/preprocessing/nougat/test-paper', exist_ok=True)
    mock_nougat.NougatOCR.return_value.predict.assert_called_with('/tmp/test_pdf.pdf')
    local_file_handler.write_text.assert_any_call('data/preprocessing/nougat/test-paper/tables.json', tables.json())


def test_create_or_load_nougat_segments_load_from_s3(mock_paper: 'pd.Series', s3_file_handler: 'FileHandler', mock_nougat: 'MagicMock'):
    # Mock the minio client methods
    s3_file_handler.client.stat_object.side_effect = lambda bucket, path: None if path.endswith('predictions.json') else Exception()
    s3_file_handler.client.get_object.side_effect = lambda bucket, path: MagicMock(read=lambda: Segments().json().encode('utf-8'))

    # Mock the file handler methods
    s3_file_handler.read_text = MagicMock(side_effect=[
        Segments().json(), Segments().json(), Segments().json()
    ])

    with patch("glob.glob", return_value=['data/preprocessing/nougat/test-paper/predictions.json']), patch("extralit.preprocessing.document.isinstance", return_value=True):
        texts, tables, figures = create_or_load_nougat_segments(
            paper=mock_paper,
            load_only=True,
            file_handler=s3_file_handler,
        )

    assert texts is not None
    assert tables is not None
    assert figures is not None
    s3_file_handler.read_text.assert_any_call('data/preprocessing/nougat/test-paper/tables.json')
