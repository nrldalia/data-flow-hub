# DataFlow V1.3.0

Double-click Start_V1.3.0.bat and keep its window open. It opens http://127.0.0.1:5001/ when ready. The previous version can remain on port 5000. For a fresh checkout run Setup_Windows.bat first.

Open Retailer Data Setup → Rules Configure. Choose one Component, choose a Rule, then click Add Rules. Each click appends a table row. Use Edit to choose the field and operation settings, and the Description box to explain its purpose. Execution messages are prefilled.

Use Condition to open the popup. All rows removes any condition; other choices limit execution to matching rows. Comparisons use the data as it exists at this step. For example, sales greater than 100 applies the selected rule only to those rows. Conditions do not color cells or remove unmatched rows.

Move rows with the sequence arrows, including across Cleaning, Transformation and Validation. Save Configuration persists the displayed order, descriptions and conditions. Upload a sample smaller than 1 MB to inspect per-rule/component previews and the final example. Full batch jobs use the same saved sequence and conditions.

Source: frontend-github/src/RetailerSetup.jsx and script/retailer_setup.py. Build the frontend with npm run build; run python -m unittest discover -s script with an isolated temporary folder inside Codex for tests. Keep local databases and samples private.
