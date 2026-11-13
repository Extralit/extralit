"""Filter clause builder and RRF SQL on synthetic legs."""

from __future__ import annotations

from uuid import uuid4

import duckdb
import pytest

from extralit_server.contexts.retrieval.search import PAYLOAD, SearchFilters, _column, build_filter, fuse_sql


def leg(rows: list[tuple[str, float]], score: str) -> str:
    values = ", ".join(
        f"('{cid}', 'd', 'r', 0, 'text', 't-{cid}', ['h'], ['#/texts/0'], 1, 1, {value})" for cid, value in rows
    )
    return f"SELECT * FROM (VALUES {values}) AS t({', '.join(PAYLOAD)}, {score})"


def fuse(fts, vector, k=60, limit=10):
    return (
        duckdb.connect()
        .execute(fuse_sql(leg(fts, "bm25"), leg(vector, "distance") if vector else None, k, limit))
        .fetchall()
    )


class TestFilter:
    def test_unfiltered_is_none(self):
        assert build_filter(None) is None
        assert build_filter(SearchFilters()) is None

    def test_clauses_are_anded_and_quoted(self):
        doc = uuid4()
        clause = build_filter(
            SearchFilters(document_ids=[doc], references=["O'Brien2020"], pages=[2, 3], kinds=["table"])
        )

        assert clause == (
            f"document_id IN ('{doc}') AND reference IN ('O''Brien2020') AND kind IN ('table') "
            "AND ((page_start <= 2 AND page_end >= 2) OR (page_start <= 3 AND page_end >= 3))"
        )

    def test_document_ids_must_be_uuids(self):
        with pytest.raises(ValueError):
            build_filter(SearchFilters(document_ids=["x' OR 1=1 --"]))

    def test_kinds_are_allow_listed(self):
        with pytest.raises(ValueError):
            build_filter(SearchFilters(kinds=["text' OR 1=1"]))

    def test_pages_must_be_integers(self):
        with pytest.raises(ValueError):
            build_filter(SearchFilters(pages=["1; DROP"]))

    def test_column_allow_list(self):
        assert _column("reference") == "reference"
        with pytest.raises(ValueError):
            _column("text; DROP TABLE chunks")


class TestFuse:
    def test_agreement_across_legs_wins(self):
        rows = fuse([("a", 9.0), ("b", 5.0), ("c", 1.0)], [("b", 0.1), ("c", 0.2), ("d", 0.3)])

        assert [r[0] for r in rows] == ["b", "c", "a", "d"]

    def test_rrf_score_is_reciprocal_rank_sum(self):
        rows = {r[0]: r for r in fuse([("a", 9.0), ("b", 5.0)], [("b", 0.1)], k=10)}

        assert rows["b"][-1] == pytest.approx(1 / 12 + 1 / 11)
        assert rows["a"][-1] == pytest.approx(1 / 11)

    def test_per_leg_scores_survive_fusion(self):
        rows = {r[0]: r for r in fuse([("a", 9.0)], [("b", 0.25)])}

        assert (rows["a"][-3], rows["a"][-2]) == (9.0, None)
        assert (rows["b"][-3], rows["b"][-2]) == (None, 0.25)

    def test_limit_applies_after_fusion(self):
        assert len(fuse([("a", 3.0), ("b", 2.0), ("c", 1.0)], None, limit=2)) == 2

    def test_missing_vector_leg_is_fts_only(self):
        rows = fuse([("a", 3.0), ("b", 2.0)], None)

        assert [r[0] for r in rows] == ["a", "b"]
        assert all(r[-2] is None for r in rows)
