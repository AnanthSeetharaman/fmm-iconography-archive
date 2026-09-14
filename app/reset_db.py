#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Database Reset Utility (reset_db.py)
Executes clean-slate reset against DuckDB:
- Preserves only ananth.seetharaman@gmail.com as Admin
- Purges all studies, study_slides, and ALL child foreign tables:
    * slide_ocr_data
    * ai_metadata_proposals
    * study_taxonomy_mappings
    * content_access_rules
    * study_slides
    * studies
    * user_downloads
    * premium_download_requests
    * user_behavior_logs
    * audit_logs
- Preserves master reference tables (series, taxonomy_types, taxonomy_terms, dictionary, etc.)
- Uses auto-commit execution to avoid DuckDB foreign key transaction index locking.
"""

import os
import sys
import duckdb

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
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
    
    try:
        conn = duckdb.connect(db_path)
    except Exception as e:
        print(f"[-] Could not connect to DuckDB: {e}")
        print("    Stop running server before reset if file is locked.")
        sys.exit(1)
        
    print("[*] Purging all studies, study_slides, dynamic logs, and foreign child tables...")
    
    # Auto-commit mode: DuckDB updates internal foreign key indexes after each deletion,
    # avoiding false-positive constraint violation errors.
    statements = [
        "DELETE FROM user_downloads;",
        "DELETE FROM user_subscriptions WHERE user_id != 'usr_admin_ananth';",
        "DELETE FROM premium_download_requests;",
        "DELETE FROM user_behavior_logs;",
        "DELETE FROM audit_logs;",
        "DELETE FROM users WHERE email != 'ananth.seetharaman@gmail.com';",
        "DELETE FROM slide_ocr_data;",
        "DELETE FROM ai_metadata_proposals;",
        "DELETE FROM study_taxonomy_mappings;",
        "DELETE FROM content_access_rules;",
        "DELETE FROM study_slides;",
        "DELETE FROM studies;"
    ]
    
    for stmt in statements:
        conn.execute(stmt)
    
    print("[+] Clean-slate reset completed successfully!")
    print("\n=== Current Table Counts ===")
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    for t in sorted(tables):
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        status = "[PRESERVED]" if cnt > 0 else "[CLEARED]"
        print(f"  {status:12} {t:28}: {cnt} rows")
        
    print("\n=== Active Users in Archive ===")
    active_users = conn.execute("SELECT id, email, full_name, role FROM users").fetchall()
    for u in active_users:
        print(f"  [ADMIN USER] {u[1]} ({u[2]}) -> Role: {u[3]}")
        
    conn.close()

if __name__ == "__main__":
    main()
