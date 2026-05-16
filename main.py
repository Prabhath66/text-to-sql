# main.py — FastAPI entry point for the Text-to-SQL Assistant.
# Run with: uvicorn main:app --reload --port 8000

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import SUPPORTED_DIALECTS, DB_URL
from app.sql_chain import ask
from app.file_manager import process_files, get_schema_for_gemini, delete_uploaded_table
from app.validator import validate_sql, translate_sql

app = FastAPI(
    title="Text-to-SQL Assistant",
    description="Natural language to SQL engine powered by LangChain and Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/ui", include_in_schema=False)
def serve_ui():
    """Serve the frontend HTML page with no-cache headers."""
    return FileResponse(
        BASE / "templates" / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    execute:  bool = False


class ValidateRequest(BaseModel):
    sql: str


class TranslateRequest(BaseModel):
    sql:     str
    dialect: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def health() -> dict:
    """Return service status and the active database URL."""
    return {
        "status": "ok",
        "message": "Text-to-SQL Assistant is running.",
        "db_url": DB_URL,
    }


@app.post("/query", summary="Natural language → SQL (+ optional execution)")
def query(req: QueryRequest) -> dict:
    """Generate SQL from a natural-language question and optionally execute it, returning rows and a chart type."""
    import sqlalchemy as sa
    try:
        uploaded_schema: dict[str, Any] = {}
        try:
            engine = sa.create_engine(DB_URL)
            with engine.connect() as conn:
                inspector = sa.inspect(engine)
                rows = conn.execute(sa.text(
                    "SELECT table_name, source_file FROM _querymind_meta WHERE source = 'uploaded'"
                )).fetchall()
                tables = {}
                for tname, src_file in rows:
                    cols = [
                        {"name": c["name"], "type": str(c["type"])}
                        for c in inspector.get_columns(tname)
                    ]
                    count = conn.execute(sa.text(f"SELECT COUNT(*) FROM [{tname}]")).scalar()
                    tables[tname] = {"columns": cols, "row_count": count, "source_file": src_file or ""}
                if tables:
                    uploaded_schema = {"tables": tables, "relationships": [], "join_hints": ""}
        except Exception:
            pass

        result = ask(
            question=req.question,
            execute=req.execute,
            uploaded_schema=uploaded_schema if uploaded_schema else None,
        )
        return result
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@app.post("/upload", summary="Upload CSV / Excel / JSON files → SQLite tables")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    """Accept file uploads, create SQLite tables, and persist metadata so uploaded tables survive restarts."""
    file_payloads = []
    for f in files:
        content = await f.read()
        file_payloads.append({"filename": f.filename, "content": content})

    try:
        result = process_files(file_payloads)
        return {
            "success":        True,
            "tables_created": list(result["tables"].keys()),
            "relationships":  result["relationships"],
            "join_hints":     result["join_hints"],
            "errors":         result["errors"],
        }
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@app.get("/schema", summary="Return current DB schema + available dialects")
def schema() -> dict:
    """Return schema info and metadata for all base and uploaded tables, plus the list of supported dialects."""
    import sqlalchemy as sa
    from langchain_community.utilities import SQLDatabase

    try:
        db = SQLDatabase.from_uri(DB_URL)
        raw_schema = db.get_table_info()
    except Exception as exc:
        raw_schema = f"Error reading base database: {exc}"

    base_tables: dict[str, Any] = {}
    uploaded_tables: dict[str, Any] = {}

    try:
        engine = sa.create_engine(DB_URL)
        with engine.connect() as conn:
            inspector = sa.inspect(engine)

            meta_rows = conn.execute(sa.text(
                "SELECT table_name, source, source_file FROM _querymind_meta"
            )).fetchall()
            meta = {r[0]: {"source": r[1], "source_file": r[2]} for r in meta_rows}

            for tname in inspector.get_table_names():
                if tname == "_querymind_meta":
                    continue

                cols = [
                    {"name": c["name"], "type": str(c["type"])}
                    for c in inspector.get_columns(tname)
                ]

                try:
                    count = conn.execute(sa.text(f"SELECT COUNT(*) FROM [{tname}]")).scalar()
                except Exception:
                    count = 0

                try:
                    res = conn.execute(sa.text(f"SELECT * FROM [{tname}] LIMIT 3"))
                    keys = list(res.keys())
                    sample = [dict(zip(keys, row)) for row in res.fetchall()]
                except Exception:
                    sample = []

                m = meta.get(tname, {})
                table_info = {
                    "columns":     cols,
                    "row_count":   count,
                    "sample_rows": sample,
                    "source_file": m.get("source_file", ""),
                }

                if m.get("source") == "uploaded":
                    uploaded_tables[tname] = table_info
                else:
                    base_tables[tname] = table_info

    except Exception:
        pass

    return {
        "raw_schema":        raw_schema,
        "base_tables":       base_tables,
        "uploaded_tables":   uploaded_tables,
        "available_dialects": SUPPORTED_DIALECTS,
    }


@app.get("/tables", summary="List all tables with column info")
def list_tables() -> dict:
    """Return all tables with column names, types, row counts, and source (base or uploaded)."""
    import sqlalchemy as sa

    tables = {}
    try:
        engine = sa.create_engine(DB_URL)
        with engine.connect() as conn:
            inspector = sa.inspect(engine)

            meta_rows = conn.execute(sa.text(
                "SELECT table_name, source, source_file FROM _querymind_meta"
            )).fetchall()
            meta = {r[0]: {"source": r[1], "source_file": r[2]} for r in meta_rows}

            for tname in inspector.get_table_names():
                if tname == "_querymind_meta":
                    continue
                cols = [
                    {"name": c["name"], "type": str(c["type"])}
                    for c in inspector.get_columns(tname)
                ]
                try:
                    count = conn.execute(sa.text(f"SELECT COUNT(*) FROM [{tname}]")).scalar()
                except Exception:
                    count = 0
                m = meta.get(tname, {})
                tables[tname] = {
                    "columns":     cols,
                    "row_count":   count,
                    "source":      m.get("source", "base"),
                    "source_file": m.get("source_file", ""),
                }
    except Exception:
        pass

    return {"tables": tables}


@app.delete("/tables/{table_name}", summary="Delete an uploaded table")
def delete_table(table_name: str) -> dict:
    """Drop an uploaded table and its metadata entry. Base tables cannot be deleted."""
    try:
        return delete_uploaded_table(table_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@app.get("/sample/{table_name}", summary="Get up to 10 sample rows from a table")
def sample_table(table_name: str) -> dict:
    """Return up to 10 rows from the specified table with column names."""
    import sqlalchemy as sa
    try:
        engine = sa.create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"SELECT * FROM [{table_name}] LIMIT 10"))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"table": table_name, "columns": columns, "rows": rows}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/validate", summary="Check SQL safety (no write ops, no DDL)")
def validate(req: ValidateRequest) -> dict:
    """Run the SQL safety validator and return {safe, reason, cleaned_sql}."""
    try:
        return validate_sql(req.sql)
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@app.post("/translate", summary="Translate SQLite SQL to another dialect")
def translate(req: TranslateRequest) -> dict:
    """Translate a SQLite query to the requested dialect and return {translated_sql, dialect, notes}."""
    try:
        return translate_sql(req.sql, req.dialect)
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
