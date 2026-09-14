import sys
import os
import json
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from backend.search_service import scholar_search

res = scholar_search(query=None, limit=5, offset=0)
for s in res["results"]:
    print(json.dumps(s, indent=2))
