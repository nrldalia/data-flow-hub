# DataFlow V1.4.0

Close the previous server window, then use the existing single V1.3.A1.bat launcher. It now opens V1.4.0 at http://127.0.0.1:5001/. Keep its window open. For a fresh checkout run Setup_Windows.bat, then Start_V1.4.0.bat.

In Retailer Data Setup → Rules Configure, click Cleaning, Transformation or Validation. Choose an individual rule, describe why it is used and click Save. Each saved draft adds one row. Cancel adds nothing. Execution messages are prefilled: Error 909 for Successful at Execution; Error 908 for Failure at Execution.

Use the row's Edit button to change its description. Use Condition → Edit Condition to change the field, operation parameters and matching-row condition. Save Condition applies these settings; Cancel leaves the row unchanged. Move rows with sequence arrows, inspect previews using a sample below 1 MB, and click Save Configuration to persist the full configuration.

The 909/908 execution codes appear in new rule audit entries alongside existing specific diagnostic codes. Existing retry, cancellation and replacement behavior is retained. Data Streams action icons remain compact.
