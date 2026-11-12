"""Checkpoint 1: run `ParserService` on the gold PDFs and check table header rows against `gold.md`.

Usage: uv run python scripts/checkpoint1_dump.py [--gold-dir DIR] [--out DIR]
Exit code 1 when a gold table header row is missing from the markdown (adageba Table 2 excepted)
or the scanned paper does not route through liteparse with OCR.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from extralit_server.contexts.ocr.parsers.registry import default_service
from extralit_server.contexts.ocr.parsers.service import OCR_PARSER

PAPERS = ("robert1991-bullwho-scanned", "adageba2022-plosone-digital")
EXCEPTIONS = {("adageba2022-plosone-digital", "Table 2")}
SCANNED = "robert1991-bullwho-scanned"


@dataclass
class HeaderCheck:
    """Whether one gold table's header row survived into the parsed markdown."""

    table: str
    header: list[str]
    status: str  # ok | cells-elsewhere | missing | excepted
    absent: tuple[str, ...] = ()


HEADER_ROWS_SCANNED = 3


def _norm(text: str) -> str:
    """Letters and digits only, so spacing, hyphens and markdown padding do not matter."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def markdown_tables(markdown: str) -> list[list[str]]:
    """Each markdown table as its non-separator rows."""
    tables: list[list[str]] = []
    current: list[str] = []
    for line in [*markdown.splitlines(), ""]:
        if line.lstrip().startswith("|"):
            if not re.fullmatch(r"\|[\s:|-]+\|?", line.strip()):
                current.append(line)
        elif current:
            tables.append(current)
            current = []
    return tables


def gold_headers(gold_md: str) -> list[tuple[str, list[str]]]:
    """Header row of each `### Table N` section: the pipe row followed by a `|---|` separator."""
    headers: list[tuple[str, list[str]]] = []
    for section in re.split(r"^### ", gold_md, flags=re.MULTILINE)[1:]:
        title = re.match(r"(Table \d+)", section)
        lines = section.splitlines()
        for line, nxt in itertools.pairwise(lines):
            if line.startswith("|") and re.fullmatch(r"\|[\s:|-]+\|?", nxt.strip()):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                headers.append((title.group(1) if title else "?", [c for c in cells if c]))
                break
    return headers


def check_headers(paper: str, gold_md: str, markdown: str) -> list[HeaderCheck]:
    """A gold header is `ok` when all its cells sit in the first rows of one markdown table."""
    heads = ["".join(_norm(row) for row in table[:HEADER_ROWS_SCANNED]) for table in markdown_tables(markdown)]
    flat = _norm(markdown)
    results = []
    for table, header in gold_headers(gold_md):
        cells = [_norm(c) for c in header]
        if any(all(c in head for c in cells) for head in heads):
            status = "ok"
        elif all(c in flat for c in cells):
            status = "cells-elsewhere"
        else:
            status = "missing"
        if (paper, table) in EXCEPTIONS and status != "ok":
            status = "excepted"
        absent = tuple(c for c, n in zip(header, cells, strict=True) if n not in flat)
        results.append(HeaderCheck(table, header, status, absent))
    return results


def dump_paper(paper: str, gold_dir: Path, out_dir: Path) -> tuple[list[str], list[HeaderCheck], bool]:
    """Parse one gold paper, write its artifacts, and return its report lines, header checks and routing verdict."""
    pdf_bytes = (gold_dir / paper / "source.pdf").read_bytes()
    service = default_service()
    plan = service.plan(pdf_bytes)
    doc = service.parse(pdf_bytes, plan, name=paper, filename="source.pdf")
    markdown = doc.export_to_markdown()

    target = out_dir / paper
    target.mkdir(parents=True, exist_ok=True)
    (target / "markdown.md").write_text(markdown)
    lines = ["ref\tlabel\tpage\tl\tt\tr\tb"]
    for item, _ in doc.iterate_items(with_groups=False):
        for prov in item.prov or [None]:
            box = prov.bbox if prov else None
            coords = f"{box.l:.1f}\t{box.t:.1f}\t{box.r:.1f}\t{box.b:.1f}" if box else "\t\t\t"
            lines.append(f"{item.self_ref}\t{item.label.value}\t{prov.page_no if prov else ''}\t{coords}")
    (target / "items.tsv").write_text("\n".join(lines) + "\n")
    plan_json = {
        "tasks": [{"pages": list(t.pages), "parser": t.parser, "ocr": t.ocr} for t in plan.tasks],
        "parsers": plan.pages_by_parser,
        "pages_needing_ocr": list(plan.pages_needing_ocr),
        "ocr_pages": plan.ocr_pages,
        "ocr_skipped_pages": plan.ocr_skipped_pages,
    }
    (target / "plan.json").write_text(json.dumps(plan_json, indent=2))

    checks = check_headers(paper, (gold_dir / paper / "gold.md").read_text(), markdown)
    routed = True
    if paper == SCANNED:
        ocr_covered = {p for t in plan.tasks if t.parser == OCR_PARSER and t.ocr for p in t.pages}
        routed = bool(plan.pages_needing_ocr) and set(plan.pages_needing_ocr) <= ocr_covered

    labels = {}
    for item, _ in doc.iterate_items(with_groups=False):
        labels[item.label.value] = labels.get(item.label.value, 0) + 1
    summary = [
        f"## {paper}",
        f"- plan: `{json.dumps(plan_json['parsers'])}`; ocr_pages={plan.ocr_pages}; "
        f"ocr_skipped_pages (text layer read, no OCR)={plan.ocr_skipped_pages}; "
        f"pages_needing_ocr={list(plan.pages_needing_ocr)}",
        f"- items by label: `{json.dumps(labels, sort_keys=True)}`",
    ]
    if paper == SCANNED:
        summary.append(f"- every page needing OCR routed through liteparse+OCR: **{routed}**")
    summary.append("- gold table header rows:")
    summary += [
        f"  - {c.table}: **{c.status}** — {' | '.join(c.header)}"
        + (f" (absent cells: {list(c.absent)})" if c.absent else "")
        for c in checks
    ]
    return summary, checks, routed


def main() -> int:
    """Dump every checkpoint paper and return non-zero if any gate fails."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-dir", type=Path, default=Path("~/Projects/Extralit/data/gold").expanduser())
    parser.add_argument("--out", type=Path, default=Path("/tmp/eng85-checkpoint1"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    report: list[str] = ["# Checkpoint 1 report", ""]
    failed = False
    for paper in PAPERS:
        summary, checks, routed = dump_paper(paper, args.gold_dir, args.out)
        report += [*summary, ""]
        failed |= not routed or any(c.status in ("missing", "cells-elsewhere") for c in checks)
    (args.out / "report.md").write_text("\n".join(report))
    print("\n".join(report))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
