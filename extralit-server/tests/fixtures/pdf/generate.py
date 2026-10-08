"""Regenerate the layout fixture PDFs.

Committed output: `sample.pdf` (untagged) and `sample_tagged.pdf` (structure tree + MCIDs).
Run with `uv run python tests/fixtures/pdf/generate.py`. Uses only pikepdf, already a dependency,
so the fixtures stay reproducible without pulling in a PDF writer.
"""

import zlib
from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name, Stream, String

HERE = Path(__file__).parent

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0

# All coordinates below are PDF-native (bottom-left origin), which is what the parsers must flip.
TITLE = ("A Study of Layout Extraction", 72, 720, 18)
HEADING = ("Methods", 72, 680, 14)
BODY = ("We evaluated two parsers on a shared corpus of documents.", 72, 655, 11)

TABLE_LEFT, TABLE_RIGHT = 72, 372
TABLE_TOP, TABLE_BOTTOM = 600, 540
TABLE_MID_Y = 570
TABLE_MID_X = 222
TABLE_CELLS = [
    ("Group", 80, 580),
    ("N", 230, 580),
    ("control", 80, 550),
    ("42", 230, 550),
]

IMAGE_X, IMAGE_Y, IMAGE_W, IMAGE_H = 72, 380, 120, 90
CAPTION = ("Figure 1. A red square.", 72, 360, 10)


def _text_op(text: str, x: float, y: float, size: float, font: str = "F1") -> str:
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return f"BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET\n"


def _table_ops() -> str:
    return (
        "0.5 w 0 0 0 RG\n"
        f"{TABLE_LEFT} {TABLE_BOTTOM} {TABLE_RIGHT - TABLE_LEFT} {TABLE_TOP - TABLE_BOTTOM} re S\n"
        f"{TABLE_LEFT} {TABLE_MID_Y} m {TABLE_RIGHT} {TABLE_MID_Y} l S\n"
        f"{TABLE_MID_X} {TABLE_BOTTOM} m {TABLE_MID_X} {TABLE_TOP} l S\n"
    )


def _image_ops() -> str:
    return f"q {IMAGE_W} 0 0 {IMAGE_H} {IMAGE_X} {IMAGE_Y} cm /Im1 Do Q\n"


def _make_image(pdf: pikepdf.Pdf) -> Stream:
    width, height = 8, 6
    raw = bytes([255, 0, 0] * width * height)
    image = Stream(pdf, zlib.compress(raw))
    image.Type = Name.XObject
    image.Subtype = Name.Image
    image.Width = width
    image.Height = height
    image.ColorSpace = Name.DeviceRGB
    image.BitsPerComponent = 8
    image.Filter = Name.FlateDecode
    return image


def _base_pdf() -> tuple[pikepdf.Pdf, Dictionary]:
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(
        Dictionary(
            Type=Name.Font,
            Subtype=Name.Type1,
            BaseFont=Name.Helvetica,
            Encoding=Name.WinAnsiEncoding,
        )
    )
    resources = Dictionary(Font=Dictionary(F1=font), XObject=Dictionary(Im1=_make_image(pdf)))
    return pdf, resources


def _add_page(pdf: pikepdf.Pdf, resources: Dictionary, content: str) -> Dictionary:
    stream = Stream(pdf, content.encode("latin-1"))
    page = pdf.make_indirect(
        Dictionary(
            Type=Name.Page,
            MediaBox=Array([0, 0, PAGE_WIDTH, PAGE_HEIGHT]),
            Resources=resources,
            Contents=stream,
        )
    )
    pdf.pages.append(pikepdf.Page(page))
    return page


def build_untagged(path: Path) -> None:
    pdf, resources = _base_pdf()
    content = (
        _text_op(*TITLE)
        + _text_op(*HEADING)
        + _text_op(*BODY)
        + _table_ops()
        + "".join(_text_op(t, x, y, 10) for t, x, y in TABLE_CELLS)
        + _image_ops()
        + _text_op(*CAPTION)
    )
    _add_page(pdf, resources, content)
    pdf.save(path)


def build_tagged(path: Path) -> None:
    """Same content, wrapped in marked-content sequences and a structure tree."""
    pdf, resources = _base_pdf()

    def marked(tag: str, mcid: int, ops: str) -> str:
        return f"/{tag} <</MCID {mcid}>> BDC\n{ops}EMC\n"

    content = (
        marked("H1", 0, _text_op(*TITLE))
        + marked("H2", 1, _text_op(*HEADING))
        + marked("P", 2, _text_op(*BODY))
        + marked(
            "Table",
            3,
            _table_ops() + "".join(_text_op(t, x, y, 10) for t, x, y in TABLE_CELLS),
        )
        + marked("Figure", 4, _image_ops())
        + marked("Caption", 5, _text_op(*CAPTION))
    )
    page = _add_page(pdf, resources, content)

    struct_root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    kids = Array()
    # Role names here are non-standard on purpose; /RoleMap is what resolves them.
    for tag, mcid in [("H1", 0), ("H2", 1), ("P", 2), ("Table", 3), ("Figure", 4), ("Caption", 5)]:
        kids.append(
            pdf.make_indirect(
                Dictionary(
                    Type=Name.StructElem,
                    S=Name("/" + tag),
                    P=struct_root,
                    Pg=page,
                    K=mcid,
                )
            )
        )
    struct_root.K = kids
    struct_root.RoleMap = Dictionary(
        **{
            "H1": Name.H1,
            "H2": Name.H2,
            "P": Name.P,
            "Table": Name.Table,
            "Figure": Name.Figure,
            "Caption": Name.Caption,
        }
    )
    pdf.Root.StructTreeRoot = struct_root
    pdf.Root.MarkInfo = Dictionary(Marked=True)
    pdf.Root.Lang = String("en-US")
    pdf.save(path)


if __name__ == "__main__":
    build_untagged(HERE / "sample.pdf")
    build_tagged(HERE / "sample_tagged.pdf")
    print(f"wrote {HERE / 'sample.pdf'} and {HERE / 'sample_tagged.pdf'}")
