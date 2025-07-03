"""DBT transformation assets using dagster-dbt integration."""

from pathlib import Path

from dagster_dbt import DbtCliResource, dbt_assets

from dagster import AssetExecutionContext

# Path to the dbt project
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "transforms"


@dbt_assets(
    manifest=DBT_PROJECT_DIR / "target" / "manifest.json",
)
def apple_health_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run dbt transformations on the ingested data."""
    yield from dbt.cli(["run"], context=context).stream()
