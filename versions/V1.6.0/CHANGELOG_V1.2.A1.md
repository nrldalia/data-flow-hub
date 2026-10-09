# V1.2.A1 — Data Streams batch audit log

Amends V1.2.0. Replaces the Data Streams cards with a paginated batch log: Retailer Name, Period (ISO week), Start Time, End Time, Status, Action and Audit Logs. Times display in Asia/Kuala_Lumpur. Sidebar uploads now open the batch form so new UI jobs receive a retailer and period.

Adds Completed, Completed with Interruption, Approved Job and Cancelled Job statuses; operator approval, cancellation and reprocessing actions; and a pencil button for execution-only audits. Every executed rule records its sequence, retry attempt, start/end timestamp, duration and Successful / Fail Execution result. Audit APIs and views contain no raw or cleaned row previews.

Validation findings count as failures, as requested. Each rule gets at most three attempts. A rule that recovers after a failed attempt yields Completed with Interruption. Three failures cancel automatically with operation-specific error codes and RULE_RETRY_LIMIT. Malformed input, server interruption and five-minute job timeouts also have explicit codes. Parsing and rule execution run in killable subprocesses, so cancellation and timeout stop work.

Cancelled jobs have no End Time, Audit Logs or stored output; error codes remain in the batch table. Cancelled replacement attempts preserve the previous recorded job and show their outcome alongside it, as confirmed by the user. A successful replacement transaction deletes the previous job, source, output and execution log and inserts the new job in the unique retailer/week slot. Concurrent duplicate attempts are rejected.

Configurations and existing retailer data are preserved. Earlier uploads without retailer/week metadata remain accessible through Quality Analytics; their missing batch timing and identity are not fabricated. Installed packages, databases and uploads are excluded from GitHub.
