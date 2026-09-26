import os
import uuid
import psycopg2
from pathlib import Path


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "ekasutra_db"),
        user=os.getenv("DB_USER", "ekasutra_user"),
        password=os.getenv("DB_PASSWORD", "ekasutra_password"),
    )


def insert_demo_materials(cur):
    cur.execute(
        """
        INSERT INTO cpse_materials (cpse_name, original_code, raw_description,
                                    raw_specs, normalized_description, category, embedding)
        VALUES
            ('Pipe-A', 'PA-001', 'A 2-inch carbon steel pipe', NULL, 'pipe a', 'Pipes', NULL),
            ('Pipe-B', 'PB-001', 'A 2-inch carbon steel pipe (identical)', NULL, 'pipe b', 'Pipes', NULL)
        ON CONFLICT DO NOTHING
        RETURNING id;
        """
    )
    return [row[0] for row in cur.fetchall()]


def insert_demo_match(cur, a_id, b_id):
    cur.execute(
        """
        INSERT INTO material_matches
            (material_a_id, material_b_id, semantic_score,
             spec_agreement, decision_level, status)
        VALUES
            (%s, %s, 0.94,
             %s, 'exact', 'pending_review')
        ON CONFLICT DO NOTHING;
        """,
        (a_id, b_id, '{"critical": true, "soft": false, "irrelevant": false}')
    )


def main():
    conn = get_connection()
    cur = conn.cursor()
    try:
        a_id, b_id = insert_demo_materials(cur)
        if a_id and b_id:
            insert_demo_match(cur, a_id, b_id)
            print(f"✅ Demo pair inserted (ids {a_id}, {b_id})")
        else:
            print("ℹ️  Materials already exist – skipping insert.")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print("❌ Error while seeding demo data:", exc)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
