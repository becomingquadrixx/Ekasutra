"""
EKASUTRA E2E Pipeline Benchmarking 
Built with ❤️ by Team QUADRIX (SIH)

This script hits the live API endpoints and checks how well our matching algorithm is doing against the synthetic data.
Computes precision & recall by querying the db directly.
"""

import os
import sys
import csv
from pathlib import Path
import requests
import psycopg2

# Add backend directory to PYTHONPATH for imports
backend_path = Path(__file__).resolve().parents[1]
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import get_db_connection

BASE_URL = os.getenv('BASE_URL', 'http://backend:8000')


def cleanup_db():
    # clean the DB before running tests so we don't get duplicate errors/dirty state
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE material_matches, code_aliases, cnmc_registry, cpse_materials RESTART IDENTITY CASCADE")
    conn.commit()
    cur.close()
    conn.close()


def ingest_synthetic(csv_path: str):
    # hit the /ingest endpoint to trigger the matching pipeline
    with open(csv_path, 'rb') as f:
        files = {'file': ('synthetic_data.csv', f, 'text/csv')}
        resp = requests.post(f"{BASE_URL}/ingest", files=files)
    resp.raise_for_status()
    return resp.json()


def load_ground_truth(csv_path: str):
    # load our pre-defined ground truth pairs for testing
    pairs = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append({
                'a': (row['cpse_a'], row['code_a']),
                'b': (row['cpse_b'], row['code_b']),
                'should_match': row['should_match'].lower() == 'true'
            })
    return pairs


def main():
    synthetic_path = Path(__file__).with_name('synthetic_data.csv')
    gt_path = Path(__file__).with_name('ground_truth.csv')

    print('Cleaning database and ingesting synthetic dataset...')
    cleanup_db()
    ingest_result = ingest_synthetic(str(synthetic_path))
    print(f"Ingest result: {ingest_result}")

    print('Loading ground truth...')
    gt_pairs = load_ground_truth(str(gt_path))

    # map CPSE material pairs to IDs for easy lookup
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cpse_name, original_code FROM cpse_materials ORDER BY id")
    id_map = {(cpse, code): mid for mid, cpse, code in cur.fetchall()}

    gt_lookup = {}
    for pair in gt_pairs:
        a_id = id_map.get(pair['a'])
        b_id = id_map.get(pair['b'])
        if a_id is None or b_id is None:
            continue
        gt_lookup[(a_id, b_id)] = pair['should_match']
        gt_lookup[(b_id, a_id)] = pair['should_match']

    # fetch the final match decisions we saved in the DB
    cur.execute("SELECT material_a_id, material_b_id, status FROM material_matches")
    db_matches = cur.fetchall()
    cur.close()
    conn.close()

    true_positives = set()
    false_positives = set()
    false_negatives = set()
    trap_rejections = 0
    total_traps = 0

    # ENGINE
    for a_id, b_id, status in db_matches:
        is_proposed = status != 'rejected'
        should_match = gt_lookup.get((a_id, b_id), False)

        if is_proposed:
            if should_match:
                true_positives.add((min(a_id, b_id), max(a_id, b_id)))
            else:
                false_positives.add((min(a_id, b_id), max(a_id, b_id)))

    # calculate false negatives (missed matches)
    for (a_id, b_id), should_match in gt_lookup.items():
        if not should_match:
            total_traps += 1
            # Count each trap only once (gt_lookup has symmetric entries)
            if a_id < b_id:
                # did the hard gate catch this trap?
                rejected = any(
                    (ma == a_id and mb == b_id) or (ma == b_id and mb == a_id)
                    for ma, mb, st in db_matches if st == 'rejected'
                )
                if rejected:
                    trap_rejections += 1
            continue

        pair_key = (min(a_id, b_id), max(a_id, b_id))
        if pair_key not in true_positives:
            false_negatives.add(pair_key)

    precision = len(true_positives) / (len(true_positives) + len(false_positives)) if (len(true_positives) + len(false_positives)) else 0.0
    recall = len(true_positives) / (len(true_positives) + len(false_negatives)) if (len(true_positives) + len(false_negatives)) else 0.0
    n_pairs = len(gt_pairs)

    print('\n=== Benchmark Results ===')
    print(f'Precision: {precision:.3f}')
    print(f'Recall:    {recall:.3f}')
    print(f'Sample size (n): {n_pairs} material pairs')
    print(f'Near-duplicate traps correctly rejected: {trap_rejections} / {total_traps // 2}')
    print(f'True positives: {len(true_positives)}')
    print(f'False positives: {len(false_positives)}')
    print(f'False negatives: {len(false_negatives)}')

    results_dict = {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "sample_size": n_pairs,
        "trap_rejections": trap_rejections,
        "total_traps": total_traps // 2,
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives)
    }
    
    import json
    out_json = Path(__file__).with_name('last_results.json')
    with open(out_json, 'w') as f:
        json.dump(results_dict, f, indent=2)
    print(f"\nWrote results to {out_json}")
if __name__ == '__main__':
    main()
