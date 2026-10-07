# DataFlow V1.2.0

On this computer, double-click **Start_V1.2.0.bat** and keep the terminal open. Close any old DataFlow server first. The browser opens when the app is ready at http://127.0.0.1:5000.

For a fresh checkout, run Setup_Windows.bat first to install the project-local Python and frontend dependencies, then run Start_V1.2.0.bat.

1. Open Retailer Data Setup. Enter the retailer name, unique key, service type and mandatory internal sender email. Retailer email is optional. Add/edit/remove store rows, then save.
2. Upload a sample smaller than 1 MB. Samples and configurations are saved per retailer.
3. Choose Rules Configure. Each section dropdown adds an existing rule or lets you create a reusable named rule. Enter its field and settings.
4. Use arrows to reorder rules or sections. Execution follows the displayed order. Expand a rule or section to inspect before/after data and issues.
5. Review Preview Final Example, export its full CSV if needed, and save the configuration. Selecting the retailer later restores its details, rules and sample.

Configuration changes use the same deterministic backend engine as previews and full sample exports. Numeric/date failures preserve values for review. Required, range, wildcard text-pattern and uniqueness rules report detections without deleting records. No email is sent by this release.

Source: frontend-github/src/RetailerSetup.jsx and script/retailer_setup.py. Build the frontend with npm run build inside frontend-github after editing. Keep private databases and samples out of GitHub.
