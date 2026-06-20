"""
dlt source for Hevy API.

Extracts data as close to source as possible.
Only dlt metadata is added (_dlt_load_id, _dlt_id, _dlt_parent_id).

API Documentation: https://api.hevyapp.com/docs/

Confirmed API details:
- Base URL: https://api.hevyapp.com/v1
- Auth: api-key header
- Pagination: page & pageSize query params
- Response: {"page": 1, "page_count": N, "workouts": [...]}
"""

import itertools
import os
from typing import Iterable, Iterator

import dlt
from dlt.sources.helpers.rest_client import RESTClient
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator

BASE_URL = "https://api.hevyapp.com/v1"


PAGE_SIZE = 10  # API max is 10


def _dedupe_by_id(records: Iterable[dict], key: str = "id") -> Iterator[dict]:
    """Yield each record once per primary key, dropping later duplicates.

    The Hevy API paginates newest-first, so a workout logged mid-pagination can
    appear on two consecutive pages. De-duplicating here keeps the landing
    snapshot clean (one row per workout) regardless of pagination overlap.
    Records without a key are passed through untouched.
    """
    seen: set = set()
    for record in records:
        rid = record.get(key)
        if rid is None:
            yield record
            continue
        if rid in seen:
            continue
        seen.add(rid)
        yield record


def _get_client() -> RESTClient:
    """Create REST client with authentication."""
    api_key = os.environ.get("HEVY_API_KEY")
    if not api_key:
        raise ValueError("HEVY_API_KEY environment variable required")

    return RESTClient(
        base_url=BASE_URL,
        headers={
            "api-key": api_key,
            "accept": "application/json",
        },
        paginator=PageNumberPaginator(
            page_param="page",
            total_path="page_count",
            base_page=1,
        ),
    )


@dlt.source(name="hevy", max_table_nesting=2)
def hevy_source(
    workouts: bool = True,
    exercise_templates: bool = True,
    routines: bool = True,
):
    """
    Hevy API source.

    Args:
        workouts: Extract workouts with exercises and sets
        exercise_templates: Extract exercise template definitions
        routines: Extract saved routines

    Yields data as-is from API, dlt adds:
        - _dlt_load_id: Unique load identifier
        - _dlt_id: Unique row identifier
        - Automatic nested table extraction (workouts__exercises, workouts__exercises__sets)
    """
    resources = []

    if workouts:
        resources.append(workouts_resource())
    if exercise_templates:
        resources.append(exercise_templates_resource())
    if routines:
        resources.append(routines_resource())

    return resources


@dlt.resource(
    name="workouts",
    write_disposition="replace",
    primary_key="id",
    columns={"id": {"nullable": False}},
)
def workouts_resource() -> Iterator[dict]:
    """
    Extract workouts with nested exercises and sets.

    Uses ``replace`` (full overwrite): the API returns the complete workout
    history on every run (no incremental cursor), so overwriting the landing
    tables is both correct and avoids the fragile nested Delta upsert MERGE,
    which fails on this deeply nested table. dbt staging dedups/typing downstream.

    dlt will automatically:
    - Flatten nested 'exercises' into 'workouts__exercises' table
    - Flatten nested 'sets' into 'workouts__exercises__sets' table
    - Add _dlt_parent_id for relationships
    """
    client = _get_client()

    pages = client.paginate(
        "workouts",
        params={"pageSize": PAGE_SIZE},
        data_selector="workouts",
    )
    # One row per workout, regardless of pagination overlap.
    yield from _dedupe_by_id(itertools.chain.from_iterable(pages))


@dlt.resource(
    name="exercise_templates",
    write_disposition="replace",
    primary_key="id",
)
def exercise_templates_resource() -> Iterator[dict]:
    """Extract exercise template definitions."""
    client = _get_client()

    for page in client.paginate(
        "exercise_templates",
        params={"pageSize": PAGE_SIZE},
        data_selector="exercise_templates",
    ):
        yield from page


@dlt.resource(
    name="routines",
    write_disposition="replace",
    primary_key="id",
)
def routines_resource() -> Iterator[dict]:
    """Extract saved workout routines/templates."""
    client = _get_client()

    for page in client.paginate(
        "routines",
        params={"pageSize": PAGE_SIZE},
        data_selector="routines",
    ):
        yield from page
