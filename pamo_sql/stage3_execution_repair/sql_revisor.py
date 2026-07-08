def build_repair_prompt(sql: str, error_msg: str, schema_info: str) -> str:
    return f"""
The following SQL query failed with an execution error.

SQL:
{sql}

SQLite Error:
{error_msg}

Relevant Schema/DDL:
{schema_info}

Please correct the SQL query to fix the error. Make sure:
- Table and column names exactly match the schema.
- SQL syntax is valid SQLite.
- Only return the corrected SQL query.

Corrected SQL:
"""
