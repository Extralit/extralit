from types import SimpleNamespace

from rich.console import Console

from extralit.cli.documents.import_bib import (
    _build_documents_payload,
    _dataframe_to_import_history_format,
    _match_pdfs_to_dataframe,
    _parse_bibtex_to_dataframe,
)

BIB = """
@article{smith2020, title={{A} Study}, doi={10.1/x}, file={Full Text:papers/smith2020_main.pdf:application/pdf}}
@article{jones2021, title={Other}, year={2021}}
@article{lee2019, title={No pdf}}
"""


def test_parse_match_and_payload(tmp_path):
    (tmp_path / "refs.bib").write_text(BIB)
    pdfs = tmp_path / "pdfs"
    (pdfs / "sub").mkdir(parents=True)
    (pdfs / "sub" / "smith2020_main.pdf").write_bytes(b"%PDF-1.4 a")
    (pdfs / "jones2021_paper.pdf").write_bytes(b"%PDF-1.4 bb")
    console = Console(quiet=True)

    df = _parse_bibtex_to_dataframe(tmp_path / "refs.bib", console)
    assert df.columns[0] == "reference" and df.columns[-1] == "files"
    assert df.filter(df["reference"] == "smith2020")["title"].item() == "A Study"
    assert df.filter(df["reference"] == "lee2019")["doi"].item() is None

    matched = _match_pdfs_to_dataframe(df, pdfs, console)
    files = dict(zip(matched["reference"], matched["files"], strict=True))
    assert files["smith2020"].endswith("sub/smith2020_main.pdf")
    assert files["jones2021"].endswith("jones2021_paper.pdf")
    assert files["lee2019"] == ""

    payload = _build_documents_payload(matched, SimpleNamespace(id="ws"), "c1")
    assert payload["smith2020"]["associated_files"] == [{"filename": "smith2020_main.pdf", "size": 10}]
    assert payload["lee2019"]["associated_files"] == []
    assert payload["smith2020"]["document_create"]["metadata"] == {"collections": ["c1"], "source": "bib_import"}
    assert payload["smith2020"]["document_create"]["doi"] == "10.1/x"

    history = _dataframe_to_import_history_format(matched)
    rows = {r["reference"]: r for r in history["data"]}
    assert rows["lee2019"]["year"] is None
    assert rows["lee2019"]["doi"] == ""
    assert {"name": "reference", "type": "string"} in history["schema"]["fields"]


def test_empty_bib_gives_empty_payload(tmp_path):
    (tmp_path / "refs.bib").write_text("% no entries\n")
    console = Console(quiet=True)
    df = _match_pdfs_to_dataframe(_parse_bibtex_to_dataframe(tmp_path / "refs.bib", console), tmp_path, console)
    assert _build_documents_payload(df, SimpleNamespace(id="ws"), None) == {}
