import sqlite3
from pathlib import Path

db_path = Path.home() / ".preflight" / "reviews.db"
print(f"Checking database at: {db_path}")

if not db_path.exists():
    print("ERROR: Database file not found.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM issues")
    count = cursor.fetchone()[0]
    print(f"Row count in issues table: {count}")
    
    # Check for columns
    cursor.execute("PRAGMA table_info(issues)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "commit_hash" in columns:
        print("SUCCESS: commit_hash column exists.")
    else:
        print("FAILURE: commit_hash column missing.")
        
    if "branch" in columns:
        print("SUCCESS: branch column exists.")
    else:
        print("FAILURE: branch column missing.")

    if "project" in columns:
        print("SUCCESS: project column exists.")
    else:
        print("FAILURE: project column missing.")
        
    cursor.execute("SELECT file, commit_hash, branch, project FROM issues ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    print(f"Sample row (latest): {row}")
    
    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
