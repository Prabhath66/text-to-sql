# app/database.py — Create and seed the sample e-commerce SQLite database.
# Run once with: python -m app.database

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    email        TEXT    UNIQUE NOT NULL,
    city         TEXT    NOT NULL,
    country      TEXT    NOT NULL DEFAULT 'India',
    joined_date  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    price        REAL    NOT NULL CHECK(price >= 0),
    stock        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date   TEXT    NOT NULL,
    status       TEXT    NOT NULL CHECK(status IN ('pending','processing','shipped','delivered','cancelled')),
    total_amount REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL REFERENCES orders(order_id),
    product_id   INTEGER NOT NULL REFERENCES products(product_id),
    quantity     INTEGER NOT NULL CHECK(quantity > 0),
    unit_price   REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS _querymind_meta (
    table_name   TEXT PRIMARY KEY,
    source       TEXT NOT NULL DEFAULT 'base',
    source_file  TEXT,
    uploaded_at  TEXT DEFAULT (datetime('now'))
);
"""

CUSTOMERS = [
    ("Arjun Sharma",   "arjun.sharma@email.com",   "Mumbai",    "India", "2022-01-15"),
    ("Priya Reddy",    "priya.reddy@email.com",    "Hyderabad", "India", "2022-03-22"),
    ("Rahul Gupta",    "rahul.gupta@email.com",    "Delhi",     "India", "2022-05-10"),
    ("Sneha Patel",    "sneha.patel@email.com",    "Bangalore", "India", "2022-07-04"),
    ("Vikram Singh",   "vikram.singh@email.com",   "Chennai",   "India", "2022-08-19"),
    ("Anjali Mehta",   "anjali.mehta@email.com",   "Pune",      "India", "2022-10-30"),
    ("Kiran Kumar",    "kiran.kumar@email.com",    "Kolkata",   "India", "2023-01-11"),
    ("Deepa Nair",     "deepa.nair@email.com",     "Jaipur",    "India", "2023-03-05"),
    ("Suresh Rao",     "suresh.rao@email.com",     "Ahmedabad", "India", "2023-05-20"),
    ("Meena Iyer",     "meena.iyer@email.com",     "Lucknow",   "India", "2023-07-14"),
]

PRODUCTS = [
    ("Samsung Galaxy S24",      "Electronics",  74999.00, 50),
    ("Apple iPhone 15",         "Electronics", 129900.00, 30),
    ("OnePlus 12",              "Electronics",  64999.00, 75),
    ("Dell XPS 15 Laptop",      "Electronics", 149999.00, 20),
    ("Sony WH-1000XM5",         "Electronics",  29990.00, 100),
    ("Nike Air Max 270",        "Footwear",      8999.00, 200),
    ("Levi's 511 Slim Jeans",   "Apparel",       3499.00, 300),
    ("Prestige Pressure Cooker","Kitchen",       2299.00, 150),
    ("Instant Pot Duo 7-in-1",  "Kitchen",       8999.00, 60),
    ("The Alchemist (Book)",    "Books",          399.00, 500),
    ("Atomic Habits (Book)",    "Books",          499.00, 500),
    ("Yoga Mat Premium",        "Sports",        1499.00, 120),
]

ORDERS = [
    (1,  "2024-01-05", "delivered",   74999.00),
    (2,  "2024-01-18", "delivered",  134399.00),
    (3,  "2024-02-02", "delivered",   64999.00),
    (4,  "2024-02-14", "shipped",     38989.00),
    (5,  "2024-03-01", "delivered",  149999.00),
    (6,  "2024-03-20", "processing",  11298.00),
    (7,  "2024-04-05", "delivered",    8999.00),
    (8,  "2024-04-22", "cancelled",    3499.00),
    (1,  "2024-05-10", "delivered",   29990.00),
    (2,  "2024-05-28", "shipped",     17998.00),
    (3,  "2024-06-15", "delivered",    9398.00),
    (9,  "2024-06-30", "pending",      2299.00),
    (10, "2024-07-08", "delivered",    8999.00),
    (4,  "2024-07-25", "delivered",   74999.00),
    (5,  "2024-08-10", "shipped",      1499.00),
]

ORDER_ITEMS = [
    (1,  1,  1,  74999.00),
    (2,  2,  1, 129900.00),
    (2,  10, 1,    399.00),
    (3,  3,  1,  64999.00),
    (4,  5,  1,  29990.00),
    (4,  6,  1,   8999.00),
    (5,  4,  1, 149999.00),
    (6,  7,  2,   3499.00),
    (6,  10, 1,    399.00),
    (7,  9,  1,   8999.00),
    (8,  7,  1,   3499.00),
    (9,  5,  1,  29990.00),
    (10, 6,  2,   8999.00),
    (11, 10, 2,    399.00),
    (11, 11, 1,    499.00),
    (11, 12, 1,   1499.00),
    (12, 8,  1,   2299.00),
    (13, 9,  1,   8999.00),
    (14, 1,  1,  74999.00),
    (15, 12, 1,   1499.00),
]


def create_database() -> None:
    """Create the SQLite database, all tables, and seed them with sample e-commerce data."""
    print(f"Creating database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.executescript(SCHEMA_SQL)

    cursor.executemany(
        "INSERT OR IGNORE INTO customers (name, email, city, country, joined_date) VALUES (?,?,?,?,?)",
        CUSTOMERS,
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO products (name, category, price, stock) VALUES (?,?,?,?)",
        PRODUCTS,
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO orders (customer_id, order_date, status, total_amount) VALUES (?,?,?,?)",
        ORDERS,
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
        ORDER_ITEMS,
    )

    conn.commit()

    base_tables = ("customers", "products", "orders", "order_items")
    cursor.executemany(
        "INSERT OR IGNORE INTO _querymind_meta (table_name, source) VALUES (?, 'base')",
        [(t,) for t in base_tables],
    )
    conn.commit()

    for table in base_tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    conn.close()
    print("Database ready.")


if __name__ == "__main__":
    create_database()
