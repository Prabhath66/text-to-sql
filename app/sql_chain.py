# app/sql_chain.py — LangChain SQL chain with Gemini and a two-step generate-then-execute flow.
# ask() generates SQL, validates it, and optionally executes it and returns a natural-language answer.

from __future__ import annotations

import re
from typing import Any

from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.messages import HumanMessage

from app.config import DB_URL, GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_TEMP, MAX_ROWS_RETURNED
from app.validator import validate_sql, explain_sql
from app.file_manager import get_schema_for_gemini

# LangChain LLM wrapper used for both SQL generation and answer generation
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GOOGLE_API_KEY,
    temperature=GEMINI_TEMP,
)

ANSWER_PROMPT = """\
A user asked: "{question}"

The SQL query returned this data (first {max_rows} rows shown):
{rows}

Write a concise, clear, plain-English answer to the user's question based
on this data. 1-3 sentences. Be specific — include numbers and names from
the data. Do NOT mention SQL, tables, or technical terms.
"""


def detect_chart_type(question: str, columns: list[str]) -> str:
    """Pick a chart type from the question and column names using keyword heuristics — no LLM call needed."""
    q_lower = question.lower()
    col_lower = " ".join(columns).lower()

    time_keywords = {"year", "month", "date", "day", "week", "quarter", "time", "period"}
    if any(kw in col_lower for kw in time_keywords) or any(kw in q_lower for kw in time_keywords):
        return "line"

    pie_keywords = {"percent", "percentage", "proportion", "share", "distribution", "breakdown"}
    if any(kw in q_lower for kw in pie_keywords):
        return "pie"

    scatter_keywords = {" vs ", "versus", "correlation", "relationship", "compare"}
    if any(kw in q_lower for kw in scatter_keywords):
        return "scatter"

    return "bar"


def generate_answer(question: str, rows: list[dict], columns: list[str]) -> str:
    """Call Gemini to produce a plain-English summary of the query results."""
    try:
        row_text = "\n".join(str(r) for r in rows[:10])
        prompt = ANSWER_PROMPT.format(
            question=question,
            max_rows=len(rows),
            rows=row_text,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as exc:
        return f"Query executed successfully. {len(rows)} row(s) returned. (Answer generation failed: {exc})"


def build_prefix(uploaded_schema: dict | None) -> str:
    """Build extra schema context to prepend to the SQL-generation prompt for JOIN-aware generation."""
    parts = []
    if uploaded_schema:
        extra = get_schema_for_gemini(uploaded_schema)
        if extra:
            parts.append("ADDITIONAL UPLOADED TABLES:\n" + extra)
    if parts:
        return "\n\n".join(parts) + "\n\n"
    return ""


def parse_result(raw: str, sql: str, db: SQLDatabase) -> tuple[list[dict], list[str]]:
    """Re-execute the SQL via SQLAlchemy to get properly typed rows and column names."""
    import sqlalchemy as sa
    engine = sa.create_engine(str(db._engine.url))
    with engine.connect() as conn:
        result = conn.execute(sa.text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows, columns


def ask(
    question: str,
    execute: bool = False,
    uploaded_schema: dict | None = None,
) -> dict[str, Any]:
    """Convert a natural-language question to SQL, validate it, and optionally execute it.

    Returns a blocked result, a pending-review result, or a full executed result with rows and chart type.
    """
    try:
        db = SQLDatabase.from_uri(DB_URL)

        prefix = build_prefix(uploaded_schema)
        chain  = create_sql_query_chain(llm, db)

        augmented_question = prefix + question if prefix else question
        raw_sql: str = chain.invoke({"question": augmented_question})

        raw_sql = re.sub(r"(?i)^sql\s*query\s*:\s*", "", raw_sql).strip()
        raw_sql = re.sub(r"(?i)^sqlquery\s*:\s*", "", raw_sql).strip()

        validation = validate_sql(raw_sql)
        if not validation["safe"]:
            return {
                "success": False,
                "blocked": True,
                "reason":  validation["reason"],
                "sql":     validation["cleaned_sql"],
            }

        clean_sql = validation["cleaned_sql"]
        sql_explanation = explain_sql(clean_sql)

        if not execute:
            return {
                "success":         True,
                "pending_review":  True,
                "sql":             clean_sql,
                "sql_explanation": sql_explanation,
            }

        exec_tool = QuerySQLDataBaseTool(db=db)
        raw_result: str = exec_tool.run(clean_sql)

        rows, columns = parse_result(raw_result, clean_sql, db)
        rows = rows[:MAX_ROWS_RETURNED]

        answer     = generate_answer(question, rows, columns)
        chart_type = detect_chart_type(question, columns)

        return {
            "success":         True,
            "pending_review":  False,
            "sql":             clean_sql,
            "sql_explanation": sql_explanation,
            "answer":          answer,
            "rows":            rows,
            "columns":         columns,
            "chart_type":      chart_type,
            "row_count":       len(rows),
        }

    except Exception as exc:
        return {
            "success": False,
            "blocked": False,
            "reason":  str(exc),
            "sql":     "",
        }
