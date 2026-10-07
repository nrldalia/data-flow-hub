# DataFlow Hub — Improved original v1.0

Enhances the original React/Vite/Tailwind frontend and Flask/Pandas/SQLite backend. The original navy/slate/blue colours, sidebar, four pages and split-pane Clients screen are preserved. This package does not use Streamlit.

## Windows quick start

Prerequisites: Python 3.11/3.12 with Add Python to PATH, plus Node.js 20.19+ or 22.12+. First-time installation requires internet access.

1. Extract this ZIP into a writable folder.
2. Double-click **Setup_Windows.bat** and let dependency installation/build finish.
3. Double-click **Start_DataFlow.bat**.
4. Open **http://localhost:5000** in your browser after the terminal says the server is running.
5. Keep the terminal open. Ctrl+C stops the app.

The Flask server serves the built React app, so normal use needs only one server. Source development retains the original two-process approach:

Backend terminal:
```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r script\requirements.txt
python script\app.py
```
Frontend terminal:
```bat
cd frontend-github
npm ci
npm run dev
```
Open http://localhost:5173 for development. Vite proxies `/api` to Flask on port 5000. After editing React, run `npm run build` again before using the single-server launcher. On macOS/Linux activate with `source .venv/bin/activate`.

## Try a full processing run

- Upload `sample_data/retail.csv` using the existing sidebar button.
- The modal opens before processing. Enter numeric fields `sales, quantity`, required fields `store_id, sales`, date field `date`, and date format `%d/%m/%Y`.
- Keep Trim enabled, then click **Run Full-Dataset Cleaning**.
- Compare true raw/processed previews. Inspect retained invalid/missing values and flagged duplicates.
- Export contains all eight rows, although previews show five.
- Download audit evidence; reopen the run from Data Streams or Quality Analytics.
- Edit a store and refresh the page to verify the edit persists.

## Improvements

| Original behaviour | Improved behaviour |
|---|---|
| Gemini cleans five rows only | Deterministic rules process every row; previews are separate |
| Export downloads cleaned sample | Export reads the full saved output by run ID |
| Raw preview can show cleaned values | API returns actual original preview |
| Upload triggers immediate AI processing | Configure rules first, then explicitly run |
| Run button has no handler | Connected to full-dataset processing |
| Edits disappear on refresh | Flask PUT endpoint persists store changes |
| Offline backend silently displays fake stores | Connection error is visible |
| Fixed 98.5% clean-record metric | Calculated store-status percentage and measured run metrics |
| Static AI insight cards | Actual run count and configured AI status |
| Audit schema exists without saved traces | Source bytes, all raw records, rules, traces, issues and output persist |
| No run history | Reopen prior runs and download audit ZIPs |
| CSV/JSON only | CSV, JSON and first-sheet Excel import/export |
| Copied email differs from displayed draft | Copies the complete displayed draft |

## Optional AI assistance

Set environment variables in the terminal before starting Flask:

```bat
set GEMINI_API_KEY=your_key_here
set GEMINI_MODEL=gemini-2.5-flash
.venv\Scripts\python.exe script\app.py
```

Use a model available to your account. The backend holds the key; it is not embedded in React. In a result modal, opt in to sharing five original rows and up to twenty issues, then request suggestions. AI explains issues/recommends rules; it never automatically changes records. Edit rules and rerun if you want to act on its advice. Automation works without AI or when a provider call fails. Live Gemini calls require your own key, quota and internet; no live AI call was verified during this build.

## Validation

```bat
cd script
python -m unittest test_app -v
```

Frontend: `npm run build` in frontend-github. Backend tests cover full output beyond five rows, raw preview, run-specific traces, audit source preservation, persistent store edits, invalid uploads, date/numeric issues, retained duplicates, CSV/Excel exports, AI consent/fallback and measured history metrics.

## Persistence and scope

SQLite is created at `script/dataflow.db`; copy it with the app stopped to back up all stores and run evidence. The original database schema is retained and extended with processing_runs and run_evidence. Existing databases initialize the new tables without deleting original tables. Store IDs remain globally unique in this edition. FILE_UPLOAD is a technical payload owner hidden from the client-store list. New uploads are not auto-associated with individual stores, so client-store missing-field counts and statuses are independent of file-run checks.

Local portfolio app, not a production multi-user system. No authentication, access roles, unattended scheduler, client-specific mappings, saved rule templates, column mapping, exclusions, freight or finance additions in this first improvement pass. Invalid numeric/date values are retained and flagged, not coerced into invented data. Duplicate checks compare complete processed records. Excel uses the first worksheet. Original CSV/XLSX columns are read as text to preserve leading zeros. JSON object/list input supports arbitrary fields. Numeric fields must contain plain numeric values; currency stripping is not automatic.

Input validation errors are shown without creating a saved run. Successfully processed runs are preserved. Audit downloads contain original bytes, source hash, rules, full output, changes and issues. Database administrators can alter SQLite; this is not a tamper-proof log. The API returns all change/issue entries and processes in memory; the 50 MB upload cap is not a scalability guarantee. The sample data and store seed are demonstrations. Client emails are drafts only and are never sent automatically.

This is a separate improved copy. The user's GitHub repository, original release and previous Streamlit ZIP were not overwritten. See CHANGELOG.md for the implementation record.
