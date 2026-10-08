# V1.4.A2 validation

Production React/Vite/Tailwind build passed. All 51 backend tests passed across the existing app, retailer/store management, rule configuration and batch jobs, plus eight new global-sequence checks. These cover interleaved retailers, stable edits and no number reuse, rollback on failed saves, five simultaneous allocations, legacy-code migration with existing MY6 values, exhaustion at the seven-digit limit, restart persistence and rejection of duplicate imported codes.

Live browser interaction is not part of these checks. Storecode generation and persistence were verified through the API and SQLite transactions.
