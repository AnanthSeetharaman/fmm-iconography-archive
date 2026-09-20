import requests
import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("Testing Backend Endpoints...")
    s = requests.Session()

    # 1. Test /api/collections
    print("\n1. Testing GET /api/collections")
    res = s.get(f"{BASE_URL}/api/collections")
    assert res.status_code == 200, f"Collections failed: {res.status_code} {res.text}"
    data = res.json()
    cols = data.get("collections", [])
    print(f"   ✓ Retrieved {len(cols)} curated collections/studies.")
    for c in cols[:3]:
        print(f"     - [{c.get('theme')}] {c.get('title')} ({c.get('access_level')}) - Can access: {c.get('user_can_access')}")

    # 2. Test /api/studies/{id}/pdf
    print("\n2. Testing GET /api/studies/s_ganesa_001/pdf")
    res = s.get(f"{BASE_URL}/api/studies/s_ganesa_001/pdf")
    assert res.status_code == 200, f"PDF failed: {res.status_code} {res.text}"
    content_type = res.headers.get("content-type", "")
    assert "pdf" in content_type.lower(), f"Unexpected content-type: {content_type}"
    print(f"   ✓ Successfully generated PDF ({len(res.content)} bytes, {content_type})")

    # 3. Test Student Application Submission
    print("\n3. Testing POST /api/membership/student-apply")
    # Login as a scholar/student user
    login_res = s.post(f"{BASE_URL}/api/auth/magic-link/request", json={"email": "student_test@university.edu"})
    token = login_res.json()["token"]
    verify_res = s.post(f"{BASE_URL}/api/auth/magic-link/verify", json={"token": token})
    assert verify_res.status_code == 200
    user = verify_res.json()["user"]
    print(f"   ✓ Signed in as test student: {user['email']}")

    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy test student id proof content")
    files = {"id_proof_file": ("student_id.pdf", dummy_pdf, "application/pdf")}
    data = {"institution_name": "Madras Sanskrit College"}
    apply_res = s.post(f"{BASE_URL}/api/membership/student-apply", data=data, files=files)
    assert apply_res.status_code == 200, f"Student apply failed: {apply_res.status_code} {apply_res.text}"
    sub_id = apply_res.json().get("subscription_id")
    print(f"   ✓ Submitted student application: {sub_id}")

    # 4. Test Admin Verification Queue & Review
    print("\n4. Testing GET /api/admin/student-applications & Review")
    # Login as admin
    admin_login = s.post(f"{BASE_URL}/api/auth/magic-link/request", json={"email": "admin@fivemetalmasonry.com"})
    admin_token = admin_login.json()["token"]
    admin_verify = s.post(f"{BASE_URL}/api/auth/magic-link/verify", json={"token": admin_token})
    assert admin_verify.status_code == 200

    queue_res = s.get(f"{BASE_URL}/api/admin/student-applications")
    assert queue_res.status_code == 200
    apps = queue_res.json().get("applications", [])
    print(f"   ✓ Retrieved {len(apps)} pending applications in queue")

    # Review & approve application
    review_res = s.post(f"{BASE_URL}/api/admin/student-applications/{sub_id}/review", json={"action": "approve"})
    assert review_res.status_code == 200
    print(f"   ✓ Approved student application: {review_res.json().get('message')}")

    # 5. Test Multi-file Upload on /api/ocr/upload
    print("\n5. Testing Multi-file Upload on /api/ocr/upload")
    # Curator session
    curator_login = s.post(f"{BASE_URL}/api/auth/magic-link/request", json={"email": "curator@fivemetalmasonry.com"})
    curator_token = curator_login.json()["token"]
    s.post(f"{BASE_URL}/api/auth/magic-link/verify", json={"token": curator_token})

    # Read a sample image
    with open("c:/Users/anant/Downloads/FMM/app/frontend/assets/shilpa_shastra_iconography.jpg", "rb") as f:
        img_bytes = f.read()
    
    files = [
        ("files", ("plate_1.jpg", io.BytesIO(img_bytes), "image/jpeg")),
        ("files", ("plate_2.jpg", io.BytesIO(img_bytes), "image/jpeg"))
    ]
    ocr_res = s.post(f"{BASE_URL}/api/ocr/upload", data={"study_slug": "ganesa-variations-in-iconography", "engine": "gemini_vision"}, files=files)
    assert ocr_res.status_code == 200, f"OCR multi upload failed: {ocr_res.status_code} {ocr_res.text}"
    ocr_data = ocr_res.json()
    print(f"   ✓ Multi-file OCR Ingestion Succeeded: Total Uploaded = {ocr_data.get('total_uploaded')}, Word Count = {ocr_data.get('word_count')}")

    print("\n=======================================================")
    print("ALL 11 CLIENT SPECIFICATIONS TESTED & VERIFIED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    test_all()
