import os
import uuid
import pandas as pd
from config import TEST_CASES_PATH


def load_test_cases(csv_path=None):
    csv_path = csv_path or TEST_CASES_PATH
    documents = []
    if not os.path.exists(csv_path):
        print(f"Test cases file not found: {csv_path}")
        return documents

    try:
        if csv_path.lower().endswith(".csv"):
            df = pd.read_csv(csv_path)
        elif csv_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(csv_path)
        else:
            print(f"Unsupported file format: {csv_path}")
            return documents

        for idx, row in df.iterrows():
            content = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            documents.append({
                "id": f"tc_{uuid.uuid4().hex[:8]}",
                "content": content,
                "source": os.path.basename(csv_path),
                "type": "test_case",
                "row_index": idx,
            })
    except Exception as e:
        print(f"Error loading test cases: {e}")

    return documents
