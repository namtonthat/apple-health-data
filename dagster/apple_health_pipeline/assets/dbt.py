"""DBT transformation assets using dagster-dbt integration."""

from pathlib import Path
from typing import Any, Mapping, Optional

from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

from dagster import AssetExecutionContext

# Path to the dbt project
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent.parent / "transforms"


class CustomDagsterDbtTranslator(DagsterDbtTranslator):
    """Custom translator to assign group names based on dbt model paths."""

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> Optional[str]:
        """Assign group names based on the model's directory."""
        # Get the model path
        model_path = dbt_resource_props.get("path", "")

        # Determine group based on directory
        if "staging/" in model_path:
            return "staging"
        elif "raw/" in model_path:
            return "raw"
        elif "semantic/" in model_path:
            return "semantic"
        else:
            return "transformation"


@dbt_assets(
    manifest=DBT_PROJECT_DIR / "target" / "manifest.json",
    dagster_dbt_translator=CustomDagsterDbtTranslator(),
)
def apple_health_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run dbt transformations on the ingested data."""
    yield from dbt.cli(["run"], context=context).stream()
