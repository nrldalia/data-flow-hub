# V1.4.0 — Component rule popups

Enhances V1.3.0 with its V1.3.A1 and V1.3.A2 amendments. Replaces the component selector with Cleaning, Transformation and Validation buttons under a small Mandatory components label. Each opens a component Rules popup with rule selection, an editable description, prefilled Error 909: Successful at Execution and Error 908: Failure at Execution, plus Save and Cancel.

As clarified by the user, the table retains one row per individual rule. Popup Save appends one row; Cancel discards the draft. Existing reusable rules and Add New Rules remain supported. Table columns stay Components, Description, Sequence, Condition and Edit. Descriptions display as text. Edit opens only the description and execution messages. Condition opens a separate summary with its own Edit Condition button for field/operation settings and row conditions. Save Condition applies the draft; Cancel discards it. Save Configuration persists the ordered rules, descriptions and conditions. Rule/component/final previews remain available.

Batch rule audits add executionCode 909 for success and 908 for failure, while preserving specific diagnostic error codes and existing retry/cancellation behavior. The codes are prefilled rather than user-editable. Ingestion/approval audit entries retain their existing behavior. Old audits without these codes remain readable.

Keeps compact Data Streams action icons from V1.3.A2. Updates the existing single V1.3.A1.bat entry point to launch V1.4.0 on localhost port 5001. Preserves local data using SQLite backup; no data, samples or runtimes are included in GitHub snapshots.
