import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend.crud_service import update_record

try:
    print("Testing update_record with series_id='1'...")
    update_record("studies", "5", {"access_level": "premium", "series_id": "1"})
    print("SUCCESS")
except Exception as e:
    print("ERROR:", str(e))
