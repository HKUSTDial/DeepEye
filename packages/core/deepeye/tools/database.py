import csv
import uuid
import os
from typing import List, Optional
from langchain_community.utilities import SQLDatabase
from pydantic import BaseModel, Field

from deepeye.tools.base import tool

# Wrapper to hold the database connection instance
class DBContext:
    _db: Optional[SQLDatabase] = None
    _artifact_dir: str = "artifacts"

    @classmethod
    def set_db(cls, db: SQLDatabase):
        cls._db = db
        if not os.path.exists(cls._artifact_dir):
            os.makedirs(cls._artifact_dir)

    @classmethod
    def get_db(cls) -> SQLDatabase:
        if cls._db is None:
            raise ValueError("Database not initialized. Call DBContext.set_db(db) first.")
        return cls._db

@tool
def list_tables() -> str:
    """List all table names in the database."""
    db = DBContext.get_db()
    return ", ".join(db.get_usable_table_names())

@tool
def get_schema(table_names: List[str]) -> str:
    """
    Get the schema and sample rows for the specified tables.
    Useful for understanding table structure before querying.
    """
    db = DBContext.get_db()
    return db.get_table_info(table_names)

@tool
def execute_sql(sql: str) -> str:
    """
    Execute a SQL query.
    If successful, returns a preview AND saves the full result to a CSV file.
    The CSV file path is returned in the output.
    """
    db = DBContext.get_db()
    try:
        # We need to get the raw connection result to save to CSV
        # LangChain's db.run returns string, so we might need run_no_throw or raw execution
        # But db.run is safer. Let's use db._execute to get cursor or raw result if possible,
        # OR just parse the result? No, parsing string is bad.
        # Let's use SQLAlchemy execution directly for data export.
        
        import sqlalchemy
        
        with db._engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(sql))
            keys = result.keys()
            rows = result.fetchall()
            
            # Save to CSV
            filename = f"query_result_{uuid.uuid4().hex[:8]}.csv"
            filepath = os.path.join(DBContext._artifact_dir, filename)
            
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(keys)
                writer.writerows(rows)
            
            # Prepare Preview (Top 5 rows)
            preview_rows = rows[:5]
            preview_str = str(preview_rows)
            
            return (
                f"Query Executed Successfully.\n"
                f"Full result saved to: {filepath}\n"
                f"Row Count: {len(rows)}\n"
                f"Preview: {preview_str}"
            )

    except Exception as e:
        return f"Error: {str(e)}"

def get_database_tools(db: SQLDatabase) -> List[tool]:
    """
    Helper to initialize the DB context and return the tool list.
    """
    DBContext.set_db(db)
    return [list_tables, get_schema, execute_sql]

