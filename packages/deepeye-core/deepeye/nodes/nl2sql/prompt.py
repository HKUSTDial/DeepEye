"""NL2SQL 节点的 Prompt 模板

该模块定义了 NL2SQL 节点使用的所有 Prompt 模板。
使用结构化的格式，输出使用 XML 标签便于解析。
"""

# ============================================================================
# 初始 SQL 生成提示词模板
# ============================================================================

INITIAL_SQL_GENERATION_PROMPT = """# Task Description
You are an expert SQL developer. Generate a SQL query based on the user's natural language question and database schema.

# Database Information

## Database Dialect
{dialect}

## Schema Information
{schema_info}

## Sample Data (First {sample_size} rows)
{sample_data}

## Statistics
{statistics_info}

# Important Notes

1. **SQL Dialect**: Generate SQL compatible with {dialect}
2. **Table and Column Names**: Use EXACT names from the schema (case-sensitive in some databases)
3. **Data Types**: Consider column types when writing conditions
4. **Sample Values**: Use sample data to understand value formats and typical data
5. **Query Optimization**: Write efficient queries with proper indexes/joins
6. **Edge Cases**: Handle NULL values, empty results, and data type mismatches

# Common Pitfalls to Avoid

- ❌ Using column names that don't exist
- ❌ Incorrect JOIN conditions
- ❌ Type mismatches in WHERE clauses
- ❌ Forgetting GROUP BY when using aggregations
- ❌ Case sensitivity issues
- ❌ Using dialect-specific syntax incorrectly

# Output Format

You MUST respond in the following structured format:

<think>
[Your analysis and reasoning]
- What is the user asking for?
- Which tables/columns are needed?
- What JOINs are required?
- What aggregations/filters/sorts are needed?
- Any potential issues or edge cases?
</think>

<sql>
[Your SQL query here - ONLY the query, no explanation]
</sql>

<explanation>
[Brief explanation of what the SQL does in plain English]
- What data it retrieves
- How it's filtered/aggregated
- What it returns
</explanation>

# User Question
{user_query}

# Now Generate SQL
Please generate the SQL query for the above question following the exact output format.
"""

# ============================================================================
# SQL 修复提示词模板
# ============================================================================

SQL_FIX_PROMPT = """# Task Description
The previous SQL query execution failed. Analyze the error and generate a corrected SQL query.

# Database Information

## Database Dialect
{dialect}

## Schema Information
{schema_info}

## Sample Data
{sample_data}

# Previous Attempt

## User Question
{user_query}

## Previous SQL (FAILED)
```sql
{previous_sql}
```

## Error Message
```
{error_message}
```

# Instructions

1. **Analyze the error**: Carefully read the error message and identify the root cause
2. **Check schema**: Verify table names, column names, and data types
3. **Fix the issue**: Generate corrected SQL that resolves the error
4. **Verify logic**: Ensure the fixed SQL still answers the user's question
5. **Test mentally**: Walk through the query to ensure it makes sense

# Common Error Types

1. **Column Not Found**: Check exact column name spelling and case
2. **Table Not Found**: Verify table names from schema
3. **Syntax Error**: Check dialect-specific syntax
4. **Type Mismatch**: Ensure comparisons use compatible types
5. **Aggregation Error**: Check GROUP BY clauses
6. **JOIN Error**: Verify JOIN conditions and table references

# Output Format

You MUST respond in the following structured format:

<think>
[Your error analysis and solution approach]
- What is the error type and message?
- What is the root cause of this error?
- What specific issue needs to be fixed?
- What is the corrected approach?
- How does the fix address the error?
</think>

<sql>
[Your CORRECTED SQL query here - ONLY the query, no explanation]
</sql>

<explanation>
[Brief explanation of what the SQL does in plain English]
- What data it retrieves
- How it's filtered/aggregated
- What it returns
</explanation>

# Now Generate Fixed SQL
Please generate the corrected SQL query following the exact output format above.
"""

# ============================================================================
# 辅助函数：格式化 Schema 信息
# ============================================================================

def format_schema_info(schema: dict) -> str:
    """格式化 schema 信息为可读文本
    
    Args:
        schema: Schema 信息字典（来自 DatabaseConnection.get_schema_info）
    
    Returns:
        格式化的 schema 文本
    
    Example:
        >>> schema = {
        ...     "tables": ["users", "orders"],
        ...     "columns": {
        ...         "users": [
        ...             {"name": "id", "type": "INTEGER", "nullable": False},
        ...             {"name": "name", "type": "VARCHAR(100)", "nullable": True},
        ...         ],
        ...         "orders": [
        ...             {"name": "id", "type": "INTEGER", "nullable": False},
        ...             {"name": "user_id", "type": "INTEGER", "nullable": False},
        ...         ]
        ...     },
        ...     "foreign_keys": {...},
        ...     "primary_keys": {...}
        ... }
        >>> print(format_schema_info(schema))
    """
    lines = []
    
    # 表列表
    lines.append("### Tables")
    for table in schema.get("tables", []):
        lines.append(f"- {table}")
    lines.append("")
    
    # 每个表的详细信息
    for table in schema.get("tables", []):
        lines.append(f"### Table: {table}")
        lines.append("")
        
        # 列信息
        lines.append("**Columns:**")
        columns = schema.get("columns", {}).get(table, [])
        for col in columns:
            nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
            auto_inc = " AUTO_INCREMENT" if col.get("autoincrement", False) else ""
            default = f" DEFAULT {col.get('default')}" if col.get('default') else ""
            lines.append(f"- `{col['name']}`: {col['type']} {nullable}{auto_inc}{default}")
        lines.append("")
        
        # 主键
        primary_keys = schema.get("primary_keys", {}).get(table, [])
        if primary_keys:
            lines.append(f"**Primary Key:** {', '.join(primary_keys)}")
            lines.append("")
        
        # 外键
        foreign_keys = schema.get("foreign_keys", {}).get(table, [])
        if foreign_keys:
            lines.append("**Foreign Keys:**")
            for fk in foreign_keys:
                constrained = ', '.join(fk['constrained_columns'])
                referred_table = fk['referred_table']
                referred = ', '.join(fk['referred_columns'])
                lines.append(f"- {constrained} → {referred_table}({referred})")
            lines.append("")
        
        # 索引
        indexes = schema.get("indexes", {}).get(table, [])
        if indexes:
            lines.append("**Indexes:**")
            for idx in indexes:
                unique = " (UNIQUE)" if idx.get("unique", False) else ""
                columns = ', '.join(idx['columns'])
                lines.append(f"- {idx['name']}: {columns}{unique}")
            lines.append("")
    
    return '\n'.join(lines)


def format_sample_data(examples: dict, max_values: int = 5) -> str:
    """格式化示例数据为可读文本
    
    Args:
        examples: 示例数据字典（来自 DatabaseConnection.get_sample_data）
        max_values: 每列显示的最大值数量
    
    Returns:
        格式化的示例数据文本
    """
    lines = []
    
    for table, columns in examples.items():
        if isinstance(columns, dict) and "error" in columns:
            lines.append(f"### Table: {table}")
            lines.append(f"Error: {columns['error']}")
            lines.append("")
            continue
        
        lines.append(f"### Table: {table}")
        lines.append("")
        
        for col_name, values in columns.items():
            # 限制显示的值数量
            display_values = values[:max_values]
            values_str = ', '.join([repr(v) for v in display_values])
            
            if len(values) > max_values:
                values_str += f", ... ({len(values)} total)"
            
            lines.append(f"- `{col_name}`: {values_str}")
        
        lines.append("")
    
    return '\n'.join(lines)


def format_statistics_info(statistics: dict) -> str:
    """格式化统计信息为可读文本
    
    Args:
        statistics: 统计信息字典（来自 DatabaseConnection.get_table_statistics）
    
    Returns:
        格式化的统计信息文本
    """
    lines = []
    
    for table, stats in statistics.items():
        if isinstance(stats, dict) and "error" in stats:
            lines.append(f"### Table: {table}")
            lines.append(f"Error: {stats['error']}")
            lines.append("")
            continue
        
        lines.append(f"### Table: {table}")
        lines.append(f"- **Row Count:** {stats.get('row_count', 'N/A'):,}")
        lines.append("")
        
        lines.append("**Column Statistics:**")
        for col_name, col_stats in stats.get("columns", {}).items():
            unique = col_stats.get("unique_count", "N/A")
            nulls = col_stats.get("null_count", "N/A")
            col_type = col_stats.get("type", "")
            
            stat_str = f"- `{col_name}` ({col_type}): {unique:,} unique values, {nulls} nulls"
            
            # 数值列的 min/max
            if "min" in col_stats and "max" in col_stats:
                stat_str += f", range: [{col_stats['min']}, {col_stats['max']}]"
            
            lines.append(stat_str)
        
        lines.append("")
    
    return '\n'.join(lines)


# ============================================================================
# 辅助函数：格式化完整 Prompt
# ============================================================================

def format_initial_prompt(
    user_query: str,
    database_info: dict,
) -> str:
    """格式化初始 SQL 生成的 prompt
    
    Args:
        user_query: 用户的自然语言问题
        database_info: 数据库信息（来自 DatabaseDataSourceNode）
    
    Returns:
        格式化的 prompt 字符串
    """
    schema = database_info.get("schema", {})
    examples = database_info.get("examples", {})
    statistics = database_info.get("statistics", {})
    dialect = database_info.get("dialect", "sql")
    
    # 计算 sample_size
    sample_size = 0
    if examples:
        first_table = next(iter(examples.values()))
        if isinstance(first_table, dict) and not "error" in first_table:
            first_col = next(iter(first_table.values()))
            sample_size = len(first_col)
    
    return INITIAL_SQL_GENERATION_PROMPT.format(
        dialect=dialect,
        schema_info=format_schema_info(schema),
        sample_data=format_sample_data(examples),
        statistics_info=format_statistics_info(statistics),
        sample_size=sample_size,
        user_query=user_query,
    )


def format_fix_prompt(
    user_query: str,
    database_info: dict,
    previous_sql: str,
    error_message: str,
) -> str:
    """格式化 SQL 修复的 prompt
    
    Args:
        user_query: 用户的自然语言问题
        database_info: 数据库信息
        previous_sql: 之前失败的 SQL
        error_message: 错误信息
    
    Returns:
        格式化的 prompt 字符串
    """
    schema = database_info.get("schema", {})
    examples = database_info.get("examples", {})
    dialect = database_info.get("dialect", "sql")
    
    return SQL_FIX_PROMPT.format(
        dialect=dialect,
        schema_info=format_schema_info(schema),
        sample_data=format_sample_data(examples),
        user_query=user_query,
        previous_sql=previous_sql,
        error_message=error_message,
    )


# ============================================================================
# 辅助函数：解析 LLM 响应
# ============================================================================

import re

def extract_response_parts(response: str) -> dict:
    """从 LLM 响应中提取结构化部分
    
    Args:
        response: LLM 的原始响应文本
    
    Returns:
        字典包含: {
            "think": str,
            "sql": str,
            "explanation": str
        }
    
    Raises:
        ValueError: 如果无法提取必要的部分
    """
    result = {}
    
    # 提取 <think>
    think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL | re.IGNORECASE)
    if think_match:
        result["think"] = think_match.group(1).strip()
    else:
        result["think"] = ""
    
    # 提取 <sql>
    sql_match = re.search(r'<sql>(.*?)</sql>', response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        result["sql"] = sql_match.group(1).strip()
    else:
        raise ValueError("无法从 LLM 响应中提取 SQL 语句。响应必须包含 <sql></sql> 标签。")
    
    # 提取 <explanation>
    exp_match = re.search(r'<explanation>(.*?)</explanation>', response, re.DOTALL | re.IGNORECASE)
    if exp_match:
        result["explanation"] = exp_match.group(1).strip()
    else:
        result["explanation"] = ""
    
    return result


