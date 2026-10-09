# V1.5.A1 — Editable ISO week

Replaces the browser-dependent week input with an editable YYYY-Www text field when starting a batch. The current Malaysia ISO week remains the default. Input accepts any valid ISO week, with backend checks for actual calendar week existence.

The Reprocess icon now opens a popup with the original period prefilled and an editable ISO week. The chosen week drives retailer/week uniqueness and the previous-week file-size baseline. Reprocessing in the same week preserves the existing successful-replacement behavior. Choosing another week keeps the original job/audit and creates or replaces the target-week job only upon success. A cancelled attempt preserves any previous target-week job. Concurrent jobs in the same retailer/week are rejected. Existing API clients that omit the period retain same-week reprocessing.

Use the existing outputs/V1.3.A1.bat launcher. Close the old server window and reopen it to load V1.5.A1 at http://127.0.0.1:5001/.

Local data is copied using SQLite backup. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
