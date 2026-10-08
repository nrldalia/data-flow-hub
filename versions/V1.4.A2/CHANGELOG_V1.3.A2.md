# V1.3.A2 — Compact Data Streams actions

Replaces Reprocess, Approve Job and Cancel Job text buttons with refresh, check and X icons in compact 32-pixel square controls. Applies the same cancel icon to active jobs. Adds title tooltips, accessible button names and keyboard focus outlines. Pending replacement work uses a spinner with an accessible status. Aligns the audit pencil with the same square control style.

Retains status-based action availability, busy states, existing handlers and the cancellation confirmation. The existing single V1.3.A1.bat entry point now launches V1.3.A2. Local data is preserved through SQLite backup and excluded from GitHub.
