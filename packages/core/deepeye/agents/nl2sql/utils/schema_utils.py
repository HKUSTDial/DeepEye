"""
Schema Utilities - Functions for handling database schema operations.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from deepeye.datasource.datasource import DatabaseMetadata, TableMetadata, ColumnMetadata

logger = logging.getLogger(__name__)


def get_database_schema_profile(metadata: DatabaseMetadata) -> str:
    """
    Generate a text profile of the database schema for LLM prompts.

    Args:
        metadata: DatabaseMetadata object

    Returns:
        Formatted string representation of the schema
    """
    lines = []
    lines.append(f"Database: {metadata.name}")

    lines.append("")

    for table in metadata.tables:
        lines.append(f"Table: {table.name}")

        lines.append("  Columns:")
        for col in table.columns:
            col_info = f"    - {col.name} ({col.type})"

            lines.append(col_info)

            # Add value examples
            if col.examples:
                examples_str = ", ".join(str(v) for v in col.examples[:5])
                lines.append(f"      Value Examples: [{examples_str}]")

            # Add enum values
            if col.enums:
                enum_values = col.get_enum_values()[:10]
                enum_str = ", ".join(str(v) for v in enum_values)
                lines.append(f"      Enum Values: [{enum_str}]")
        lines.append("")

    profile = "\n".join(lines)
    max_chars = 28000
    if len(profile) > max_chars:
        profile = profile[:max_chars] + "\n... [schema truncated]\n"
    return profile


def get_database_schema_profile_from_dict(database_schema: Dict[str, Any]) -> str:
    """
    Generate a text profile of the database schema from a dictionary format.

    Args:
        database_schema: Dictionary containing schema information

    Returns:
        Formatted string representation of the schema
    """
    lines = []

    if "name" in database_schema:
        lines.append(f"Database: {database_schema['name']}")

    tables = database_schema.get("tables", {})

    for table_name, table_info in tables.items():
        lines.append(f"\nTable: {table_name}")

        if isinstance(table_info, dict):
            columns = table_info.get("columns", {})

            lines.append("  Columns:")
            for col_name, col_info in columns.items():
                if isinstance(col_info, dict):
                    col_type = col_info.get("column_type", "UNKNOWN")
                    col_str = f"    - {col_name} ({col_type})"

                    if col_info.get("is_primary_key"):
                        col_str += " [PRIMARY KEY]"
                    if col_info.get("is_foreign_key"):
                        col_str += " [FOREIGN KEY]"

                    lines.append(col_str)

                    if col_info.get("column_description"):
                        lines.append(f"      Description: {col_info['column_description']}")

                    value_examples = col_info.get("value_examples", [])
                    if value_examples:
                        examples_str = ", ".join(str(v) for v in value_examples[:5])
                        lines.append(f"      Value Examples: [{examples_str}]")

    return "\n".join(lines)


def map_lower_table_name_to_original(
        table_name: str,
        metadata: DatabaseMetadata
) -> Optional[str]:
    """
    Map a lowercase table name to its original case in the schema.

    Args:
        table_name: The lowercase table name to map
        metadata: DatabaseMetadata object

    Returns:
        The original table name or None if not found
    """
    table_name_lower = table_name.lower()
    for table in metadata.tables:
        if table.name.lower() == table_name_lower:
            return table.name
    return None


def map_lower_table_name_to_original_from_dict(
        table_name: str,
        database_schema: Dict[str, Any]
) -> Optional[str]:
    """
    Map a lowercase table name to its original case in the schema dict.
    """
    table_name_lower = table_name.lower()
    tables = database_schema.get("tables", {})
    for orig_name in tables.keys():
        if orig_name.lower() == table_name_lower:
            return orig_name
    return None


def map_lower_column_name_to_original(
        table_name: str,
        column_name: str,
        metadata: DatabaseMetadata
) -> Optional[str]:
    """
    Map a lowercase column name to its original case in the schema.

    Args:
        table_name: The table name containing the column
        column_name: The lowercase column name to map
        metadata: DatabaseMetadata object

    Returns:
        The original column name or None if not found
    """
    column_name_lower = column_name.lower()
    table = metadata.get_table(table_name)
    if table is None:
        return None

    for col in table.columns:
        if col.name.lower() == column_name_lower:
            return col.name
    return None


def map_lower_column_name_to_original_from_dict(
        table_name: str,
        column_name: str,
        database_schema: Dict[str, Any]
) -> Optional[str]:
    """
    Map a lowercase column name to its original case in the schema dict.
    """
    column_name_lower = column_name.lower()
    tables = database_schema.get("tables", {})

    # Find the table (case-insensitive)
    table_info = None
    for orig_name, info in tables.items():
        if orig_name.lower() == table_name.lower():
            table_info = info
            break

    if table_info is None:
        return None

    columns = table_info.get("columns", {})
    for orig_name in columns.keys():
        if orig_name.lower() == column_name_lower:
            return orig_name
    return None


def filter_used_database_schema(
        metadata: DatabaseMetadata,
        linked_tables_and_columns: Dict[str, List[str]]
) -> DatabaseMetadata:
    """
    Filter the database schema to only include linked tables and columns.

    Args:
        metadata: Original DatabaseMetadata object
        linked_tables_and_columns: Dict mapping table names to list of column names

    Returns:
        Filtered DatabaseMetadata object
    """
    from copy import deepcopy

    filtered_metadata = deepcopy(metadata)
    filtered_tables = []

    for table_name, column_names in linked_tables_and_columns.items():
        table = metadata.get_table(table_name)
        if table is None:
            continue

        filtered_table = deepcopy(table)
        column_names_set = set(col.lower() for col in column_names)

        # Filter columns
        filtered_columns = []
        for col in table.columns:
            if col.name.lower() in column_names_set or col.is_primary or col.is_foreign:
                filtered_columns.append(deepcopy(col))

        filtered_table.columns = filtered_columns
        filtered_tables.append(filtered_table)

    filtered_metadata.tables = filtered_tables
    return filtered_metadata


def filter_used_database_schema_dict(
        database_schema: Dict[str, Any],
        linked_tables_and_columns: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Filter the database schema dict to only include linked tables and columns.
    """
    from copy import deepcopy

    filtered_schema = deepcopy(database_schema)
    filtered_tables = {}

    original_tables = database_schema.get("tables", {})

    for table_name, column_names in linked_tables_and_columns.items():
        # Find the original table (case-insensitive match)
        orig_table_name = None
        orig_table_info = None
        for name, info in original_tables.items():
            if name.lower() == table_name.lower():
                orig_table_name = name
                orig_table_info = info
                break

        if orig_table_info is None:
            continue

        filtered_table = deepcopy(orig_table_info)
        column_names_set = set(col.lower() for col in column_names)

        # Filter columns
        if "columns" in filtered_table:
            filtered_columns = {}
            for col_name, col_info in orig_table_info.get("columns", {}).items():
                if (col_name.lower() in column_names_set or
                        col_info.get("is_primary_key") or
                        col_info.get("is_foreign_key")):
                    filtered_columns[col_name] = deepcopy(col_info)
            filtered_table["columns"] = filtered_columns

        filtered_tables[orig_table_name] = filtered_table

    filtered_schema["tables"] = filtered_tables
    return filtered_schema


def merge_schema_linking_results(
        results: List[Optional[Dict[str, List[str]]]]
) -> Dict[str, List[str]]:
    """
    Merge multiple schema linking results into one.

    Args:
        results: List of schema linking results. None values are skipped.

    Returns:
        Merged result dictionary
    """
    merged_result: Dict[str, Set[str]] = {}

    for result in results:
        if result is None:
            continue
        for table_name, columns in result.items():
            if table_name not in merged_result:
                merged_result[table_name] = set()
            merged_result[table_name].update(columns)

    return {table_name: list(columns) for table_name, columns in merged_result.items()}


def extract_tables_and_columns_from_sql(
        sql: str,
        metadata: DatabaseMetadata
) -> Dict[str, List[str]]:
    """
    Extract table and column names mentioned in a SQL query.

    Args:
        sql: SQL query string
        metadata: DatabaseMetadata object

    Returns:
        Dict mapping table names to list of column names found in the SQL
    """
    sql_lower = sql.lower()

    # Get all table and column names
    all_table_names = [table.name for table in metadata.tables]
    all_column_names = []
    for table in metadata.tables:
        all_column_names.extend([col.name for col in table.columns])

    all_table_names = list(set(all_table_names))
    all_column_names = list(set(all_column_names))

    # Find mentioned tables and columns
    mentioned_tables = [
        name for name in all_table_names
        if name.lower() in sql_lower
    ]
    mentioned_columns = [
        name for name in all_column_names
        if name.lower() in sql_lower
    ]

    # Build result
    result: Dict[str, List[str]] = {}
    for table_name in mentioned_tables:
        orig_table_name = map_lower_table_name_to_original(table_name.lower(), metadata)
        if orig_table_name is None:
            continue

        result[orig_table_name] = []
        for col_name in mentioned_columns:
            orig_col_name = map_lower_column_name_to_original(orig_table_name, col_name.lower(), metadata)
            if orig_col_name is not None:
                result[orig_table_name].append(orig_col_name)

    return result


def extract_tables_and_columns_from_sql_dict(
        sql: str,
        database_schema: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Extract table and column names mentioned in a SQL query from schema dict.
    """
    sql_lower = sql.lower()
    tables = database_schema.get("tables", {})

    all_table_names = list(tables.keys())
    all_column_names = []
    for table_info in tables.values():
        if isinstance(table_info, dict) and "columns" in table_info:
            all_column_names.extend(list(table_info["columns"].keys()))

    all_table_names = list(set(all_table_names))
    all_column_names = list(set(all_column_names))

    mentioned_tables = [
        name for name in all_table_names
        if name.lower() in sql_lower
    ]
    mentioned_columns = [
        name for name in all_column_names
        if name.lower() in sql_lower
    ]

    result: Dict[str, List[str]] = {}
    for table_name in mentioned_tables:
        orig_table_name = map_lower_table_name_to_original_from_dict(table_name.lower(), database_schema)
        if orig_table_name is None:
            continue

        result[orig_table_name] = []
        for col_name in mentioned_columns:
            orig_col_name = map_lower_column_name_to_original_from_dict(orig_table_name, col_name.lower(), database_schema)
            if orig_col_name is not None:
                result[orig_table_name].append(orig_col_name)

    return result


if __name__ == '__main__':

    from deepeye.datasource.extractors.sqlite_extractor import SQLiteExtractor

    sqlite_extractor = SQLiteExtractor()

    sqlite_extractor.connect(database_path='/Users/tiantiantian/Code/bird-2023-dataset/dev_20240627/dev_databases/card_games/card_games.sqlite')

    metadata = sqlite_extractor.extract()
    result = get_database_schema_profile(metadata=metadata)