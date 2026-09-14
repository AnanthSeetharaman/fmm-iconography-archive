#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Database Reset Utility (reset_db.py)
Executes reset.sql against DuckDB with row-count reporting.
"""

import os
import sys
import duckdb

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(base_dir, "reset.sql")
    
    # Candidate database locations
    candidates = [
        os.path.join(base_dir, "backend", "data", "fmm_archive.duckdb"),
        os.path.join(base_dir, "backend", "fmm_archive.duckdb"),
        os.path.join(base_dir, "data", "fmm_archive.duckdb")
    ]
    
    db_path = None
    for c in candidates:
        if os.path.exists(c):
            db_path = c
            break
            
    if not db_path:
        print("[-] Error: fmm_archive.duckdb not found in known paths.")
        sys.exit(1)
        
    print(f"[*] Target Database: {db_path}")
    print(f"[*] Reading reset script: {sql_path}")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
        
    try:
        conn = duckdb.connect(db_path)
    except Exception as e:
        print(f"[-] Could not connect to DuckDB: {e}")
        print("    If the application server is running, stop it first or restart after reset.")
        sys.exit(1)
        
    print("[*] Executing reset script...")
    # Execute statements
    statements = [
        "DELETE FROM user_downloads",
        "DELETE FROM user_subscriptions",
        "DELETE FROM premium_download_requests",
        "DELETE FROM user_behavior_logs",
        "DELETE FROM audit_logs",
        "DELETE FROM users",
        "DELETE FROM slide_ocr_data",
        "DELETE FROM ai_metadata_proposals",
        "DELETE FROM study_slides"
    ]
    
    conn.execute("BEGIN TRANSACTION;")
    for stmt in statements:
        print(f"    -> {stmt}...")
        conn.execute(stmt + ";")
    conn.execute("COMMIT;")
    
    print("
[+] Database reset completed successfully!")
    print("
=== VERIFICATION: Current Table Counts ===")
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    for t in sorted(tables):
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        status = "[PRESERVED]" if cnt > 0 else "[CLEARED]"
        print(f"  {status:12} {t:28}: {cnt} rows")
        
    conn.close()

if __name__ == "__main__":
    main()
