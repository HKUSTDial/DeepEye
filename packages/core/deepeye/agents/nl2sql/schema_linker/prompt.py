DIRECT_LINKING_PROMPT = """
# Task:
You are an expert and very smart data analyst.
Your task is to examine the provided database schema, understand the posed question, and use the hint to **pinpoint the specific tables and columns** that are essential for crafting a SQL query to answer the question.

# Instructions:
The given schema provides a detailed definition of the database's structure, including tables, their columns, primary keys, foreign keys, and any relevant details about relationships or constraints.
The given hint aims to direct your focus towards the specific elements of the database schema that are crucial for answering the question effectively.

For each of the selected tables and columns, explain why exactly it is necessary for answering the question. Your reasoning should be concise and clear, demonstrating a logical connection between the selected items and the question asked.

[IMPORTANT!]
1. For key phrases mentioned in the question, we have provided the most similar values within the columns (TEXT-TYPE columns) denoted by "Value Examples". **This is a critical hint to identify the tables/columns that will be used in the SQL query.**
2. If you are not sure whether a column is needed or not, it's better to include it in your selection. **It's safer to select more columns than to miss necessary ones.**
3. If a column contains values that are related to the current question (check the "Value Examples"), you MUST include this column in your selection.
4. If there are multiple tables to JOIN, you MUST ensure that the joined tables have EXPLICIT FOREIGN KEYS between them. For example, "TableA -> TableB, TableC -> TableB", directly join TableA and TableC is NOT ALLOWED, you must join TableA and TableB, and then join TableB and TableC.

# Output Format:
Please respond with XML code structured as follows:
<reasoning>
    Your reasoning for selecting the tables and columns, be concise and clear.
</reasoning>
<result>
    <table table_name="table_name">
        <column column_name="column_name" />
        ...
    </table>
    <table table_name="another_table_name">
        <column column_name="another_column_name" />
        ...
    </table>
    ...
</result>

# Input:
## Database Schema:
{DATABASE_SCHEMA}

## Question:
{QUESTION}

Only output the XML code following the output format as your response.

# Output:
"""


ICL_SQL_GENERATION_PROMPT = """
# Task:
You are an experienced database expert specializing in cross-domain SQL generation.
You will be given a target database schema, a question, and several similar examples from different databases (cross-domain few-shot examples).
Your task is to generate a SQL query for the target question by learning from the provided examples.

# Instructions:
1. **Analyze the Examples**: Study the provided few-shot examples carefully. Each example contains:
   - A question from a different database domain
   - The corresponding SQL query that answers the question

2. **Identify Patterns**: Look for common SQL patterns, query structures, and logical approaches used in the examples:
   - How to handle aggregations (MAX, MIN, COUNT, SUM, AVG)
   - How to structure JOINs and subqueries
   - How to apply WHERE conditions and filtering
   - How to handle string matching and comparisons
   - How to use ORDER BY and LIMIT clauses

3. **Apply to Target Question**: Use the learned patterns to generate SQL for the target question:
   - Map the target question's requirements to similar patterns from examples
   - Adapt the SQL structure to work with the target database schema
   - Ensure the query logic matches the question's intent

# Important Rules:
1. **Schema Adaptation**: The examples use different database schemas, so you must adapt the patterns to work with the target schema
2. **Column Mapping**: Pay attention to how similar concepts are represented in different schemas
3. **Query Structure**: Follow the structural patterns from examples (JOIN types, subquery usage, etc.)
4. **SQLite Compatibility**: Use only SQLite-compatible functions and syntax
5. **Exact Column Names**: Use the exact column and table names from the target schema
6. **Logical Consistency**: Ensure the generated query logically answers the target question
7. **Foreign Key Constraints**: If there are multiple tables to JOIN, you MUST ensure that the joined tables have EXPLICIT FOREIGN KEYS between them. For example, "TableA -> TableB, TableC -> TableB", directly join TableA and TableC is NOT ALLOWED, you must join TableA and TableB, and then join TableB and TableC.

# Output Format:
Please respond with XML code structured as follows:
<reasoning>
    Your analysis of the examples and reasoning for the SQL generation.
</reasoning>
<result>
    The final SQL query that answers the target question and can be executed on the target SQLite database, ensure there is not any SQLite comment and not any other explanation text in the SQL query.
    The SQL query must not include XML-specific characters (e.g., `&lt;`, `&gt;`, `&amp;`); only SQL-valid characters are allowed.
</result>

# Input:
## Few-Shot Examples:
{FEW_SHOT_EXAMPLES}

## Target Database Schema:
{DATABASE_SCHEMA}

## Target Question:
{QUESTION} {HINT}

# Output:
"""