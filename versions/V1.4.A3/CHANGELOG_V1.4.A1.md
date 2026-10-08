# V1.4.A1 — Store Table Management

Amends V1.4.0. Replaces the inline store inputs with Retailer Store ID, Retailer Store Name, SUITE Storecode, Active, Inactive and Edit columns. Status indicators are mutually exclusive. The pencil opens a separate store edit page; Add Store opens the same page with a new draft.

The page prefills the retailer name and shared retailer key. Includes editable Store ID, Store Name and Store Address, Active/Inactive and exception Yes/No radio choices, and a read-only SUITE Storecode. As confirmed by the user, Retailer Key updates the retailer's shared key for all its stores. Save Store persists the retailer/store data and returns to the table; Cancel/Back discard the store draft. Store saves require valid retailer information and rule configuration.

The server assigns each saved store an immutable identity and a SUITE-prefixed UUID storecode. Updates preserve the code even if the Store ID or shared retailer key changes, ignoring caller attempts to overwrite it. New codes are distinct; invalid or reused identities are rejected. Existing legacy stores receive codes on their next save, defaulting to Active, no exception and an empty optional address. Shared-key uniqueness conflicts roll back atomically.

Preserves Rules Configuration popups, batch audit codes and compact Data Streams icons. The existing single V1.3.A1.bat entry point now launches V1.4.A1 on port 5001. Local data is copied via a consistent SQLite backup and excluded from GitHub.
