#!/usr/bin/env python3
"""Open an interactive DuckDB shell connected to S3 transformed tables."""

import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

conn = duckdb.connect(":memory:")
conn.execute(f"SET s3_region = '{os.environ['AWS_DEFAULT_REGION']}'")
conn.execute(f"SET s3_access_key_id = '{os.environ['AWS_ACCESS_KEY_ID']}'")
conn.execute(f"SET s3_secret_access_key = '{os.environ['AWS_SECRET_ACCESS_KEY']}'")

bucket = os.environ["S3_BUCKET_NAME"]
prefix = "transformed"
tables = [
    "fct_daily_summary",
    "recent/fct_daily_summary",
    "recent/fct_workout_sets",
    "recent/fct_strava_activities",
    "fct_workout_sets",
    "fct_exercise_progress",
    "fct_personal_bests",
    "fct_strava_activities",
]

print("Creating views for transformed tables...")
for table in tables:
    view_name = table.replace("/", "__")
    s3_path = f"s3://{bucket}/{prefix}/{table}"
    try:
        conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet('{s3_path}')")
        print(f"  {view_name}")
    except Exception as e:
        print(f"  {view_name} (skipped: {e})")

print("\nAvailable tables (use as view names):")
for row in conn.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall():
    print(f"  {row[0]}")

print("\nStarting DuckDB shell. Type SQL queries or .quit to exit.\n")

# Pass connection to interactive mode
if sys.stdin.isatty():
    while True:
        try:
            query = input("D> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query or query == ".quit":
            break
        try:
            result = conn.execute(query)
            print(result.fetchdf().to_string())
        except Exception as e:
            print(f"Error: {e}")
else:
    # Piped input
    for line in sys.stdin:
        query = line.strip()
        if query:
            print(conn.execute(query).fetchdf().to_string())
