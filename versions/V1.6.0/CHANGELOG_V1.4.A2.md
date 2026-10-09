# V1.4.A2 — Global MY6 storecode sequence

Amends V1.4.A1. SUITE storecodes now use MY6 followed by exactly seven zero-padded digits, starting at MY60000001. One persistent sequence serves all retailers: a new store in B can receive MY60000021, the next in A MY60000022, and the next in B MY60000023.

Allocations and retailer saves share a SQLite BEGIN IMMEDIATE transaction. A global registry enforces unique store identities, codes and sequence numbers. Simultaneous saves receive consecutive distinct numbers; failed saves roll back their allocation. Edits do not allocate new numbers, removing a store does not release its code, and restart/reinitialization preserves the counter. The allocator fails clearly at 9,999,999 instead of wrapping or extending the digit width.

At startup, existing valid MY6 codes are registered first and retained. UUID-style or missing storecodes are converted in retailer insertion order and existing store-array order, above the highest registered number. The registry retains each previous code as an internal migration reference. Migration is transactional and idempotent; duplicate existing MY6 codes are rejected rather than silently reassigned. User-provided codes remain ignored on ordinary store saves.

Updates the existing single V1.3.A1.bat launcher to start V1.4.A2 on port 5001. Local databases are backed up consistently and excluded from GitHub snapshots.
