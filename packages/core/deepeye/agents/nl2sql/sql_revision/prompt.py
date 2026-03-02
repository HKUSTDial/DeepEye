"""
SQL Revision Prompts - SQL修正提示词模板
"""

# 执行错误修正提示词
EXECUTION_CHECKER_PROMPT = """
# Task:
Correct a SQL query that failed or returned unexpected results.

# Instructions:
1. Review the database schema to understand the structure
2. Analyze the execution error or unexpected result
3. Correct the query to properly answer the question

# Database Schema:
{DATABASE_SCHEMA}

# Question:
{QUESTION}

# Hint:
{HINT}

# Previous SQL:
{QUERY}

# Execution Result:
{RESULT}

# Output Format:
<reasoning>
    Analysis of the error and fix reasoning
</reasoning>
<r>
    Corrected SQL query (no comments, no explanations)
</r>
"""

# 通用修正提示词
COMMON_CHECKER_PROMPT = """
# Task:
Correct a SQL query based on the provided suggestions.

# Instructions:
1. Review the database schema
2. Understand the modification suggestions
3. Apply ONLY the suggested modifications

# Database Schema:
{DATABASE_SCHEMA}

# Question:
{QUESTION}

# Hint:
{HINT}

# Previous SQL:
{QUERY}

# Modification Suggestions:
{SUGGESTIONS}

[IMPORTANT] Only apply the suggested modifications. Do not make other changes.

# Output Format:
<reasoning>
    Fix reasoning based on suggestions
</reasoning>
<r>
    Corrected SQL query (no comments, no explanations)
</r>
"""
