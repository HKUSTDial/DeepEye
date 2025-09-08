from .base import BaseTool
import sqlite3


DB_PATH = "/hpc2hdd/home/bli303/boyan_project/label/dev_databases/california_schools/california_schools.sqlite"


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

    async def execute(self, query: str):
        """Execute the SQL query and return the result with column names."""
        with sqlite3.connect(DB_PATH) as connection:
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
