# QueryMind — Text-to-SQL Assistant

A production-grade Natural Language to SQL engine that lets you query any database using plain English. Ask questions, get SQL, review it, execute it, and see results as charts and tables — all in a clean web UI.

---

## What It Does

You type a question like **"Who are the top 5 customers by revenue?"** and the system:

1. Converts it to SQL using Google Gemini AI
2. Shows you the SQL for review before running it
3. Explains what the SQL does in plain English
4. Executes it against your SQLite database
5. Returns the results as a table + auto-selected chart
6. Gives a plain-English summary of the answer

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | Google Gemini 2.0 Flash via LangChain |
| Backend | FastAPI (Python) |
| Database | SQLite via SQLAlchemy |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Charts | Plotly.js |
| SQL Highlighting | Highlight.js |

---

## Project Structure

```
SQL Project/
├── config.py           # All configuration — API keys, paths, model name
├── database.py         # Creates and seeds the SQLite database
├── main.py             # FastAPI app — all API endpoints
├── sql_chain.py        # Core NL→SQL logic using LangChain + Gemini
├── validator.py        # SQL safety validation, dialect translation, explanation
├── file_manager.py     # CSV/Excel/JSON upload → SQLite table conversion
├── requirements.txt    # Python dependencies
├── .env                # API keys (not committed to git)
├── templates/
│   └── index.html      # Single-page frontend
└── static/
    ├── css/style.css   # All styles
    └── js/app.js       # All frontend JavaScript
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A Google Gemini API key — get one at [aistudio.google.com](https://aistudio.google.com)

### 2. Create virtual environment

```bash
python -m venv sql-env
sql-env\Scripts\activate        # Windows
# source sql-env/bin/activate   # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_api_key_here
```

### 5. Create the database

```bash
python database.py
```

This creates `data/ecommerce.db` with 4 tables (customers, orders, products, order_items) and sample data.

### 6. Start the server

```bash
uvicorn main:app --reload --port 8000
```

### 7. Open the UI

Navigate to **http://localhost:8000/ui**

---

## Features

### Ask Questions
- Type any natural language question about your data
- Gemini generates the SQL
- Review the SQL before running it
- See results as a table + chart (bar, line, pie, or scatter — auto-detected)
- Get a plain-English answer summarising the results
- Export results as CSV

### Show Table
- Browse any table with a dropdown selector
- See column names, types, row counts
- Preview up to 10 sample rows
- Upload CSV, Excel, or JSON files to add new tables

### Schema Explorer
- View column definitions for any selected table
- Filter by specific table
- Uploaded tables are tracked persistently — survive server restarts

### SQL Validator
- Paste any SQL and check if it's safe (read-only)
- Blocks DROP, DELETE, UPDATE, INSERT, and other write operations

### Dialect Translator
- Translate any SQLite query to MySQL, PostgreSQL, SQL Server, Oracle, BigQuery, or Snowflake
- Download the translated query as a `.sql` file

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ui` | Serves the web frontend |
| `GET` | `/` | Health check |
| `POST` | `/query` | Natural language → SQL (+ optional execution) |
| `POST` | `/upload` | Upload CSV/Excel/JSON → SQLite tables |
| `GET` | `/tables` | List all tables with columns and row counts |
| `GET` | `/schema` | Full schema info + dialect list |
| `GET` | `/sample/{table}` | Get up to 10 rows from a table |
| `DELETE` | `/tables/{table}` | Delete an uploaded table |
| `POST` | `/validate` | Check SQL safety |
| `POST` | `/translate` | Translate SQL to another dialect |

Full interactive docs at **http://localhost:8000/docs**

---

## How the AI Calls Work

Every time you ask a question and run it, exactly **3 Gemini API calls** are made:

1. **Generate SQL** — converts your question to a SQL query
2. **Explain SQL** — generates a plain-English description of the query
3. **Answer** — summarises the query results in 1–3 sentences

The SQL safety validator uses **pure regex** — no AI call needed.

---

## Uploading Your Own Data

1. Go to the **Show Table** tab
2. Drop a CSV, Excel, or JSON file into the upload zone
3. Click **Load Files**
4. The new table appears in the dropdown immediately
5. You can now ask questions about it in the **Ask Questions** tab
6. To delete an uploaded table, go to **Schema** tab and click the red **Delete** button on the table card

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Your Google Gemini API key |

---

## Notes

- The database file is stored at `../data/ecommerce.db` (one level above the project folder)
- Uploaded tables persist across server restarts — metadata is stored in `_querymind_meta` table inside SQLite
- Base tables (customers, orders, products, order_items) cannot be deleted
- SQL results are capped at 500 rows to prevent large payloads
