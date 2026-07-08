import os
from pathlib import Path

def resolve_db_path(db_id: str, base_dir: str = None) -> str:
    """Resolve absolute path to SQLite file given db_id."""
    if base_dir is None:
        # Default to pamo_sql/data/raw/bird
        base_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "bird"
    return str(Path(base_dir) / "database" / db_id / f"{db_id}.sqlite")

def resolve_desc_dir(db_id: str, base_dir: str = None) -> str:
    """Resolve directory to database description csv/txt files."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "bird"
    return str(Path(base_dir) / "database_description" / db_id)
