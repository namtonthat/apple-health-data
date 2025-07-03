"""Asset group definitions for the Apple Health pipeline."""

# Define groups with metadata for better visualization
ASSET_GROUPS = {
    "ingestion": {
        "description": "Raw data ingestion from external sources",
        "metadata": {"color": "#1f77b4"},  # Blue
    },
    "staging": {
        "description": "Initial data loading and timezone conversion",
        "metadata": {"color": "#ff7f0e"},  # Orange
    },
    "raw": {
        "description": "Data unnesting and deduplication",
        "metadata": {"color": "#2ca02c"},  # Green
    },
    "semantic": {
        "description": "Business logic and metric calculations",
        "metadata": {"color": "#d62728"},  # Red
    },
    "calendar": {
        "description": "Calendar generation and export",
        "metadata": {"color": "#9467bd"},  # Purple
    },
}
