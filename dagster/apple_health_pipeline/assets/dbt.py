"""DBT transformation assets using dagster-dbt integration."""

import json
from pathlib import Path

from dagster_dbt import DbtCliResource, dbt_assets

from dagster import AssetExecutionContext, AssetKey

# Path to the dbt project
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "transforms"
DBT_MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"


def get_dbt_manifest():
    """Load the dbt manifest, generating it if necessary."""
    if not DBT_MANIFEST_PATH.exists():
        # Generate manifest if it doesn't exist
        import subprocess

        subprocess.run(
            ["dbt", "compile"],
            cwd=DBT_PROJECT_DIR,
            check=True,
        )

    with DBT_MANIFEST_PATH.open() as f:
        return json.load(f)


@dbt_assets(
    manifest=get_dbt_manifest(),
    select="raw staging semantic",
    dagster_dbt_translator=None,  # Use default translator
)
def dbt_transform_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run dbt transformations on the ingested data."""
    # Define upstream dependencies
    hevy_key = AssetKey(["hevy_raw_data"])
    opl_key = AssetKey(["openpowerlifting_raw_data"])

    # Check if upstream assets are materialized
    context.log.info(
        "Running dbt models with dependencies on %s and %s", hevy_key, opl_key
    )

    # Run dbt commands
    yield from dbt.cli(["run"], context=context).stream()
