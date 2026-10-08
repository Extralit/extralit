"""Appends a single table `LayoutBlock` to a `DoclingDocument`."""

from __future__ import annotations

from typing import Optional

from docling_core.types.doc import DoclingDocument, TableCell, TableData
from docling_core.types.doc.document import NodeItem, TableItem

from extralit_server.contexts.ocr.docling_builder import LayoutBlock, PageContext, make_prov


def build_table_data(cells: Optional[list[TableCell]]) -> TableData:
    """Size a `TableData` from its cells. `grid` is a computed field and must never be set."""
    if not cells:
        return TableData(num_rows=0, num_cols=0, table_cells=[])

    num_rows = max(cell.end_row_offset_idx for cell in cells)
    num_cols = max(cell.end_col_offset_idx for cell in cells)
    return TableData(num_rows=num_rows, num_cols=num_cols, table_cells=list(cells))


def make_cell(
    text: str,
    row: int,
    col: int,
    *,
    row_span: int = 1,
    col_span: int = 1,
    column_header: bool = False,
    row_header: bool = False,
    bbox=None,
) -> TableCell:
    """Build a cell with docling's exclusive end offsets (`end = start + span`)."""
    return TableCell(
        text=text,
        start_row_offset_idx=row,
        end_row_offset_idx=row + row_span,
        start_col_offset_idx=col,
        end_col_offset_idx=col + col_span,
        row_span=row_span,
        col_span=col_span,
        column_header=column_header,
        row_header=row_header,
        bbox=bbox,
    )


def add_table_block(
    doc: DoclingDocument,
    block: LayoutBlock,
    ctx: PageContext,
    parent: Optional[NodeItem] = None,
) -> TableItem:
    """Add one table, anchored by its page bbox."""
    prov = make_prov(ctx, block.bbox, text=None)
    return doc.add_table(
        data=build_table_data(block.cells),
        prov=prov,
        parent=parent,
        label=block.label,
    )
