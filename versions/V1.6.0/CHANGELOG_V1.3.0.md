# V1.3.0 — Rules Configure table and conditions

Enhances V1.2.A1. Adds a single component dropdown above the sample area, followed vertically by the selected component's rule dropdown and Add Rules button. Only one component is selected at a time; each added rule appends one row.

The rules table uses Components, Description, Sequence, Condition and Edit columns. Descriptions explain the reason for each rule. Successful at Execution and Failure at Execution messages are prefilled and read-only. Edit opens the existing field/operation settings. Up/down arrows move rules across components; persistence, previews, exports and batch jobs use the exact displayed order.

Condition opens a popup with all rows, equal/not equal, numeric comparisons, inclusive between, text contains/begins/ends, and blank/not blank. Conditions gate which rows the operation applies to, using current values at that sequence step. Nonmatching rows are retained. Text matching is case-insensitive; numeric bounds are validated. Existing rules without conditions apply to all rows. Rule and component previews and the final example remain available.

No new error-code configuration is introduced; existing batch failure behavior is retained. V1.3.0 uses port 5001 via its launcher to coexist with V1.2.A1 on 5000. Local databases, uploaded samples and installed runtimes are excluded from GitHub snapshots.
