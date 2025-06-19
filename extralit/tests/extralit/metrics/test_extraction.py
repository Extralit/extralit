from typing import TYPE_CHECKING
from extralit.metrics.extraction import grits_paper

if TYPE_CHECKING:
    from extralit.extraction.models.paper import PaperExtraction

def test_grits_paper_with_pred_missing_column(mock_paper_extraction_true: 'PaperExtraction', mock_paper_extraction_pred: 'PaperExtraction'):
    result = grits_paper(mock_paper_extraction_true, mock_paper_extraction_pred)
    assert result["Observation"].loc[("grits", "con", "precision")] == 1.0
    assert result["Observation"].loc[("grits", "con", "recall")] < 1.0
    assert result["Observation"].loc[("grits", "con", "f1")] < 1.0
    assert result["ITNCondition"].loc[("grits", "con", "f1")] == 1.0


def test_grits_paper_with_pred_missing_column_reversed(mock_paper_extraction_true: 'PaperExtraction', mock_paper_extraction_pred: 'PaperExtraction'):
    result = grits_paper(mock_paper_extraction_pred, mock_paper_extraction_true)
    assert result["Observation"].loc[("grits", "con", "precision")] < 1.0
    assert result["Observation"].loc[("grits", "con", "recall")] == 1.0
    assert result["Observation"].loc[("grits", "con", "f1")] < 1.0
    assert result["ITNCondition"].loc[("grits", "con", "f1")] == 1.0
