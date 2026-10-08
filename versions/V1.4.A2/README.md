# DataFlow V1.4.A2

Close the previous server window and open the same V1.3.A1.bat launcher. It now opens V1.4.A2 at http://127.0.0.1:5001/. Keep its window open. Fresh checkouts: run Setup_Windows.bat and Start_V1.4.A2.bat.

SUITE Storecode is automatically assigned on Save Store, using MY6 plus seven digits. The first new database starts at MY60000001. All retailers share the same counter: B → MY60000021, A → MY60000022, B → MY60000023. It never resets per retailer.

The code is read-only and remains fixed through store edits and retailer-key changes. Failed saves do not consume numbers; removed stores' numbers are not reused. The counter persists across restarts. The seven-digit limit is 9,999,999 stores allocated.

Existing UUID-style or missing codes convert to MY6 codes at first startup. Already-valid MY6 codes remain unchanged, and new allocations continue above the highest registered number. Previous codes are retained internally in store_code_registry. The previous release database remains available in its original version folder.

All Store Table Management, Rules Configuration and Data Streams features remain included.
