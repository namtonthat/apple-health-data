import duckdb
import polars as pl
from helpers import logger


def create_reflections_table(db_path: str) -> None:
    """
    Create the reflections table in DuckDB if it does not exist.

    Args:
        db_path: Path to the DuckDB database file.
    """
    con = duckdb.connect(database=db_path, read_only=False)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS reflections (
                week VARCHAR,
                q1 VARCHAR,
                q2 VARCHAR,
                q3 VARCHAR,
                q4 VARCHAR,
                q5 VARCHAR,
                timestamp VARCHAR
            )
            """
        )
        logger.info("Reflections table ensured in %s", db_path)
    except Exception as e:
        logger.error("Error creating reflections table: %s", e)
        raise
    finally:
        con.close()


def load_reflections_from_duckdb(db_path: str) -> pl.DataFrame:
    """
    Load reflections data from a DuckDB database and return a Polars DataFrame.

    If the table does not exist, it is created first.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        A Polars DataFrame with reflections data.
    """
    # Ensure the reflections table exists.
    create_reflections_table(db_path)

    con = duckdb.connect(database=db_path, read_only=False)
    try:
        # Use DuckDB's Arrow integration to fetch data.
        arrow_table = con.execute("SELECT * FROM reflections").arrow()
        df = pl.from_arrow(arrow_table)
        logger.info("Loaded reflections data from %s", db_path)
    except Exception as e:
        logger.error("Error loading reflections: %s", e)
        df = pl.DataFrame()
    finally:
        con.close()
    return df


def insert_reflections_into_duckdb(db_path: str, new_entry: dict[str, str]) -> None:
    """
    Insert a new reflections entry into the DuckDB database.

    Assumes the reflections table has columns: week, q1, q2, q3, q4, q5, timestamp.

    Args:
        db_path: Path to the DuckDB database file.
        new_entry: A dictionary representing the new reflections entry.
    """
    con = duckdb.connect(database=db_path, read_only=False)
    columns = ", ".join(new_entry.keys())
    values = ", ".join(f"'{v}'" for v in new_entry.values())
    query = f"INSERT INTO reflections ({columns}) VALUES ({values})"
    logger.info("Executing query: %s", query)
    con.execute(query)
    con.close()
