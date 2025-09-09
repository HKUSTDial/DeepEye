from .base import BaseTool
import sqlite3
from app.config.config import config
from pydantic import model_validator
from app.logger import logger


class SQLiteDatabase(BaseTool):
    name: str = "sqlite_database"
    description: str = "A tool to query the sqlite database."
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL query to execute, only read-only operations are allowed.",
            }
        },
        "required": ["query"],
    }
    
    path: str = None
    
    @model_validator(mode="after")
    def _initialize_sqlite_database(self) -> "SQLiteDatabase":
        self.path = config.sqlite_database_config.path
        if self.path is None:
            logger.error("SQLite database tool is used, but the database path is not set")
            raise ValueError("SQLite database tool is used, but the database path is not set")
        return self

    async def execute(self, query: str):
        """Execute the SQL query and return the result with column names."""
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(query)
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return {
                "column_names": column_names,
                "rows": rows
            }



if __name__ == "__main__":
    import asyncio
    db = SQLiteDatabase()
    # select all table names
    result = asyncio.run(db.execute("DROP TABLE IF EXISTS test1"))
    print("列名:", result["column_names"])
    print("数据:", result["rows"])
