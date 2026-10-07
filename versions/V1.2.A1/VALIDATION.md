# V1.2.A1 validation

Production React/Vite/Tailwind build passed.

30 backend tests cover existing retailer setup and cleaning behavior plus completed/approved/cancelled statuses, retries, validation failures, timeout cancellation, timing-only audits, replacement deletion, preservation on cancellation, cancellation races, uniqueness and latest-rule reprocessing.

Real Windows multiprocessing checks passed for subprocess parsing, rule execution, audit timing and automatic timeout cancellation. Smoke data used an isolated work database. The previous retailer database was preserved with a consistent SQLite backup.

Interactive browser automation remains unavailable in this session. Use the Windows launcher to review the UI locally; starting the server inside the sandbox previously did not expose a reachable localhost endpoint to the browser.
