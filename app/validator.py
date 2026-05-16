# app/validator.py — SQL safety validation, dialect translation, and plain-English explanation.
# Three public functions: validate_sql, translate_sql, explain_sql.

import re
import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMP, SUPPORTED_DIALECTS

# Single LLM instance shared across all functions in this module
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GOOGLE_API_KEY,
    temperature=GEMINI_TEMP,
)

BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER",
    "CREATE", "REPLACE", "MERGE", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "ATTACH", "DETACH",
]

# Compiled pattern with word boundaries so 'created_at' is NOT matched by 'CREATE'.
BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def strip_markdown(sql: str) -> str:
    """Remove ```sql ... ``` fences that LLMs sometimes wrap around their output."""
    sql = re.sub(r"```[a-zA-Z]*", "", sql)
    sql = sql.replace("```", "")
    return sql.strip()


def validate_sql(sql: str) -> dict[str, Any]:
    """Check a SQL string for safety — must be a SELECT/WITH query with no write or DDL keywords."""
    cleaned = strip_markdown(sql).strip()

    first_word = cleaned.split()[0].upper() if cleaned.split() else ""
    if first_word not in ("SELECT", "WITH"):
        return {
            "safe": False,
            "reason": (
                f"Query must begin with SELECT or WITH. "
                f"Got '{first_word}'. Only read operations are permitted."
            ),
            "cleaned_sql": cleaned,
        }

    match = BLOCKED_PATTERN.search(cleaned)
    if match:
        keyword = match.group(0).upper()
        return {
            "safe": False,
            "reason": (
                f"Blocked keyword detected: '{keyword}'. "
                f"Write operations and DDL statements are not allowed."
            ),
            "cleaned_sql": cleaned,
        }

    return {
        "safe": True,
        "reason": "Query passed all safety checks.",
        "cleaned_sql": cleaned,
    }


TRANSLATION_PROMPT = """\
You are an expert SQL dialect translator. Translate the following SQLite query
to {dialect} SQL. Apply ALL relevant syntax changes:

1. LIMIT/OFFSET:
   - MySQL/PostgreSQL: LIMIT n OFFSET m  (same as SQLite)
   - SQL Server: TOP n  or  OFFSET m ROWS FETCH NEXT n ROWS ONLY
   - Oracle: FETCH FIRST n ROWS ONLY  or  ROWNUM
   - BigQuery: LIMIT n  (same)
   - Snowflake: LIMIT n  (same)

2. Date functions:
   - SQLite:    strftime('%Y', col)
   - MySQL:     DATE_FORMAT(col, '%Y') or YEAR(col)
   - PostgreSQL: EXTRACT(YEAR FROM col) or DATE_TRUNC(...)
   - SQL Server: YEAR(col) or FORMAT(col, 'yyyy')
   - Oracle:    TO_CHAR(col, 'YYYY') or EXTRACT(YEAR FROM col)
   - BigQuery:  EXTRACT(YEAR FROM col) or FORMAT_DATE(...)
   - Snowflake: YEAR(col) or DATE_TRUNC('year', col)

3. Identifier quoting:
   - SQLite/PostgreSQL/BigQuery/Snowflake: "double_quotes"
   - MySQL: `backticks`
   - SQL Server: [square brackets]
   - Oracle: "double_quotes"

4. Auto-increment:
   - SQLite:    INTEGER PRIMARY KEY AUTOINCREMENT
   - MySQL:     INT AUTO_INCREMENT PRIMARY KEY
   - PostgreSQL: SERIAL PRIMARY KEY  or  GENERATED ALWAYS AS IDENTITY
   - SQL Server: INT IDENTITY(1,1) PRIMARY KEY
   - Oracle:    NUMBER GENERATED ALWAYS AS IDENTITY
   - BigQuery:  No native auto-increment (use INT64 + GENERATE_UUID)
   - Snowflake: INT AUTOINCREMENT PRIMARY KEY

Original SQLite query:
{sql}

Respond in this EXACT JSON format (no markdown, no extra text):
{{
  "translated_sql": "<translated query here>",
  "dialect": "{dialect}",
  "notes": "<brief bullet-point list of changes made, or 'No changes needed'>"
}}
"""


def translate_sql(sql: str, dialect: str) -> dict[str, Any]:
    """Translate a SQLite SELECT query to the target SQL dialect using Gemini."""
    if dialect not in SUPPORTED_DIALECTS:
        return {
            "translated_sql": sql,
            "dialect": dialect,
            "notes": f"Unsupported dialect '{dialect}'. Supported: {SUPPORTED_DIALECTS}",
        }

    if dialect.lower() == "sqlite":
        return {
            "translated_sql": sql,
            "dialect": "SQLite",
            "notes": "Source is already SQLite — no translation needed.",
        }

    prompt = TRANSLATION_PROMPT.format(sql=sql.strip(), dialect=dialect)

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        raw = re.sub(r"```[a-zA-Z]*", "", raw).replace("```", "").strip()
        result = json.loads(raw)
        return result
    except Exception as exc:
        return {
            "translated_sql": sql,
            "dialect": dialect,
            "notes": f"Translation failed: {exc}",
        }


EXPLAIN_PROMPT = """\
Explain what the following SQL query does in plain English.
Use 2-3 sentences. Write for a non-technical business user.
Avoid technical jargon like JOIN, GROUP BY, etc.
Focus on WHAT data it retrieves and WHY someone would want it.

SQL:
{sql}

Plain-English explanation:"""


def explain_sql(sql: str) -> str:
    """Return a 2-3 sentence plain-English explanation of what the SQL query does."""
    try:
        prompt = EXPLAIN_PROMPT.format(sql=sql.strip())
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as exc:
        return f"Could not generate explanation: {exc}"
