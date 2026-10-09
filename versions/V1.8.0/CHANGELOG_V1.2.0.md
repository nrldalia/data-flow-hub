# V1.2.0 — Retailer Data Setup and ordered configuration

Built from the local V1.1.0 enhancement. Adds a dedicated Retailer Data Setup page with retailer name and unique key, SM/HM/MM service type, retailer-specific editable store table, optional retailer alert contact and mandatory internal sender email. Configurations and samples persist in SQLite.

Adds Cleaning, Transformation and Validation rule dropdowns, reusable named rule creation, editable settings, rule movement and section movement. The backend applies the displayed sequence to the entire sample. Every rule and section has before/after table previews and detection results. Final Example shows the final data and exports all sample rows as CSV.

Sample uploads support CSV, XLSX and JSON and must be strictly smaller than 1,000,000 bytes. Previews show the first 25 rows. Samples are limited to 10,000 rows and 100 columns. Invalid numeric and date values are retained and flagged. Text-pattern validation uses literal text with * and ? wildcards.

Alert contact details are stored for later alert delivery; this release does not send emails. AI remains dormant. Existing V1.1.0 cleaning logs and previous application modules are preserved. Local databases, uploaded samples, runtime packages and machine-specific files are excluded from GitHub version snapshots.
