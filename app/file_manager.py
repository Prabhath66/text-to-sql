# app/file_manager.py — Handle CSV / Excel / JSON uploads and register them as SQLite tables.
# Sanitises names, maps dtypes, auto-detects JOIN relationships, and returns schema info for Gemini.

import io
import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import DB_PATH, SAMPLE_ROWS, SUPPORTED_EXTENSIONS


def sanitise_table_name(raw: str) -> str:
    """Convert a raw filename to a valid SQLite table name (lowercase, alphanumeric + underscores, max 60 chars)."""
    stem = Path(raw).stem
    clean = re.sub(r"[^a-zA-Z0-9]", "_", stem)
    clean = re.sub(r"_+", "_", clean).strip("_")
    clean = clean.lower()
    if clean and clean[0].isdigit():
        clean = "t_" + clean
    return clean[:60] or "uploaded_table"


def sanitise_column(raw: str) -> str:
    """Convert a raw column header to a valid SQL column name (lowercase, alphanumeric + underscores)."""
    clean = re.sub(r"[^a-zA-Z0-9]", "_", str(raw))
    clean = re.sub(r"_+", "_", clean).strip("_").lower()
    if clean and clean[0].isdigit():
        clean = "col_" + clean
    return clean or "column"


def dtype_to_sqlite(dtype) -> str:
    """Map a pandas dtype to a SQLite type affinity string (INTEGER, REAL, or TEXT)."""
    name = str(dtype)
    if "int" in name:
        return "INTEGER"
    if "float" in name:
        return "REAL"
    if "bool" in name:
        return "INTEGER"
    if "datetime" in name:
        return "TEXT"
    return "TEXT"


def create_table_from_df(conn: sqlite3.Connection, table_name: str, df: pd.DataFrame, source_file: str = "") -> None:
    """Drop and recreate a SQLite table from a DataFrame, then record it in _querymind_meta as 'uploaded'."""
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")

    col_defs = ", ".join(
        f"[{col}] {dtype_to_sqlite(df[col].dtype)}"
        for col in df.columns
    )
    cursor.execute(f"CREATE TABLE [{table_name}] ({col_defs})")

    placeholders = ", ".join("?" * len(df.columns))
    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]
    cursor.executemany(f"INSERT INTO [{table_name}] VALUES ({placeholders})", rows)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _querymind_meta (
            table_name   TEXT PRIMARY KEY,
            source       TEXT NOT NULL DEFAULT 'base',
            source_file  TEXT,
            uploaded_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    cursor.execute(
        "INSERT OR REPLACE INTO _querymind_meta (table_name, source, source_file) VALUES (?, 'uploaded', ?)",
        (table_name, source_file),
    )
    conn.commit()


def read_file(filename: str, content: bytes) -> pd.DataFrame:
    """Parse raw file bytes into a DataFrame based on the file extension (csv, xlsx, xls, json)."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {SUPPORTED_EXTENSIONS}")

    buf = io.BytesIO(content)
    if suffix == ".csv":
        df = pd.read_csv(buf)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(buf)
    elif suffix == ".json":
        df = pd.read_json(buf)
    else:
        raise ValueError(f"Unhandled suffix: {suffix}")

    return df


def detect_relationships(table_schemas: dict[str, list[str]]) -> list[dict]:
    """Scan column names ending in '_id' or '_key' across tables and return likely FK relationships."""
    col_to_tables: dict[str, list[str]] = {}
    for tbl, cols in table_schemas.items():
        for col in cols:
            if col.endswith("_id") or col.endswith("_key"):
                col_to_tables.setdefault(col, []).append(tbl)

    relationships = []
    seen = set()
    for col, tables in col_to_tables.items():
        if len(tables) < 2:
            continue
        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                t1, t2 = sorted([tables[i], tables[j]])
                key = (t1, t2, col)
                if key in seen:
                    continue
                seen.add(key)
                relationships.append({
                    "table1": t1,
                    "table2": t2,
                    "on_column": col,
                    "join_hint": f"JOIN {t2} ON {t1}.{col} = {t2}.{col}",
                })

    return relationships


def build_join_hints_string(relationships: list[dict]) -> str:
    """Build a compact join-hints string to inject into Gemini's system prompt."""
    if not relationships:
        return ""
    lines = ["Detected JOIN relationships:"]
    for rel in relationships:
        lines.append(
            f"  - {rel['table1']} ↔ {rel['table2']} via {rel['on_column']}"
            f"  (hint: {rel['join_hint']})"
        )
    return "\n".join(lines)


def process_files(files: list[dict[str, Any]]) -> dict:
    """Read uploaded files, create SQLite tables, detect relationships, and return a schema summary dict."""
    conn = sqlite3.connect(DB_PATH)
    table_schemas: dict[str, list[str]] = {}
    result_tables: dict[str, dict] = {}
    errors: list[str] = []

    for file_info in files:
        filename = file_info["filename"]
        content  = file_info["content"]
        try:
            df = read_file(filename, content)

            df.columns = [sanitise_column(c) for c in df.columns]

            seen_cols: dict[str, int] = {}
            new_cols = []
            for col in df.columns:
                if col in seen_cols:
                    seen_cols[col] += 1
                    new_cols.append(f"{col}_{seen_cols[col]}")
                else:
                    seen_cols[col] = 0
                    new_cols.append(col)
            df.columns = new_cols

            table_name = sanitise_table_name(filename)
            create_table_from_df(conn, table_name, df, source_file=filename)

            col_info = [
                {"name": col, "type": dtype_to_sqlite(df[col].dtype)}
                for col in df.columns
            ]
            sample = df.head(SAMPLE_ROWS).fillna("").to_dict(orient="records")

            result_tables[table_name] = {
                "columns":     col_info,
                "row_count":   len(df),
                "sample_rows": sample,
                "source_file": filename,
            }
            table_schemas[table_name] = list(df.columns)

        except Exception as exc:
            errors.append(f"{filename}: {exc}")

    conn.close()

    relationships = detect_relationships(table_schemas)
    join_hints = build_join_hints_string(relationships)

    return {
        "tables":        result_tables,
        "relationships": relationships,
        "join_hints":    join_hints,
        "errors":        errors,
    }


def delete_uploaded_table(table_name: str) -> dict:
    """Drop an uploaded table from SQLite and remove its metadata entry. Raises ValueError for base tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT source FROM _querymind_meta WHERE table_name = ?", (table_name,)
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"Table '{table_name}' not found in metadata.")
    if row[0] != "uploaded":
        conn.close()
        raise ValueError(f"Table '{table_name}' is a base table and cannot be deleted.")

    cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
    cursor.execute("DELETE FROM _querymind_meta WHERE table_name = ?", (table_name,))
    conn.commit()
    conn.close()
    return {"deleted": table_name}


def get_schema_for_gemini(schema: dict) -> str:
    """Build a compact schema string for injection into Gemini's prompt, mirroring LangChain's table info format."""
    if not schema or not schema.get("tables"):
        return "No uploaded schema available."

    lines = []
    for tbl, info in schema["tables"].items():
        col_str = ", ".join(
            f"{c['name']} ({c['type']})" for c in info["columns"]
        )
        lines.append(f"Table: {tbl}  |  Columns: {col_str}  |  Rows: {info['row_count']}")

    if schema.get("join_hints"):
        lines.append("")
        lines.append(schema["join_hints"])

    return "\n".join(lines)
