# V1.6.0 — Separate batch log for every run

Enhances V1.5.A1. Every accepted run has a distinct Run ID and log row, including successful, interrupted, failed and user-cancelled runs for the same retailer/week. Successful runs no longer delete earlier jobs, sources, outputs or audits. Failed reprocessing creates its own Cancelled Job row with diagnostic codes rather than attaching a lastAttempt to the previous job. After three rule failures the row includes the operation error and RULE_RETRY_LIMIT. Cancelled jobs retain empty end time and audit, as requested earlier.

Both historical jobs and active attempts permit repeated retailer/week runs. Finalization is transactional and cancellation cannot later become completion. Store approval still adds only unknown stores with globally sequential MY6 codes. File-size deviation snapshots the latest successful/approved run from exactly the previous ISO week, selected by completion/start time and stable row order. Failed runs are excluded from that baseline.

Schema migration removes retailer/week uniqueness while retaining existing data. The most recent nested cancellation metadata retained by earlier releases is recovered as its own row. Its original file content and metrics were not retained and cannot be reconstructed; reprocessing that recovered row asks the user to upload the file. Earlier runs already deleted by the old overwrite behavior cannot be recovered.

The UI identifies runs by Run ID and updates batch/reprocess text to describe retained history. All ISO-week editing and audit receipt metrics remain available.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.6.0 at http://127.0.0.1:5001/.

Local databases are backed up consistently. Databases, uploads, personal configuration, installed dependencies and build output are excluded from GitHub.
