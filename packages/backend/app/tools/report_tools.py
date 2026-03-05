"""Report generation tool for supervisor agent."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.node.report.runtime import create_report_temp_dir, run_report_pipeline
from app.repositories import DataSourceRepository
from app.services.minio_service import download_bytes
from deepeye.tools.base import tool

logger = logging.getLogger(__name__)


def _export_datasource_to_csv(datasource_id: str, output_path: str) -> bool:
    """Export a datasource to CSV file. Returns True if successful."""
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    with Session() as db:
        ds = DataSourceRepository(db).get(datasource_id)
        if not ds:
            logger.warning(f"DataSource not found: {datasource_id}")
            return False
        
        category = getattr(ds, "category", "database")
        
        if category == "file":
            # File datasource: storage_path is a MinIO object key (see datasource_file_service)
            storage_path = getattr(ds, "storage_path", None)
            if not storage_path or storage_path == "pending":
                logger.warning(f"File datasource {datasource_id} has no usable storage_path")
                return False
            try:
                data = download_bytes(settings.MINIO_DATA_BUCKET, storage_path)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(data)
                return True
            except Exception as e:
                logger.warning(f"Failed to export file datasource {datasource_id}: {e}")
                return False
        
        elif category == "database":
            # Database datasource: export to CSV
            import pandas as pd
            from sqlalchemy import create_engine as sa_create_engine, inspect
            
            connection_string = ds.connection_string
            if not connection_string:
                return False
            
            try:
                from app.node.utils import normalize_connection_string
                data_engine = sa_create_engine(normalize_connection_string(connection_string))
                inspector = inspect(data_engine)
                tables = inspector.get_table_names()
                
                if not tables:
                    return False
                
                # Export first table (or merge multiple if needed)
                first_table = tables[0]
                df = pd.read_sql_table(first_table, data_engine)
                df.to_csv(output_path, index=False)
                return True
            except Exception as e:
                logger.error(f"Failed to export datasource {datasource_id}: {e}")
                return False
    
    return False


def create_generate_report_tool(session_id: str):
    """Create a tool that generates reports using report_module pipeline."""
    
    @tool
    async def generate_report(query: str, datasource_ids: list[str]) -> str:
        """
        Generate a comprehensive data analysis report using the report_module pipeline.
        
        Args:
            query: User's analysis request or question about the data
            datasource_ids: List of datasource UUIDs to analyze. Must be the "id"
                values from Available Data Sources (UUID format), not file names.
            
        Returns:
            Status message. The report HTML will be displayed in the right panel.
        """
        if not datasource_ids:
            return "Error: At least one datasource is required to generate a report."
        
        tmp_dir = create_report_temp_dir(session_id, prefix="deepeye_report_datasource_")
        csv_paths = []
        
        try:
            for ds_id in datasource_ids:
                csv_path = Path(tmp_dir) / f"datasource_{ds_id}.csv"
                if _export_datasource_to_csv(ds_id, str(csv_path)):
                    csv_paths.append(str(csv_path))
                else:
                    logger.warning(f"Failed to export datasource {ds_id}")
            
            if not csv_paths:
                return "Error: Failed to export any datasources to CSV."
            
            # Run report pipeline (it will publish steps and report_done to Redis)
            report_html, error = run_report_pipeline(session_id, query, csv_paths)
            
            if error:
                return f"Report generation failed: {error}"
            
            return f"Report generation completed successfully. {len(csv_paths)} datasource(s) analyzed. View the report in the right panel."
            
        except Exception as e:
            logger.exception("Report generation failed")
            return f"Report generation error: {str(e)}"
        finally:
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)
    
    return generate_report
