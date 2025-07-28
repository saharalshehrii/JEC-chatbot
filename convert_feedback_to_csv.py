import os
import json
import csv

FEEDBACK_DIR = "feedback"
OUTPUT_CSV = "feedback.csv"

# نحفظ رؤوس الأعمدة
fields = ["session_id", "timestamp", "rating", "comment"]
rows = []

# نقرأ كل ملفات feedback/
for filename in os.listdir(FEEDBACK_DIR):
    if filename.endswith(".json"):
        path = os.path.join(FEEDBACK_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            session_id = filename.replace(".json", "")
            row = {
                "session_id": session_id,
                "timestamp": data.get("timestamp", ""),
                "rating": data.get("rating", ""),
                "comment": data.get("comment", "")
            }
            rows.append(row)

# نكتب البيانات في CSV
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"[✅] File saved as: {OUTPUT_CSV}")

