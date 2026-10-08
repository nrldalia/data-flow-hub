# DataFlow V1.4.A1

Close the previous server window and open the existing single V1.3.A1.bat launcher. It now opens V1.4.A1 at http://127.0.0.1:5001/. Keep its window open. Fresh checkouts: run Setup_Windows.bat and Start_V1.4.A1.bat.

In Retailer Data Setup, Store Table Management shows Retailer Store ID, Retailer Store Name, SUITE Storecode, Active, Inactive and Edit. Click Add Store or a row's pencil to open the store page.

Retailer Name is prefilled. Retailer Key is editable and shared across all stores under that retailer. Set Store ID, Store Name, optional Store Address, Active/Inactive and exception Yes/No. Save Store persists the changes and generates a read-only SUITE Storecode for a new store. Future edits keep that code. Cancel or Back discards the draft.

Existing stores without storecodes receive them on the next save. Codes use SUITE- plus a UUID. Store IDs remain unique within a retailer; retailer keys remain unique across retailers. A duplicate-key error leaves saved data unchanged.

Rules Configuration and Data Streams features from V1.4.0 remain included.
