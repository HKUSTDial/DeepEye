DC_SQL_GENERATION_PROMPT = """
# Task:
You are an experienced database expert.
You will be given details about the database schema and you need understand the tables and columns.
Then you need to generate a SQL query given the database information, a question and some additional information.

# Instructions:
You will be using a way called "recursive divide-and-conquer approach to SQL query generation from natural language".

Here is a high level description of the steps.
1. **Divide (Decompose Sub-question with Pseudo SQL):** The complex natural language question is recursively broken down into simpler sub-questions. Each sub-question targets a specific piece of information or logic required for the final SQL query. 
2. **Conquer (Real SQL for sub-questions):**  For each sub-question (and the main question initially), a "pseudo-SQL" fragment is formulated. This pseudo-SQL represents the intended SQL logic but might have placeholders for answers to the decomposed sub-questions. 
3. **Combine (Reassemble):** Once all sub-questions are resolved and their corresponding SQL fragments are generated, the process reverses. The SQL fragments are recursively combined by replacing the placeholders in the pseudo-SQL with the actual generated SQL from the lower levels.
4. **Final Output:** This bottom-up assembly culminates in the complete and correct SQL query that answers the original complex question.

# Important Rules:
1. **SELECT Clause:** 
    - Only select columns mentioned in the user's question and with the SAME ORDER as the question requires.
    - Avoid unnecessary columns or values.
2. **Handling NULLs:**
    - If a column may contain NULL values, use `JOIN` or `WHERE <column> IS NOT NULL`.
3. **FROM/JOIN Clauses:**
    - Only include tables essential to answer the question.
4. **Thorough Question Analysis:**
    - Address all conditions mentioned in the question.
5. **DISTINCT Keyword:**
    - Use `SELECT DISTINCT` when the question requires unique values (e.g., IDs, URLs). 
    - Refer to column statistics ("Total count" and "Distinct count") to determine if `DISTINCT` is necessary.
6. **Column Selection:**
    - Carefully analyze column descriptions and hints to choose the correct column when similar columns exist across tables.
7. **String Concatenation:**
    - Never use `|| ' ' ||` or any other method to concatenate strings in the `SELECT` clause.
8. **JOIN Preference:**
    - Prioritize `INNER JOIN` over nested `SELECT` statements.
9. **SQLite Functions Only:**
    - Use only functions available in SQLite.
10. **Date Processing:**
    - Utilize `STRFTIME()` for date manipulation (e.g., `STRFTIME('%Y', SOMETIME)` to extract the year).
11. **Schema Syntax:**
    - When table name or column name contains whitespace, include quotes (`table_name` or `column_name`) around the table name or column name.
12. **Value Examples:**
    - For key phrases mentioned in the question, we have provided the most similar values within the columns (TEXT-TYPE columns) denoted by "Value Examples".
13. **Foreign Key Constraints:**
    - If there are multiple tables to JOIN, you MUST ensure that the joined tables have EXPLICIT FOREIGN KEYS between them. For example, "TableA -> TableB, TableC -> TableB", directly join TableA and TableC is NOT ALLOWED, you must join TableA and TableB, and then join TableB and TableC.

# Output Format:
Please respond with XML code structured as follows.
<reasoning>
    Your detailed reasoning for the SQL query generation, with Recursive Divide-and-Conquer approach.
</reasoning>
<result>
    The final SQL query that answers the question and can be executed by SQLite directly, ensure there is not any SQLite comment and not any other explanation text in the SQL query.
    The SQL query must not include XML-specific characters (e.g., `&lt;`, `&gt;`, `&amp;`); only SQL-valid characters are allowed.
</result>

# Input:
## Database Schema:
{DATABASE_SCHEMA}

## Question:
{QUESTION}

Repeating the question and hint, and generating the SQL with Recursive Divide-and-Conquer approach, and finally try to simplify the SQL query using `INNER JOIN` over nested `SELECT` statements IF POSSIBLE.

# Output:
"""




SKELETON_SQL_GENERATION_PROMPT = """
# Task:
You are an expert SQL developer who uses a systematic approach to generate complex SQL queries.
Your task is to analyze the given question and database schema, then generate a SQL query using a three-step process:
1. **Plan**: Identify the required SQL components and logical structure
2. **Skeleton**: Create a structured SQL skeleton with placeholders
3. **Complete**: Fill in the skeleton with actual table/column names and conditions

# Instructions:

## Step 1: Plan (SQL Components Analysis)
Analyze the question and identify:
- **SELECT clause**: What data needs to be retrieved? (columns, aggregations, calculations)
- **FROM clause**: Which tables are needed?
- **JOIN clauses**: What relationships need to be established?
- **WHERE clause**: What filtering conditions are required?
- **GROUP BY clause**: What grouping is needed for aggregations?
- **HAVING clause**: What post-aggregation filtering is needed?
- **ORDER BY clause**: What sorting is required?
- **LIMIT clause**: Are there any row limits?
- **Subqueries**: Are nested queries needed?
- **Special functions**: Date functions, string functions, mathematical operations

## Step 2: Skeleton (Structured Template)
Create a SQL skeleton with:
- Clear structure showing the logical flow
- Placeholders for table names, column names, and conditions
- Comments explaining the purpose of each section
- Proper indentation and formatting

## Step 3: Complete (Final SQL)
Fill in the skeleton with:
- Exact table and column names from the schema
- Specific values and conditions from the question
- Proper SQLite syntax and functions
- Final validation of the query logic

# Important Rules:
1. **Schema Accuracy**: Use exact table and column names from the provided schema
2. **SQLite Compatibility**: Use only SQLite-compatible functions and syntax
3. **Logical Flow**: Ensure the query logic matches the question requirements
4. **Performance**: Prefer efficient JOIN patterns over nested subqueries when possible
5. **Readability**: Use clear aliases and proper formatting
6. **Completeness**: Address all aspects mentioned in the question and hint
7. **Foreign Key Constraints**: If there are multiple tables to JOIN, you MUST ensure that the joined tables have EXPLICIT FOREIGN KEYS between them. For example, "TableA -> TableB, TableC -> TableB", directly join TableA and TableC is NOT ALLOWED, you must join TableA and TableB, and then join TableB and TableC.


# Output Format:
Please respond with XML code structured as follows:
<reasoning>
    Your comprehensive analysis and planning for the SQL query generation and the SQL skeleton with placeholders.
</reasoning>
<result>
    The final SQL query that answers the target question and can be executed on the target SQLite database, ensure there is not any SQLite comment and not any other explanation text in the SQL query.
    The SQL query must not include XML-specific characters (e.g., `&lt;`, `&gt;`, `&amp;`); only SQL-valid characters are allowed.
</result>

# Input:
## Database Schema:
{DATABASE_SCHEMA}

## Question:
{QUESTION}

# Output:
"""