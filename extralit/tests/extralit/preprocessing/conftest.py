
import sys
from typing import TYPE_CHECKING
import pytest
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

@pytest.fixture
def mock_deepdoctection():
    mock_dd = MagicMock()
    mock_dd.get_dd_analyzer = MagicMock()
    sys.modules['deepdoctection'] = mock_dd
    with patch.dict('sys.modules', {'deepdoctection': mock_dd}):
        yield mock_dd


@pytest.fixture(autouse=True)
def mock_nougat(mocker: "MockerFixture"):
    sys.modules["pypdfium2"] = MagicMock()
    sys.modules["torch"] = MagicMock(spec=sys.modules.get("torch", None))
    
    mock_nougat = MagicMock()
    mock_nougat_dataset = MagicMock()
    mock_nougat_rasterize = MagicMock()
    mock_nougat_postprocessing = MagicMock()
    mock_nougat_utils = MagicMock()
    mock_nougat_utils_dataset = MagicMock()
    mock_nougat_utils_device = MagicMock()
    mock_nougat_utils_checkpoint = MagicMock()

    sys.modules['nougat'] = mock_nougat
    sys.modules['nougat.dataset'] = mock_nougat_dataset
    sys.modules['nougat.dataset.rasterize'] = mock_nougat_rasterize
    sys.modules['nougat.postprocessing'] = mock_nougat_postprocessing
    sys.modules['nougat.utils'] = mock_nougat_utils
    sys.modules['nougat.utils.dataset'] = mock_nougat_utils_dataset
    sys.modules['nougat.utils.device'] = mock_nougat_utils_device
    sys.modules['nougat.utils.checkpoint'] = mock_nougat_utils_checkpoint

    mocker.patch("extralit.preprocessing.text.NougatOCR", return_value=MagicMock())
    mocker.patch("nougat.dataset.rasterize.rasterize_paper", return_value=MagicMock())
    
    with patch.dict('sys.modules', {'nougat': mock_nougat}):
        yield mock_nougat
