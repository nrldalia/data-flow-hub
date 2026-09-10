import sqlite3
import json
import os

# Dynamically locate the directory where database.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "dataflow.db")
SCHEMA_FILE = os.path.join(BASE_DIR, "schema.sql")

def get_db_connection():
    """Establishes connection to the SQLite database with row factory and timeout enabled."""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows instead of tuples
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Reads schema.sql using its absolute path and initializes tables."""
    if not os.path.exists(SCHEMA_FILE):
        raise FileNotFoundError(f"Could not find schema.sql at: {SCHEMA_FILE}")
        
    with open(SCHEMA_FILE, "r") as f:
        schema_sql = f.read()

    conn = get_db_connection()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print("Database schema initialized successfully.")

def seed_db():
    """Seeds default stores and sample dirty payloads for testing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM stores;")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Seed Stores (Using 'id' column)
    stores_data = [
        ("ST-101", "Metro Retail Alpha", "North America", "Error"),
        ("ST-102", "Urban Mart West", "Europe", "Clean"),
        ("ST-103", "Metro Retail Bipte", "Asia Pacific", "Error")
    ]
    cursor.executemany(
        "INSERT INTO stores (id, store_name, region, status) VALUES (?, ?, ?, ?);",
        stores_data
    )

    # Seed Raw Dirty Payloads
    dirty_payload = {
        "store_name": "metro retail alpha",
        "region": None,
        "revenue": " 25000 ",
        "invalid_metric": ""
    }
    cursor.execute(
        "INSERT INTO raw_data_payloads (store_id, raw_json_payload, missing_fields_count) VALUES (?, ?, ?);",
        ("ST-101", json.dumps(dirty_payload), 2)
    )

    conn.commit()
    conn.close()
    print("Database seeded with sample data.")

if __name__ == "__main__":
    init_db()
    seed_db()