-- Enable foreign key support in SQLite
PRAGMA foreign_keys = ON;

-- Table 1: Retail Client Stores
CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,               -- e.g., 'ST-101'
    store_name TEXT NOT NULL,
    region TEXT,
    status TEXT CHECK(status IN ('Clean', 'Error', 'Pending')) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: Raw Dirty Payloads received from client stores
CREATE TABLE IF NOT EXISTS raw_data_payloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    raw_json_payload TEXT NOT NULL,    -- JSON string stored as TEXT
    missing_fields_count INTEGER DEFAULT 0,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

-- Table 3: Step-by-Step Data Transformation Traces
CREATE TABLE IF NOT EXISTS transformation_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    action_taken TEXT NOT NULL,        -- e.g., "Filled missing key 'region' with 'N/A_DEFAULT'"
    cleaned_json_payload TEXT,         -- State of JSON after this trace step
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payload_id) REFERENCES raw_data_payloads(id) ON DELETE CASCADE
);

-- Table 4: Generated AI Communications
CREATE TABLE IF NOT EXISTS ai_generated_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    recipient_email TEXT,
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);

-- Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_raw_payloads_store ON raw_data_payloads(store_id);
CREATE INDEX IF NOT EXISTS idx_traces_payload ON transformation_traces(payload_id);