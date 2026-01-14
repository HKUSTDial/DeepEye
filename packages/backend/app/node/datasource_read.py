from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import DataSourceRepository
from app.node.base import BaseNode
from app.node.utils import create_engine, fetch_rows, validate_datasource_type, validate_table_name
from app.sandbox.docker_sandbox import DockerSandbox
from deepeye.workflows.models import Node, Port
from deepeye.workflows.registry import NodeSpec


class DataSourceReadHandler:
    def __init__(self, db: Session, user_id, sandbox: DockerSandbox | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.sandbox = sandbox

    def execute(self, node: Node, inputs: dict[str, Any], context: object) -> dict[str, Any]:
        datasource_id = node.params.get("datasource_id")
        datasource_url = node.params.get("datasource_url")
        datasource_type = node.params.get("datasource_type")
        table = node.params.get("table")
        query = node.params.get("query")
        limit = int(node.params.get("limit") or 100)
        
        if not datasource_id and not datasource_url:
            raise ValueError("datasource_id or datasource_url is required")

        # 1. Handle File Datasource
        if datasource_id:
            ds = DataSourceRepository(self.db).get_by_id_and_user(datasource_id, self.user_id)
            if not ds:
                raise ValueError("datasource not found")
            
            if getattr(ds, "category", "database") == "file":
                if not self.sandbox:
                    raise RuntimeError("Sandbox not available for file datasource")
                
                local_path = f"/workspace/data/{ds.name}"
                # Use pandas in sandbox to read file
                read_cmd = ""
                ext = ds.name.split('.')[-1].lower()
                if ext == 'csv':
                    read_cmd = f"import pandas as pd; df = pd.read_csv('{local_path}'); print(df.head({limit}).to_json(orient='records'))"
                elif ext in ['xlsx', 'xls']:
                    read_cmd = f"import pandas as pd; df = pd.read_excel('{local_path}'); print(df.head({limit}).to_json(orient='records'))"
                elif ext == 'json':
                    read_cmd = f"import pandas as pd; df = pd.read_json('{local_path}'); print(df.head({limit}).to_json(orient='records'))"
                elif ext == 'parquet':
                    read_cmd = f"import pandas as pd; df = pd.read_parquet('{local_path}'); print(df.head({limit}).to_json(orient='records'))"
                else:
                    raise ValueError(f"Unsupported file type: {ext}")
                
                import json
                result = self.sandbox.container.exec_run(
                    cmd=["python3", "-c", read_cmd],
                    workdir="/workspace"
                )
                if result.exit_code != 0:
                    raise RuntimeError(f"Failed to read file in sandbox: {result.output.decode()}")
                
                rows = json.loads(result.output.decode())
                return {"rows": rows}

            connection_string = ds.connection_string
        else:
            connection_string = datasource_url

        # 2. Handle Database Datasource
        validate_datasource_type(datasource_type)
        engine = create_engine(connection_string)
        if not query:
            if not table:
                raise ValueError("table or query is required")
            validate_table_name(str(table))
            query = f"SELECT * FROM {table} LIMIT {limit}"

        rows = fetch_rows(engine, str(query), limit)
        return {"rows": rows}


class DataSourceReadNode(BaseNode):
    node_type = "datasource.read"

    @classmethod
    def spec(cls) -> NodeSpec:
        return NodeSpec(
            type=cls.node_type,
            description="Read rows from a datasource.",
            params_schema={
                "datasource_id": {"type": "string", "required": False, "description": "Datasource ID"},
                "datasource_url": {"type": "string", "required": False, "description": "Connection string"},
                "datasource_type": {"type": "string", "required": False, "description": "postgres | mysql | sqlite"},
                "table": {"type": "string", "required": False, "description": "Table name"},
                "query": {"type": "string", "required": False, "description": "Optional SQL query"},
                "limit": {"type": "integer", "required": False, "description": "Row limit"},
            },
            outputs={"rows": Port(schema="list[dict]", description="Rows from the datasource.")},
        )

    @classmethod
    def build_handler(cls, db: Session, user_id, sandbox=None):
        return DataSourceReadHandler(db, user_id, sandbox=sandbox)
