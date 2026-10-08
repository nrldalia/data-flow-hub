# DataFlow V1.2.A1

Close the previous DataFlow server. Double-click **Start_V1.2.A1.bat** and keep its window open. It opens http://127.0.0.1:5000 once the server is ready. For a fresh checkout, run Setup_Windows.bat first.

## Batch processing

1. Save a retailer and its ordered rules in Retailer Data Setup.
2. Open Data Streams and choose New Batch Job. Select the retailer, ISO week and CSV, XLSX or JSON file. Sidebar Upload Data File opens the same flow. Batch uploads use the existing 50 MB upload cap; retailer configuration samples retain their separate smaller-than-1-MB limit.
3. Follow the active job panel. Rules retry at most three times; invalid data findings count as failures. Jobs exceeding five minutes cancel automatically. Cancel Job stops an active attempt.
4. Completed jobs appear in the batch log. A recovered retry produces Completed with Interruption. Approve Job marks a completed job as Approved Job.
5. Click the pencil to view rule execution timings and success/failure results. Audit logs contain execution metadata only.
6. Reprocess uses the original source file with the retailer's latest saved rules. Uploading a different file for the same retailer and week also starts a replacement. The old job remains while the replacement runs. Success deletes the old job and logs; cancellation preserves them and shows the latest cancellation/error codes.

Cancelled jobs have blank End Time and Audit Logs. Relevant error codes appear with the status. RULE_RETRY_LIMIT means a rule failed three times; JOB_TIMEOUT means the processing time limit was reached.

The batch table records one job per retailer/week. Active replacement work appears separately and is never inserted as a duplicate recorded job. Existing older uploads that lacked retailer/week details remain under Quality Analytics.

## Development

Frontend: frontend-github/src/BatchLogs.jsx. Backend: script/batch_jobs.py. Build with npm run build inside frontend-github. Run the backend tests with python -m unittest discover -s script -v after building. Source snapshots and commits use the user-facing amendment code V1.2.A1; package metadata uses the valid npm version 1.2.1.
