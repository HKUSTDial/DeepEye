from .base import BaseTool
from .sqlite_database import SQLiteDatabase
import re
from app.llm import LLM
from pydantic import Field, model_validator, ConfigDict

_TEXT2SQL_DESCRIPTION = """A tool to convert user's natural language question to SQL query."""


class Text2SQL(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "text2sql"
    description: str = _TEXT2SQL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The natural language question from the user.",
            }
        },
        "required": ["question"],
    }
    
    sqlite_database: SQLiteDatabase = Field(default_factory=SQLiteDatabase, description="The sqlite database to execute the SQL query.")
    llm: LLM = Field(default_factory=LLM, description="The llm to convert the natural language question to SQL query.")

    
    @model_validator(mode="after")
    def _initialize_text2sql(self) -> "Text2SQL":
        self.sqlite_database = SQLiteDatabase()
        self.llm = LLM(config_name="default")
        return self
    
    async def get_database_schema(self) -> str:
        """Get the schema of the sqlite database."""
        result = await self.sqlite_database.execute("SELECT sql FROM sqlite_master WHERE type='table' and name != 'sqlite_sequence'")
        table_ddls = [row[0] for row in result["rows"]]
        schema = "\n\n".join(table_ddls)
        return schema
    
    async def execute(self, question: str):
        """Convert the natural language question to SQL query."""
        schema = await self.get_database_schema()
        prompt = f"""
You are a helpful assistant that converts natural language questions to SQL queries.

Here is the schema of the sqlite database:
{schema}

Here is the natural language question:
{question}

Output format:
<think>
YOUR THINKING HERE
</think>
<sql>
YOUR COMPLETED SQL QUERY HERE
</sql>

Now, please convert the natural language question to SQL query, strictly follow the output format.
        """
        response = await self.llm.ask(
            [{"role": "user", "content": prompt}]
        )
        # print(prompt)
        # print("--------------------------------")
        # print(response.content)
        sql = re.search(r"<sql>(.*?)</sql>", response.content, re.DOTALL).group(1)
        return sql.strip()
    

if __name__ == "__main__":
    import asyncio
    text2sql = Text2SQL()
    sql = asyncio.run(text2sql.execute("How many schools are there in the database?"))
    print(sql)