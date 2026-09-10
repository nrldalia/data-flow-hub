import os
import json
import io
import pandas as pd
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types
from database import get_db_connection, init_db, seed_db

app = Flask(__name__)
CORS(app)

init_db()
seed_db()

api_key = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=api_key) if api_key else genai.Client()

@app.route('/api/v1/stores', methods=['GET'])
def get_stores():
    """Fetch stores and calculate basic data quality metrics for dashboard."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id as store_id, store_name, region, status FROM stores")
            stores = [dict(row) for row in cursor.fetchall()]
            
            # Fetch raw data counts for missing fields
            cursor.execute("SELECT store_id, missing_fields_count FROM raw_data_payloads")
            payload_map = {row['store_id']: row['missing_fields_count'] for row in cursor.fetchall()}

            for store in stores:
                store['missing_fields'] = payload_map.get(store['store_id'], 0)

        return jsonify({"success": True, "stores": stores})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/upload-and-clean', methods=['POST'])
def upload_and_clean():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files['file']
    filename = file.filename.lower()

    try:
        if filename.endswith('.json'):
            file_content = file.read().decode('utf-8')
            raw_data = json.loads(file_content)
            if isinstance(raw_data, dict):
                raw_data = [raw_data]
            file_type = 'json'
        elif filename.endswith('.csv'):
            df = pd.read_csv(file.stream)
            df = df.where(pd.notnull(df), None)
            raw_data = df.to_dict(orient='records')
            file_type = 'csv'
        else:
            return jsonify({"success": False, "error": "Unsupported format"}), 400

        sample_data = raw_data[:5]
        system_prompt = (
            "You are an expert Data Quality Engine. Analyze the provided dataset sample, "
            "apply data cleaning rules (strip whitespace, sanitize missing values to 'N/A', "
            "standardize date/numeric formats), and return the cleaned sample alongside "
            "an explicit list of transformation trace steps performed."
        )

        prompt = f"Dataset Sample to Clean:\n{json.dumps(sample_data, indent=2)}"

        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "cleanedSample": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "store_id": {"type": "STRING"},
                                    "store_name": {"type": "STRING"},
                                    "contact_email": {"type": "STRING"},
                                    "phone_number": {"type": "STRING"},
                                    "last_audit_date": {"type": "STRING"},
                                    "inventory_count": {"type": "STRING"},
                                    "monthly_revenue": {"type": "STRING"},
                                    "status": {"type": "STRING"}
                                }
                            }
                        },
                        "transformationTrace": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "step": {"type": "INTEGER"},
                                    "field": {"type": "STRING"},
                                    "action": {"type": "STRING"}
                                },
                                "required": ["step", "field", "action"]
                            }
                        }
                    },
                    "required": ["cleanedSample", "transformationTrace"]
                }
            )
        )

        ai_result = json.loads(response.text)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO stores (id, store_name, status) VALUES (?, ?, ?);",
                ("FILE_UPLOAD", "Uploaded Files Directory", "Pending")
            )
            cursor.execute(
                "INSERT INTO raw_data_payloads (store_id, raw_json_payload) VALUES (?, ?);",
                ("FILE_UPLOAD", json.dumps(raw_data[:20]))
            )
            conn.commit()

        return jsonify({
            "success": True,
            "filename": file.filename,
            "fileType": file_type,
            "totalRows": len(raw_data),
            "cleanedSample": ai_result.get("cleanedSample", []),
            "transformationTrace": ai_result.get("transformationTrace", [])
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/v1/export', methods=['POST'])
def export_dataset():
    """Export cleaned sample dataset matching original uploaded file extension."""
    try:
        payload = request.get_json()
        cleaned_data = payload.get("data", [])
        file_type = payload.get("fileType", "csv")

        if file_type == "csv":
            df = pd.DataFrame(cleaned_data)
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                output,
                mimetype="text/csv",
                as_attachment=True,
                download_name="cleaned_dataset.csv"
            )
        else:
            json_str = json.dumps(cleaned_data, indent=2)
            output = io.BytesIO(json_str.encode('utf-8'))
            output.seek(0)
            return send_file(
                output,
                mimetype="application/json",
                as_attachment=True,
                download_name="cleaned_dataset.json"
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)