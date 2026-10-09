# V1.6.A1 — Client list and nested retailer Setup

Amends V1.6.0. Client is the first sidebar module and initial page. Replaces the placeholder Clients dashboard with a saved-retailer table containing an unlabeled checkbox column, Retailer Name, Setup Status and Edit. Removes the separate Retailer Data Setup sidebar entry. Edit opens the existing complete setup within Client, including retailer/store details, Rules Configure, sample upload and previews. Back to Client returns to a refreshed list. Add Retailer opens a new setup. Unsaved setup changes require discard confirmation when returning.

Setup Status is Ready when saved details, at least one store and executable rules in Cleaning, Transformation and Validation exist; otherwise Setup incomplete. A configuration containing an unimplemented rule reference displays Reference only. These are setup completeness indicators, not claims of successful batch execution.

Supports individual selection, select all with a mixed-selection state, and Delete with selected count. Deletion confirms the selected retailer count and removes configurations and samples in one transaction. Missing selections or a selected retailer with an active batch reject the entire operation. Recorded batch jobs and audits remain accessible. Storecode registry and sequence are retained so deleted storecodes are never reused. Reprocessing a deleted retailer requires a new setup and upload.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.6.A1 at http://127.0.0.1:5001/.

Local data is backed up consistently. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
