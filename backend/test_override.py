import requests
import json
import time

def run_test():
    # 1. Ingest test data
    csv_content = """cpse_name,original_code,description,spec_diameter
TestA,A-1,"Mild Steel Pipe 100mm",100mm
TestB,B-1,"Mild Steel Pipe 150mm",150mm
TestC,C-1,"MS Pipe DN100",DN100
"""
    with open("temp_test.csv", "w") as f:
        f.write(csv_content)
        
    print("--- Ingesting Test Data ---")
    resp = requests.post("http://localhost:8000/ingest", files={'file': open('temp_test.csv', 'rb')})
    print("Ingest Response:", resp.json())
    
    # 2. Get IDs for our test materials
    # Since we can't easily query DB without psycopg2 in this script, we'll assume the IDs are the last 3,
    # or better, just use psycopg2 to query them safely.
    import psycopg2, os
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname="ekasutra_db", user="ekasutra_user", password="ekasutra_password"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, original_code FROM cpse_materials WHERE original_code IN ('A-1', 'B-1', 'C-1') ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    id_map = {code: id for id, code in rows}
    
    target_100 = id_map['A-1']
    
    print(f"\n--- Running evaluation for 'Mild Steel Pipe 100mm' (ID: {target_100}) ---")
    resp = requests.post(f"http://localhost:8000/materials/{target_100}/find_and_evaluate_matches")
    data = resp.json()
    
    for match in data.get('matches', []):
        c_id = match['candidate_id']
        c_code = next(code for code, id in id_map.items() if id == c_id)
        
        print(f"\nEvaluating against candidate {c_code} (ID: {c_id}):")
        print(f"  Semantic Score: {match['semantic_score']:.4f}")
        print(f"  Override Triggered: {match['spec_result']['override_triggered']}")
        print(f"  Override Reason: {match['spec_result']['override_reason']}")
        print(f"  Final Decision: {match['decision']}")

if __name__ == "__main__":
    run_test()
