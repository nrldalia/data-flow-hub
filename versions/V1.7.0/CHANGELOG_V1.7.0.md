# V1.7.0 — Retailer configuration history and batch provenance

Enhances V1.6.A1. Save Configuration records a numbered, timestamped complete retailer snapshot, including retailer details, stores, exact rule order, descriptions, operation settings and conditions. Snapshots carry a stable identity and SHA-256 of canonical content. Unchanged saves reuse the latest version; failed saves do not create versions. Configuration update and version creation share a transaction. New-store approval also versions its setup change.

Configuration History in Client / Setup opens read-only versions with ordered rules and saved stores. Viewing history never replaces current configuration. No restore action is introduced.

Each new batch captures the exact configuration version at launch within the same transaction as its input/pipeline snapshot. Data Streams displays a Configuration vN link for successful, failed and cancelled runs. The audit shows the version number, and the link opens the full captured snapshot. Reprocessing uses the latest saved configuration and captures its version. Later setup changes or store approval cannot change an older run's snapshot. Versions remain available for retained batch audits after retailer deletion.

Existing retailer setups receive a baseline on first startup. Earlier setup edits cannot be reconstructed. Old batches without recorded provenance are labeled Configuration version not captured; their current setup is not claimed as the one used historically. Uploaded sample contents are not part of configuration snapshots.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.7.0 at http://127.0.0.1:5001/.

Local data is copied using SQLite backup. Databases, samples, personal configuration, installed dependencies and build output are excluded from GitHub.
