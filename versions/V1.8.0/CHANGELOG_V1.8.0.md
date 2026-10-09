# V1.8.0 — Independent New Store review

Enhances V1.7.0. Data Streams now has a compact Review New Stores action and an audit link opening a dedicated review page. Flagged stores show read-only received IDs, editable Store Name, Store Address, Active/Inactive status and exception Yes/No. Select one or multiple pending stores and choose Approve New Stores. Only selected details are saved; unselected stores remain pending. Back navigation confirms discarding unsaved edits.

Approve Job and Approve New Stores are independent. Approve Job changes only the job approval state and its audit entry. New Store approval adds reviewed stores without changing job status; it is available for completed, interrupted or approved jobs. Cancelled jobs cannot add stores. Store approval records a configuration version, review decision/time/generated code and a distinct action audit. The configuration originally pinned to the job remains unchanged.

Approval validates that each distinct selected ID was actually flagged by that run, validates store details, and atomically saves approved stores, global MY6 allocations, configuration history, review metadata and audit. Already-reviewed selections are rejected. Stores registered by another run are not duplicated or overwritten and are marked Already registered. Invalid selection/details leave all stores, codes and versions unchanged. Existing stores added by earlier job-approval releases are recognized rather than added again.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.8.0 at http://127.0.0.1:5001/.

Local data is backed up consistently. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
