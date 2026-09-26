import psycopg2
import os
from pathlib import Path

# Use environment variables or fallback to defaults matching docker-compose
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "ekasutra_db")
DB_USER = os.environ.get("DB_USER", "ekasutra_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "ekasutra_password")

def init_db():
    print(f"Connecting to {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()

        migration_dir = Path(__file__).parent.parent / "migrations"
        
        for migration_file in sorted(os.listdir(migration_dir)):
            if migration_file.endswith(".sql"):
                migration_path = migration_dir / migration_file
                print(f"Reading migration file from {migration_path}...")
                with open(migration_path, "r") as f:
                    sql = f.read()

                sql = sql.strip()
                if not sql:
                    print(f"Skipping empty migration {migration_file}...")
                    continue
                print(f"Executing {migration_file}...")
                cursor.execute(sql)
                
        print("All migrations executed successfully.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    init_db()
