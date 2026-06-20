from __future__ import annotations

from pipelines.sources.hevy import _dedupe_by_id


def test_dedupe_drops_pagination_overlap():
    # Same workout id surfacing on two pages (Hevy paginates newest-first).
    records = [
        {"id": "w1", "title": "Squat"},
        {"id": "w2", "title": "Bench"},
        {"id": "w1", "title": "Squat"},  # overlap repeat
    ]
    assert [r["id"] for r in _dedupe_by_id(records)] == ["w1", "w2"]


def test_dedupe_keeps_first_occurrence_order():
    records = [{"id": i} for i in (3, 1, 3, 2, 1, 2)]
    assert [r["id"] for r in _dedupe_by_id(records)] == [3, 1, 2]


def test_dedupe_passes_through_records_without_id():
    # Missing/None keys are not collapsed into one another.
    records = [{"id": None}, {"id": None}, {"foo": 1}]
    assert len(list(_dedupe_by_id(records))) == 3
