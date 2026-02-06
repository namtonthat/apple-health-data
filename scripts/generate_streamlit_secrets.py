#!/usr/bin/env python3
"""Generate .streamlit/secrets.toml from .env file.

Usage:
    python scripts/generate_streamlit_secrets.py

This reads your .env file and generates a secrets.toml file containing
only sensitive values (API keys, credentials). Non-sensitive config
is stored in pyproject.toml under [tool.dashboard].
"""

from pathlib import Path

# Only these keys are secrets (credentials, API keys)
SECRET_KEYS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REFRESH_TOKEN",
    "HEVY_API_KEY",
]


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse .env file into a dictionary."""
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
    return env_vars


def generate_secrets_toml(env_vars: dict[str, str]) -> str:
    """Generate secrets.toml content from env vars."""
    lines = [
        "# =============================================================================",
        "# Streamlit Cloud Secrets",
        "# =============================================================================",
        "# Copy this into Streamlit Cloud: Settings → Secrets",
        "#",
        "# These are SENSITIVE values only. Non-sensitive config (bucket names, goals)",
        "# is stored in pyproject.toml under [tool.dashboard].",
        "# =============================================================================",
        "",
    ]

    # AWS credentials
    lines.append("# AWS Credentials (REQUIRED)")
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        if key in env_vars:
            lines.append(f'{key} = "{env_vars[key]}"')
    lines.append("")

    # Strava (optional)
    strava_keys = ["STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN"]
    if any(k in env_vars for k in strava_keys):
        lines.append("# Strava API (OPTIONAL)")
        for key in strava_keys:
            if key in env_vars:
                lines.append(f'{key} = "{env_vars[key]}"')
        lines.append("")

    # Hevy (optional)
    if "HEVY_API_KEY" in env_vars:
        lines.append("# Hevy API (OPTIONAL)")
        lines.append(f'HEVY_API_KEY = "{env_vars["HEVY_API_KEY"]}"')

    return "\n".join(lines).rstrip() + "\n"


def main():
    # Find project root (where .env is)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / ".env"
    secrets_dir = project_root / ".streamlit"
    secrets_path = secrets_dir / "secrets.toml"

    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        print("Please create a .env file first (copy from .env.example)")
        return 1

    # Parse .env
    env_vars = parse_env_file(env_path)

    # Check for required keys
    required = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}
    missing = required - set(env_vars.keys())
    if missing:
        print(f"Warning: Missing required secrets in .env: {', '.join(sorted(missing))}")

    # Generate secrets.toml
    secrets_content = generate_secrets_toml(env_vars)

    # Ensure .streamlit directory exists
    secrets_dir.mkdir(exist_ok=True)

    # Write secrets.toml
    secrets_path.write_text(secrets_content)
    print(f"Generated {secrets_path}")
    print()
    print("To deploy on Streamlit Cloud:")
    print("1. Go to your app settings → Secrets")
    print("2. Copy the contents of .streamlit/secrets.toml")
    print()
    print("Note: Non-sensitive config (bucket names, goals, URLs) is in pyproject.toml")

    return 0


if __name__ == "__main__":
    exit(main())
