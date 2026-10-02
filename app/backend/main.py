import secrets
import time
import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel

from config import IMAGES_STORAGE_DIR, FRONTEND_DIR, HOST, PORT, GOOGLE_CLIENT_ID, SESSION_COOKIE_NAME, APP_DIR, LLM_MODEL
from database import init_duckdb_schema, get_db, get_param
from search_service import scholar_search, get_autocomplete
from ocr_service import (
    perform_ocr,
    clean_ocr_text,
    extract_candidate_proposals,
    commit_curator_approval,
    validate_iconography_image,
    get_ocr_context,
    create_new_study,
    create_new_series,
)
from ocr_grouping_service import infer_study_groupings
from auth_service import (
    verify_google_id_token,
    create_session_token,
    verify_session_token,
    upsert_user,
    get_current_user_from_request
)
from razorpay_service import create_subscription_order, verify_payment_signature
from pdf_service import generate_study_pdf, generate_image_only_pdf

# Initialize FastAPI App
app = FastAPI(
    title="Five Metal Masonry (FMM) Iconography Archive API",
    description="Professional Scholar Archive with DuckDB, OCR Ingestion, Re-Ranking, Google OAuth, and DRM Protection",
    version="1.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent XSS
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions Policy (restrict camera, mic, geolocation)
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # CSP: Allow same-origin, Google fonts/CDN, Google Identity Services, and Razorpay
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://cdnjs.cloudflare.com https://checkout.razorpay.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://images.unsplash.com https://*.googleusercontent.com https://*.razorpay.com blob:; "
        "connect-src 'self' https://accounts.google.com https://api.razorpay.com https://lumberjack.razorpay.com https://*.razorpay.com; "
        "frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    return response

# Initialize DuckDB Schema on startup
@app.on_event("startup")
def on_startup():
    init_duckdb_schema()


def check_active_subscription(user_id):
    """Check if a user has an active paid or trial subscription."""
    if not user_id:
        return False
    try:
        conn = get_db()
        result = conn.execute(
            """SELECT COUNT(*) FROM user_subscriptions 
               WHERE user_id = ? 
                 AND status = 'active' 
                 AND tier IN ('trial_member', 'trial', 'student', 'scholar', 'scholar_pro', 'member', 'patron')
                 AND (next_billing_date IS NULL OR next_billing_date >= CURRENT_TIMESTAMP)""",
            (str(user_id),)
        ).fetchone()
        conn.close()
        return bool(result and result[0] > 0)
    except Exception:
        return False

def ensure_trial_subscription(user_id: str, email: str = "") -> dict:
    """Provisions a free-trial membership for users signing in via Google SSO or trial flow.

    Trial length is driven by the `trial_duration_days` param_config value (default 30).
    """
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id, tier, status, next_billing_date FROM user_subscriptions WHERE user_id = ?",
            (str(user_id),)
        ).fetchone()
        if existing:
            return {
                "id": existing[0],
                "tier": existing[1],
                "status": existing[2],
                "expires_at": str(existing[3]) if existing[3] else None
            }

        # Configurable trial duration (validated int -> safe to inline in INTERVAL)
        try:
            trial_days = int(float(get_param(conn, "trial_duration_days", "30") or 30))
        except Exception:
            trial_days = 30
        if trial_days <= 0:
            trial_days = 30

        sub_id = f"sub_trial_{uuid.uuid4().hex[:8]}"
        conn.execute(f"""
            INSERT INTO user_subscriptions (id, user_id, tier, status, billing_cycle, amount_inr, payment_due_amount, next_billing_date, payment_method)
            VALUES (?, ?, 'trial_member', 'active', 'trial', 0.0, 0.0, CURRENT_TIMESTAMP + INTERVAL {trial_days} DAY, 'google_sso');
        """, (sub_id, str(user_id)))
        conn.commit()
        return {
            "id": sub_id,
            "tier": "trial_member",
            "status": "active",
            "is_new_trial": True
        }
    except Exception as e:
        print(f"Error provisioning trial subscription: {e}")
        return {}
    finally:
        conn.close()

# Mount Static Storage (Slide Images)
app.mount("/storage/images", StaticFiles(directory=str(IMAGES_STORAGE_DIR)), name="storage_images")

# Student Proofs Storage Directory
STUDENT_PROOFS_DIR = APP_DIR / "backend" / "storage" / "student_proofs"
STUDENT_PROOFS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage/student_proofs", StaticFiles(directory=str(STUDENT_PROOFS_DIR)), name="student_proofs")

# Mount Archival Raw Images Directory if present
IMAGES_ARCHIVE_DIR = APP_DIR.parent / "Images-archieve"
if IMAGES_ARCHIVE_DIR.exists():
    app.mount("/Images-archieve", StaticFiles(directory=str(IMAGES_ARCHIVE_DIR)), name="images_archieve")
    app.mount("/Images-archive", StaticFiles(directory=str(IMAGES_ARCHIVE_DIR)), name="images_archive")


# ----------------------------------------------------------------------------
# 0. AUTHENTICATION & GOOGLE OAUTH 2.0 ENDPOINTS
# ----------------------------------------------------------------------------

class GoogleAuthPayload(BaseModel):
    id_token: str

class DemoAuthPayload(BaseModel):
    role: str = "scholar"
    name: Optional[str] = None
    email: Optional[str] = None

@app.get("/api/health")
def api_health():
    """Health check endpoint for Google Cloud Run container liveness probe."""
    return {"status": "healthy", "service": "fmm-iconography-archive", "engine": "duckdb"}

# ----------------------------------------------------------------------------
# CONFIG API: Externalized Application Configuration
# ----------------------------------------------------------------------------

@app.get("/api/config")
def api_get_config(group: Optional[str] = Query(None)):
    """Returns public (non-sensitive) configuration parameters. Optionally filter by param_group."""
    conn = get_db()
    if group:
        rows = conn.execute(
            "SELECT param_group, param_key, param_value, value_type, description FROM param_config WHERE param_group = ? AND is_sensitive = FALSE ORDER BY param_group, param_key",
            (group,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT param_group, param_key, param_value, value_type, description FROM param_config WHERE is_sensitive = FALSE ORDER BY param_group, param_key"
        ).fetchall()
    conn.close()

    result = {}
    for r in rows:
        grp, key, val, vtype, desc = r
        if grp not in result:
            result[grp] = {}
        # Cast value based on type
        if vtype == "number":
            try: val = float(val) if "." in val else int(val)
            except: pass
        elif vtype == "boolean":
            val = val.lower() in ("true", "1", "yes")
        result[grp][key] = {"value": val, "type": vtype, "description": desc}

    return {"config": result}

@app.get("/api/config/all")
def api_get_all_config(request: Request):
    """Returns ALL configuration (including sensitive). Requires admin role."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to view all configuration")

    conn = get_db()
    rows = conn.execute(
        "SELECT id, param_group, param_key, param_value, value_type, description, is_sensitive, created_by, updated_by, created_at, updated_at FROM param_config ORDER BY param_group, param_key"
    ).fetchall()
    conn.close()

    return {"configs": [
        {
            "id": r[0], "param_group": r[1], "param_key": r[2],
            "param_value": r[3] if not r[6] else "***REDACTED***",
            "value_type": r[4], "description": r[5], "is_sensitive": r[6],
            "created_by": r[7], "updated_by": r[8],
            "created_at": str(r[9]) if r[9] else None,
            "updated_at": str(r[10]) if r[10] else None
        } for r in rows
    ]}

class ConfigUpdatePayload(BaseModel):
    param_value: str

@app.put("/api/config/{config_id}")
def api_update_config(config_id: str, payload: ConfigUpdatePayload, request: Request):
    """Updates a configuration parameter. Requires admin role."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to update configuration")

    conn = get_db()
    existing = conn.execute("SELECT id FROM param_config WHERE id = ?", (config_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Configuration parameter not found")

    conn.execute(
        "UPDATE param_config SET param_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (payload.param_value, user.get("email", "admin"), config_id)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Configuration {config_id} updated"}

class ConfigCreatePayload(BaseModel):
    param_group: str
    param_key: str
    param_value: str
    value_type: str = "string"
    description: str = ""
    is_sensitive: bool = False

@app.post("/api/config")
def api_create_config(payload: ConfigCreatePayload, request: Request):
    """Creates a new configuration parameter. Requires admin role."""
    import uuid
    user = get_current_user_from_request(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = get_db()
    # Check for duplicates
    dup = conn.execute(
        "SELECT id FROM param_config WHERE param_group = ? AND param_key = ?",
        (payload.param_group, payload.param_key)
    ).fetchone()
    if dup:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Config '{payload.param_group}.{payload.param_key}' already exists")

    config_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO param_config (id, param_group, param_key, param_value, value_type, description, is_sensitive, created_by, updated_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (config_id, payload.param_group, payload.param_key, payload.param_value, payload.value_type, payload.description, payload.is_sensitive, user.get("email", "admin"), user.get("email", "admin"))
    )
    conn.commit()
    conn.close()
    return {"status": "success", "id": config_id}

@app.delete("/api/config/{config_id}")
def api_delete_config(config_id: str, request: Request):
    """Deletes a configuration parameter. Requires admin role."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = get_db()
    conn.execute("DELETE FROM param_config WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Configuration {config_id} deleted"}

@app.get("/api/auth/config")
def api_auth_config():
    """Returns public authentication configuration for frontend initialization."""
    client_id = GOOGLE_CLIENT_ID
    try:
        conn = get_db()
        row = conn.execute("SELECT param_value FROM param_config WHERE param_group = 'gcp' AND param_key = 'google_client_id'").fetchone()
        conn.close()
        if row and row[0] and row[0].strip():
            client_id = row[0].strip()
    except Exception:
        pass
    return {
        "google_client_id": client_id,
        "auth_enabled": True,
        "trial_enabled": True,
        "trial_duration_days": 30
    }

@app.post("/api/auth/google")
def api_auth_google(payload: GoogleAuthPayload):
    """
    Verifies Google ID Token and logs the user in with 30-Day Scholar Pro Trial membership.
    """
    try:
        user_info = verify_google_id_token(payload.id_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = upsert_user(
        email=user_info["email"],
        full_name=user_info["name"],
        avatar_url=user_info["picture"],
        google_sub=user_info["google_sub"]
    )
    
    # Automatically provision 30-day Scholar Pro trial membership for Google SSO members
    trial_info = ensure_trial_subscription(user["id"], user["email"])
    
    is_admin = user.get("role") == "admin"
    is_curator = user.get("role") == "curator"
    has_sub = is_admin or is_curator or check_active_subscription(user["id"])
    
    user["has_active_sub"] = has_sub
    user["subscription_tier"] = "admin" if is_admin else ("curator" if is_curator else "trial_member")
    user["tier_name"] = "Super Administrator" if is_admin else ("Admin Curator" if is_curator else "Scholar Pro (30-Day Free Trial)")
    
    token = create_session_token(user)
    response = JSONResponse({
        "status": "success",
        "user": user,
        "token": token,
        "trial_info": trial_info
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    return response


# ----------------------------------------------------------------------------
# PASSWORDLESS MAGIC LINK AUTHENTICATION (Zero Passwords Captured/Stored)
# ----------------------------------------------------------------------------
magic_link_store: Dict[str, Dict[str, Any]] = {}

class MagicLinkRequest(BaseModel):
    email: str
    name: Optional[str] = None

class MagicLinkVerifyPayload(BaseModel):
    token: str

@app.post("/api/auth/magic-link/request")
def api_request_magic_link(payload: MagicLinkRequest):
    """
    Generates a secure, passwordless magic link token.
    No passwords are requested or stored.
    """
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    
    token = secrets.token_urlsafe(32)
    name = payload.name or email.split("@")[0].replace(".", " ").title()
    
    magic_link_store[token] = {
        "email": email,
        "name": name,
        "expires_at": time.time() + 900  # 15 minutes
    }
    
    return {
        "status": "success",
        "message": f"Secure sign-in link generated for {email}.",
        "email": email,
        "token": token,
        "verify_url": f"/api/auth/magic-link/verify?token={token}"
    }

@app.get("/api/auth/magic-link/verify")
def api_verify_magic_link_get(token: str):
    """Verifies magic link token from email link click and redirects to archive."""
    data = magic_link_store.get(token)
    if not data or data["expires_at"] < time.time():
        raise HTTPException(status_code=400, detail="Sign-in link is invalid or has expired. Please request a new link.")
    
    email = data["email"]
    name = data["name"]
    is_admin = email == "ananth.seetharaman@gmail.com"
    role = "admin" if is_admin else ("curator" if "curator" in email else "scholar")
    
    user = upsert_user(email=email, full_name=name, role=role)
    ensure_trial_subscription(user["id"], email)
    
    session_token = create_session_token(user)
    response = RedirectResponse(url="/#search", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    magic_link_store.pop(token, None)
    return response

@app.post("/api/auth/magic-link/verify")
def api_verify_magic_link_post(payload: MagicLinkVerifyPayload):
    """Verifies magic link token and establishes authenticated session with 30-Day Trial."""
    token = payload.token
    data = magic_link_store.get(token)
    if not data or data["expires_at"] < time.time():
        raise HTTPException(status_code=400, detail="Sign-in link is invalid or has expired.")
    
    email = data["email"]
    name = data["name"]
    is_admin = email == "ananth.seetharaman@gmail.com"
    role = "admin" if is_admin else ("curator" if "curator" in email else "scholar")
    
    user = upsert_user(email=email, full_name=name, role=role)
    trial_info = ensure_trial_subscription(user["id"], email)
    
    has_sub = is_admin or role == "curator" or check_active_subscription(user["id"])
    user["has_active_sub"] = has_sub
    user["subscription_tier"] = "admin" if is_admin else ("curator" if role == "curator" else "trial_member")
    user["tier_name"] = "Super Administrator" if is_admin else ("Admin Curator" if role == "curator" else "Scholar Pro (30-Day Free Trial)")
    
    session_token = create_session_token(user)
    response = JSONResponse({
        "status": "success",
        "user": user,
        "token": session_token,
        "trial_info": trial_info
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    magic_link_store.pop(token, None)
    return response

@app.post("/api/auth/demo-login")
def api_auth_demo_login(payload: DemoAuthPayload):
    """
    Facilitates 1-click Scholar, Curator, or Super Admin sign-in for testing.
    """
    if payload.role == "admin" or (payload.email and payload.email.lower() == "ananth.seetharaman@gmail.com"):
        email = "ananth.seetharaman@gmail.com"
        name = payload.name or "Ananth Seetharaman (Admin)"
        role = "admin"
        avatar = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80"
    elif payload.role == "curator":
        email = payload.email or "curator.ramanujam@fivemetalmasonry.com"
        name = payload.name or "Dr. K. Ramanujam (Curator)"
        role = "curator"
        avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80"
    elif payload.role == "trial" or (payload.email and "trial" in payload.email.lower()):
        email = payload.email or "scholar.trial@fmm-archive.org"
        name = payload.name or "Trial Scholar Member (Google SSO)"
        role = "scholar"
        avatar = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80"
    else:
        email = payload.email or "scholar.ananta@fmm-archive.org"
        name = payload.name or "Ananta (Visiting Scholar)"
        role = "scholar"
        avatar = "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80"

    user = upsert_user(
        email=email,
        full_name=name,
        avatar_url=avatar,
        role=role
    )
    
    # If trial role or Google SSO email, provision trial subscription
    if payload.role == "trial" or (payload.email and ("@" in payload.email and ("gmail" in payload.email.lower() or "trial" in payload.email.lower()))):
        ensure_trial_subscription(user["id"], user["email"])

    token = create_session_token(user)
    # Enrich user with subscription status
    is_admin = role == "admin"
    is_curator = role == "curator"
    has_sub = is_admin or is_curator or check_active_subscription(user.get("id", ""))
    user["has_active_sub"] = has_sub
    user["subscription_tier"] = "admin" if is_admin else ("curator" if is_curator else ("trial_member" if has_sub else "free"))
    user["tier_name"] = "Super Administrator" if is_admin else ("Admin Curator" if is_curator else ("Scholar Pro (30-Day Free Trial)" if has_sub else "Visiting Scholar (Free)"))
    response = JSONResponse({
        "status": "success",
        "user": user,
        "token": token
    })
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    return response

@app.get("/api/auth/me")
def api_auth_me(request: Request):
    """
    Returns the currently logged-in user profile.
    """
    user_payload = get_current_user_from_request(request)
    if not user_payload:
        return {"authenticated": False, "user": None}
    
    user_role = user_payload.get("role", "scholar")
    user_id = user_payload["sub"]
    # Admins and curators always have full access; scholars need active subscription
    has_sub = user_role in ("admin", "curator") or check_active_subscription(user_id)

    is_admin = user_role == "admin"
    is_curator = user_role == "curator"

    # Read the real subscription snapshot so the UI can reflect the actual tier,
    # payment status, and (for students) verification state.
    sub_tier = sub_status = verification_status = None
    if not (is_admin or is_curator):
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT tier, status, verification_status FROM user_subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            conn.close()
            if row:
                sub_tier, sub_status, verification_status = row[0], row[1], row[2]
        except Exception:
            pass

    if is_admin:
        tier, tier_name = "admin", "Super Administrator"
    elif is_curator:
        tier, tier_name = "curator", "Admin Curator"
    elif sub_status == "active" and sub_tier in ("student", "scholar_pro", "scholar"):
        tier = sub_tier
        tier_name = "Student Scholar (\u20b9350/mo)" if sub_tier == "student" else "Scholar (\u20b9750/mo)"
    elif has_sub:
        tier, tier_name = "trial_member", "Scholar Pro (Trial Member)"
    else:
        # Not yet active: could be a free visitor or a student pending/approved-unpaid
        tier = sub_tier if sub_tier else "free"
        tier_name = "Visiting Scholar (Free)"

    return {
        "authenticated": True,
        "user": {
            "id": user_id,
            "email": user_payload["email"],
            "full_name": user_payload["name"],
            "avatar_url": user_payload.get("avatar_url", ""),
            "role": user_role,
            "has_active_sub": has_sub,
            "subscription_tier": tier,
            "subscription_status": sub_status,
            "verification_status": verification_status,
            "tier_name": tier_name
        }
    }

@app.post("/api/auth/logout")
def api_auth_logout():
    """Logs out user and clears session cookie."""
    response = JSONResponse({"status": "success", "message": "Logged out successfully"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

# ----------------------------------------------------------------------------
# PAYMENT & SUBSCRIPTION ENDPOINTS (Razorpay)
# ----------------------------------------------------------------------------

class PaymentVerifyRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    tier: Optional[str] = "scholar"

class CreateOrderPayload(BaseModel):
    tier: str = "scholar"

def _resolve_paid_tier(tier: Optional[str]):
    """Maps a requested tier label to (tier_key, price_config_key, default_price_inr).

    The internal Scholar identifier remains `scholar_pro` for compatibility with
    existing rows and `check_active_subscription`.
    """
    t = (tier or "scholar").strip().lower()
    if t == "student":
        return "student", "student_monthly_inr", 350.0
    return "scholar_pro", "scholar_monthly_inr", 750.0

@app.post("/api/payment/create-order")
def api_create_order(request: Request, payload: Optional[CreateOrderPayload] = Body(default=None)):
    """Creates a Razorpay order for a Student (requires approval) or Scholar upgrade.

    Price is read from param_config (`student_monthly_inr` / `scholar_monthly_inr`).
    Student orders are rejected unless the applicant's ID proof is already approved.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized. Please sign in to upgrade.")

    tier_key, price_key, default_price = _resolve_paid_tier(payload.tier if payload else "scholar")

    conn = get_db()
    try:
        # Student is a proof-gated tier: require curator/admin approval before payment.
        if tier_key == "student":
            row = conn.execute(
                "SELECT verification_status FROM user_subscriptions WHERE user_id = ? LIMIT 1",
                (user["sub"],)
            ).fetchone()
            vstatus = (row[0] if row else None)
            if vstatus != "approved":
                raise HTTPException(
                    status_code=403,
                    detail="Your Student application must be approved by a curator before payment. Please submit your Student ID for review first."
                )

        price_raw = get_param(conn, price_key, str(default_price))
        try:
            amount_inr = float(price_raw)
        except Exception:
            amount_inr = default_price
    finally:
        conn.close()

    order = create_subscription_order(amount_inr, user["sub"], tier=tier_key)
    if "error" in order:
        raise HTTPException(status_code=500, detail=order["error"])

    from config import RAZORPAY_KEY_ID
    return {
        "order_id": order.get("id"),
        "amount": order.get("amount"),
        "currency": order.get("currency"),
        "key_id": RAZORPAY_KEY_ID,
        "tier": tier_key,
        "amount_inr": amount_inr
    }

@app.post("/api/payment/verify")
def api_verify_payment(payload: PaymentVerifyRequest, request: Request):
    """Verifies payment and activates the purchased tier (Student ₹350 / Scholar ₹750)."""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    is_valid = verify_payment_signature(
        payload.razorpay_payment_id,
        payload.razorpay_order_id,
        payload.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
        
    user_id = user["sub"]
    tier_key, price_key, default_price = _resolve_paid_tier(payload.tier)

    # Update Subscription in Database
    conn = get_db()
    try:
        price_raw = get_param(conn, price_key, str(default_price))
        try:
            amount_inr = float(price_raw)
        except Exception:
            amount_inr = default_price

        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        res = conn.execute("SELECT id FROM user_subscriptions WHERE user_id = ?", (user_id,)).fetchone()
        if res:
            conn.execute("""
                UPDATE user_subscriptions 
                SET tier = ?, status = 'active', payment_method = 'razorpay', 
                    verification_status = 'approved', billing_cycle = 'monthly',
                    last_payment_date = CURRENT_TIMESTAMP, 
                    next_billing_date = CURRENT_TIMESTAMP + INTERVAL 30 DAY,
                    amount_inr = ?
                WHERE user_id = ?
            """, (tier_key, amount_inr, user_id))
        else:
            conn.execute("""
                INSERT INTO user_subscriptions 
                (id, user_id, tier, status, billing_cycle, amount_inr, payment_method, verification_status, last_payment_date, next_billing_date) 
                VALUES (?, ?, ?, 'active', 'monthly', ?, 'razorpay', 'approved', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL 30 DAY)
            """, (sub_id, user_id, tier_key, amount_inr))

        tier_label = "Student" if tier_key == "student" else "Scholar"
        return {
            "status": "success",
            "tier": tier_key,
            "amount_inr": amount_inr,
            "message": f"Upgraded to {tier_label} (\u20b9{int(amount_inr)}/mo) successfully! All premium iconographs and unlimited PDF downloads are now active."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ----------------------------------------------------------------------------
# 1. SCHOLAR SEARCH & DISCOVERY ENDPOINTS
# ----------------------------------------------------------------------------

@app.get("/api/search")
def api_search(
    request: Request,
    q: Optional[str] = Query(None, description="Scholar query"),
    series_id: Optional[int] = Query(None, description="Series ID filter"),
    divinity: Optional[str] = Query(None, description="Divinity filter"),
    element: Optional[str] = Query(None, description="Iconographic element filter"),
    access_level: Optional[str] = Query(None, description="Access level: public, member_only, all"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    from database import log_behavior
    user = get_current_user_from_request(request)
    log_behavior(
        user_id=user["sub"] if user else None,
        event_type="search_query",
        payload=f"q={q}&series={series_id}&divinity={divinity}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return scholar_search(
        query=q,
        series_id=series_id,
        divinity=divinity,
        element=element,
        access_level=access_level,
        limit=limit,
        offset=offset
    )

@app.get("/api/autocomplete")
def api_autocomplete(q: str = Query(..., min_length=1)):
    return get_autocomplete(prefix=q, limit=8)

@app.get("/api/collections")
def api_get_collections(request: Request):
    """
    Public Collections Showcase endpoint themed after fivemetalmasonry.com/collections.
    Returns all curated sacred bronze studies with metadata, plate count, tala ratio, and role access info.
    """
    user = get_current_user_from_request(request)
    user_role = user.get("role") if user else "guest"
    user_email = user.get("email") if user else None
    
    conn = get_db()
    
    # Check user subscription
    has_active_sub = False
    if user and user.get("sub"):
        sub = conn.execute("""
            SELECT COUNT(*) FROM user_subscriptions
            WHERE user_id = ? AND status = 'active'
              AND (next_billing_date IS NULL OR next_billing_date >= CURRENT_TIMESTAMP);
        """, (user.get("sub"),)).fetchone()
        if sub and sub[0] > 0:
            has_active_sub = True

    studies = conn.execute("""
        SELECT s.id, s.slug, s.title, s.subtitle, s.study_number,
               ser.id AS series_id, ser.name AS series_name, s.access_level,
               s.summary_markdown, s.cover_image_url, s.total_slides,
               s.created_at
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        ORDER BY s.study_number ASC, s.id ASC;
    """).fetchall()
    
    collections_list = []
    for st in studies:
        sid, slug, title, subtitle, study_num, ser_id, ser_name, access_level, summary, cover_img, total_slides, created_at = st
        is_free_study = (sid == "s_ganesa_001" or slug == "ganesa-variations-in-iconography" or access_level == "public")
        
        can_access = is_free_study or user_role in ["admin", "curator"] or has_active_sub
        
        # Determine theme collection tag based on divinity/subject
        theme_tag = "Masterpieces"
        lower_title = f"{title} {subtitle} {ser_name}".lower()
        if "ganesa" in lower_title or "ganapati" in lower_title:
            theme_tag = "Ganesha Collection"
        elif "nataraja" in lower_title or "shiva" in lower_title or "tandava" in lower_title:
            theme_tag = "Nataraja & Shiva Icons"
        elif "krishna" in lower_title or "radha" in lower_title or "venugopala" in lower_title:
            theme_tag = "Krishna & Vaishnava"
        elif "devi" in lower_title or "amman" in lower_title or "parvati" in lower_title or "durga" in lower_title:
            theme_tag = "Devi & Amman Sacred Bronzes"
        elif "temple" in lower_title or "chola" in lower_title or "arch" in lower_title:
            theme_tag = "Temple Archival Classics"

        collections_list.append({
            "id": sid,
            "slug": slug,
            "title": title,
            "subtitle": subtitle or "",
            "study_number": study_num or "Study 001",
            "series_id": ser_id,
            "series_name": ser_name,
            "theme_tag": theme_tag,
            "access_level": access_level,
            "is_public": is_free_study,
            "can_access": can_access,
            "summary": summary,
            "cover_image_url": cover_img or "/assets/shilpa_shastra_iconography.jpg",
            "total_slides": total_slides or 0
        })

    conn.close()
    return {
        "status": "success",
        "total_collections": len(collections_list),
        "user_role": user_role,
        "has_active_sub": has_active_sub,
        "collections": collections_list
    }

@app.get("/api/studies/{study_id}")
def api_get_study(study_id: str, request: Request):
    from database import log_behavior
    user = get_current_user_from_request(request)
    log_behavior(
        user_id=user["sub"] if user else None,
        event_type="study_view",
        resource_id=study_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    conn = get_db()
    study = conn.execute("""
        SELECT s.id, s.slug, s.title, s.subtitle, s.study_number,
               ser.name AS series_name, s.access_level, s.summary_markdown,
               s.cover_image_url, s.total_slides, ser.id AS series_id
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        WHERE s.id = ? OR s.slug = ?
    """, (study_id, study_id)).fetchone()

    if not study:
        conn.close()
        raise HTTPException(status_code=404, detail="Iconograph study not found")

    sid = study[0]
    slug = study[1]

    # Non-Premium Rule: Free scholars get Study 001 (s_ganesa_001) or public studies.
    # Other studies are reserved for Student / Scholar members or Admin/Curator staff.
    user_role = user.get("role") if user else "guest"
    user_email = user.get("email") if user else None
    is_free_study = (sid == "s_ganesa_001" or slug == "ganesa-variations-in-iconography" or study[6] == "public")
    is_staff = user_role in ["admin", "curator"]

    has_premium_access = False
    trial_limit_reached = False
    study_limit = 3
    if is_free_study or is_staff:
        has_premium_access = True
    elif user_email:
        # Check if user purchased this study or has an active subscription
        paid = conn.execute("""
            SELECT COUNT(*) FROM premium_download_requests 
            WHERE LOWER(user_email) = LOWER(?) AND (study_id = ? OR status = 'approved' OR status = 'completed');
        """, (user_email, sid)).fetchone()
        sub = conn.execute("""
            SELECT tier FROM user_subscriptions
            WHERE user_id = ? AND status = 'active'
              AND (next_billing_date IS NULL OR next_billing_date >= CURRENT_TIMESTAMP)
            LIMIT 1;
        """, (user.get("sub", ""),)).fetchone()
        has_paid = bool(paid and paid[0] > 0)
        sub_tier = sub[0] if sub else None

        if has_paid:
            has_premium_access = True
        elif sub_tier in ("trial_member", "trial"):
            # Free trial: cap on the number of DISTINCT premium studies viewable.
            try:
                study_limit = int(float(get_param(conn, "trial_study_limit", "3") or 3))
            except Exception:
                study_limit = 3
            # The current study_view was already logged at the top of this handler,
            # so this count includes the study being opened now.
            distinct_premium = conn.execute("""
                SELECT COUNT(DISTINCT st.id)
                FROM user_behavior_logs bl
                JOIN studies st ON (bl.resource_id = st.id OR bl.resource_id = st.slug)
                WHERE bl.user_id = ?
                  AND bl.event_type = 'study_view'
                  AND st.access_level != 'public'
                  AND st.id != 's_ganesa_001';
            """, (user.get("sub", ""),)).fetchone()
            viewed = distinct_premium[0] if distinct_premium else 0
            if study_limit <= 0 or viewed <= study_limit:
                has_premium_access = True
            else:
                trial_limit_reached = True
        elif sub_tier:
            # Paid Student / Scholar tiers: full access
            has_premium_access = True

    if not has_premium_access:
        # Explicit per-plate public picks WIN: if the study has any is_public plates,
        # expose exactly those and ignore the global preview count. Otherwise fall back
        # to the admin-configurable global preview (count + first/latest).
        all_slides = conn.execute("""
            SELECT id, slide_number, slide_title, image_url, thumbnail_url,
                   caption, extracted_ocr_text, cleaned_text, visual_elements_summary, is_public
            FROM study_slides
            WHERE study_id = ?
            ORDER BY slide_number ASC
        """, (sid,)).fetchall()

        explicit = [sl for sl in all_slides if sl[9]]
        if explicit:
            subset = explicit
            preview_basis = "explicit"
        else:
            try:
                prev_count = int(float(get_param(conn, "guest_slide_preview_count", "2") or 2))
            except Exception:
                prev_count = 2
            prev_mode = (get_param(conn, "guest_slide_preview_mode", "latest") or "latest").strip().lower()
            if prev_count > 0:
                subset = all_slides[-prev_count:] if prev_mode == "latest" else all_slides[:prev_count]
            else:
                subset = []
            preview_basis = "global"

        preview_slides = [
            {
                "id": sl[0],
                "slide_number": sl[1],
                "slide_title": sl[2],
                "image_url": sl[3],
                "thumbnail_url": sl[4],
                "caption": sl[5],
                "raw_ocr": sl[6],
                "cleaned_text": sl[7],
                "summary": sl[8],
                "is_public": bool(sl[9])
            } for sl in subset
        ]
        conn.close()

        if trial_limit_reached:
            lock_title = "Free Trial Study Limit Reached"
            lock_message = (
                f"Your free trial includes full access to {study_limit} premium studies "
                "(plus all public studies, the Dictionary, and Search). Upgrade to "
                "Student (\u20b9350/mo) or Scholar (\u20b9750/mo) to unlock the complete archive."
            )
        else:
            lock_title = "Scholar Iconograph Access"
            lock_message = (
                "The free scholar access includes full study plates and OCR for Study 001 "
                "(Ganesa Variations in Iconography) along with Dictionary and Search. To unlock "
                "full multi-slide plates, high-res details, and OCR taxonomy for this iconograph, "
                "upgrade to Student (\u20b9350/mo) or Scholar (\u20b9750/mo)."
            )
        return {
            "id": study[0],
            "slug": study[1],
            "title": study[2],
            "subtitle": study[3],
            "study_number": study[4],
            "series_name": study[5],
            "access_level": study[6],
            "summary": study[7],
            "cover_image_url": study[8],
            "total_slides": study[9],
            "series_id": study[10],
            "is_premium_locked": True,
            "trial_limit_reached": trial_limit_reached,
            "lock_title": lock_title,
            "lock_message": lock_message,
            "is_preview": len(preview_slides) > 0,
            "preview_count": len(preview_slides),
            "preview_basis": preview_basis,
            "slides": preview_slides,
            "taxonomy": []
        }

    # Fetch all slides
    slides = conn.execute("""
        SELECT id, slide_number, slide_title, image_url, thumbnail_url,
               caption, extracted_ocr_text, cleaned_text, visual_elements_summary, is_public
        FROM study_slides
        WHERE study_id = ?
        ORDER BY slide_number ASC
    """, (sid,)).fetchall()

    # Fetch taxonomy mappings
    mappings = conn.execute("""
        SELECT t.canonical_name, t.iast_name, tt.name AS category,
               m.relevance_level, m.slide_numbers
        FROM study_taxonomy_mappings m
        JOIN taxonomy_terms t ON m.term_id = t.id
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        WHERE m.study_id = ?
    """, (sid,)).fetchall()

    conn.close()

    return {
        "id": study[0],
        "slug": study[1],
        "title": study[2],
        "subtitle": study[3],
        "study_number": study[4],
        "series_name": study[5],
        "access_level": study[6],
        "summary": study[7],
        "cover_image_url": study[8],
        "total_slides": study[9],
        "series_id": study[10],
        "slides": [
            {
                "id": sl[0],
                "slide_number": sl[1],
                "slide_title": sl[2],
                "image_url": sl[3],
                "thumbnail_url": sl[4],
                "caption": sl[5],
                "raw_ocr": sl[6],
                "cleaned_text": sl[7],
                "summary": sl[8],
                "is_public": bool(sl[9])
            } for sl in slides
        ],
        "taxonomy": [
            {
                "term": m[0],
                "iast": m[1],
                "category": m[2],
                "relevance": m[3],
                "slides": m[4]
            } for m in mappings
        ]
    }

@app.get("/api/studies/{study_id}/pdf")
def api_download_study_pdf(study_id: str, request: Request):
    """
    Default Download as PDF action for iconograph studies.
    Enforces download quotas:
      - Public Studies: Free direct download for all visitors and scholars
      - Member-only Studies / Free Trial: Exactly 1 download permitted across trial period
      - Student (₹350/mo) / Scholar Pro (₹750/mo) / Admin: Unlimited downloads
    """
    user = get_current_user_from_request(request)
    user_id = user.get("sub", "guest") if user else "guest"
    user_email = user.get("email", "Visiting Scholar / Guest") if user else "Visiting Scholar / Guest"
    conn = get_db()

    # 1. Fetch study data
    study = conn.execute("""
        SELECT s.id, s.slug, s.title, s.subtitle, s.study_number,
               ser.name AS series_name, s.access_level, s.summary_markdown,
               s.cover_image_url, s.total_slides
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        WHERE s.id = ? OR s.slug = ?
    """, (study_id, study_id)).fetchone()

    if not study:
        conn.close()
        raise HTTPException(status_code=404, detail="Iconograph study not found")

    sid, slug, title, subtitle, study_num, ser_name, access_level, summary, cover_img, total_slides = study

    # 2. Check access permissions
    is_public = (access_level == "public" or sid == "s_ganesa_001" or slug == "ganesa-variations-in-iconography")
    if not is_public:
        if not user:
            conn.close()
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please sign in or activate your 15-day Free Trial to download research iconograph PDFs."
            )

        user_role = user.get("role", "scholar")
        is_staff = user_role in ["admin", "curator"]

        if not is_staff:
            sub_row = conn.execute("""
                SELECT tier, status FROM user_subscriptions 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,)).fetchone()
            
            sub_tier = sub_row[0] if sub_row else "free"
            
            if sub_tier in ["trial_member", "trial", "free"]:
                try:
                    dl_limit = int(float(get_param(conn, "trial_download_limit", "1") or 1))
                except Exception:
                    dl_limit = 1
                dl_count = conn.execute("""
                    SELECT COUNT(DISTINCT study_id) FROM user_downloads WHERE user_id = ?;
                """, (user_id,)).fetchone()[0]

                if dl_count >= dl_limit:
                    conn.close()
                    raise HTTPException(
                        status_code=403,
                        detail=f"Free Trial download quota reached ({dl_limit} download limit). Upgrade to Student (\u20b9350/month) or Scholar (\u20b9750/month) for unlimited 300 DPI PDF downloads."
                    )

    # Fetch all slides
    slides = conn.execute("""
        SELECT id, slide_number, slide_title, image_url, thumbnail_url,
               caption, extracted_ocr_text, cleaned_text, visual_elements_summary
        FROM study_slides
        WHERE study_id = ?
        ORDER BY slide_number ASC
    """, (sid,)).fetchall()

    # Fetch taxonomy mappings
    mappings = conn.execute("""
        SELECT t.canonical_name, t.iast_name, tt.name AS category,
               m.relevance_level, m.slide_numbers
        FROM study_taxonomy_mappings m
        JOIN taxonomy_terms t ON m.term_id = t.id
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        WHERE m.study_id = ?
    """, (sid,)).fetchall()

    # Record download log
    dl_id = f"dl_{uuid.uuid4().hex[:10]}"
    try:
        conn.execute("""
            INSERT INTO user_downloads (id, user_id, study_id, license_ref, resolution, downloaded_at)
            VALUES (?, ?, ?, 'pdf_export', '300dpi_master', CURRENT_TIMESTAMP);
        """, (dl_id, user_id, sid))
    except Exception:
        pass
    conn.close()

    study_dict = {
        "id": sid,
        "slug": slug,
        "title": title,
        "subtitle": subtitle,
        "study_number": study_num,
        "series_name": ser_name,
        "access_level": access_level,
        "summary": summary,
        "cover_image_url": cover_img,
        "slides": [
            {
                "slide_number": sl[1],
                "slide_title": sl[2],
                "image_url": sl[3],
                "caption": sl[5],
                "raw_ocr": sl[6],
                "cleaned_text": sl[7]
            } for sl in slides
        ],
        "taxonomy": [
            {
                "term": m[0],
                "iast": m[1],
                "category": m[2]
            } for m in mappings
        ]
    }

    pdf_buffer = generate_study_pdf(study_dict, user_email=user_email)
    safe_filename = f"{slug or 'study'}_fmm_iconograph.pdf"

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Download-License": dl_id
        }
    )

@app.get("/api/series/{series_id}/pdf")
def api_download_series_pdf(series_id: str, request: Request):
    """
    Download an entire curatorial series as a single images-only PDF:
    every plate image from every study in the series, one image per page,
    ordered by study number then slide number. No text or templates.
    """
    user = get_current_user_from_request(request)
    user_role = user.get("role", "guest") if user else "guest"
    conn = get_db()

    series = conn.execute(
        "SELECT id, name FROM series WHERE id = ?", (series_id,)
    ).fetchone()
    if not series:
        conn.close()
        raise HTTPException(status_code=404, detail="Series not found")
    ser_id, ser_name = series[0], series[1]

    # Access: staff or active subscribers may export a full series bundle.
    is_staff = user_role in ["admin", "curator"]
    has_sub = False
    if user and user.get("sub"):
        sub = conn.execute("""
            SELECT COUNT(*) FROM user_subscriptions
            WHERE user_id = ? AND status = 'active'
              AND (next_billing_date IS NULL OR next_billing_date >= CURRENT_TIMESTAMP);
        """, (user.get("sub"),)).fetchone()
        has_sub = bool(sub and sub[0] > 0)

    if not (is_staff or has_sub):
        conn.close()
        raise HTTPException(
            status_code=403,
            detail=("Full-series PDF export is available to Student (\u20b9350/mo) or "
                    "Scholar (\u20b9750/mo) members. Individual public studies remain free to download.")
        )

    rows = conn.execute("""
        SELECT ss.image_url
        FROM studies s
        JOIN study_slides ss ON ss.study_id = s.id
        WHERE s.series_id = ?
        ORDER BY s.study_number ASC, s.id ASC, ss.slide_number ASC
    """, (ser_id,)).fetchall()
    conn.close()

    image_urls = [r[0] for r in rows if r[0]]
    if not image_urls:
        raise HTTPException(status_code=404, detail="No plate images found for this series.")

    pdf_buffer = generate_image_only_pdf(image_urls)

    safe = (ser_name or "series").lower().replace(" ", "_").replace("&", "and")
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in ("_", "-")) or "series"

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}_series_plates.pdf"'}
    )

@app.get("/api/taxonomy/hierarchy")
def api_taxonomy_hierarchy():
    conn = get_db()
    series = conn.execute("SELECT id, slug, name, scope, status FROM series ORDER BY sort_order ASC").fetchall()
    categories = conn.execute("SELECT id, code, name FROM taxonomy_types ORDER BY id ASC").fetchall()
    terms = conn.execute("""
        SELECT t.id, t.canonical_name, t.iast_name, t.slug, tt.code, t.parent_id
        FROM taxonomy_terms t
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        WHERE t.is_active = TRUE
        ORDER BY t.display_order ASC
    """).fetchall()
    dictionary = conn.execute("SELECT id, slug, headword, iast_headword, part_of_speech, definition FROM dictionary_entries").fetchall()
    conn.close()

    return {
        "series": [{"id": s[0], "slug": s[1], "name": s[2], "scope": s[3], "status": s[4]} for s in series],
        "categories": [{"id": c[0], "code": c[1], "name": c[2]} for c in categories],
        "terms": [{"id": t[0], "name": t[1], "iast": t[2], "slug": t[3], "category": t[4], "parent_id": t[5]} for t in terms],
        "dictionary": [{"id": d[0], "slug": d[1], "headword": d[2], "iast": d[3], "pos": d[4], "definition": d[5]} for d in dictionary]
    }

# ----------------------------------------------------------------------------
# 1.1 STUDENT MEMBERSHIP VERIFICATION & ONBOARDING WORKFLOW
# ----------------------------------------------------------------------------

@app.post("/api/membership/student-apply")
async def api_student_apply(
    request: Request,
    institution_name: str = Form(...),
    proof_file: UploadFile = File(...)
):
    """
    Onboarding: Student Tier application (₹350/mo).
    Requires institutional ID / student proof upload.
    Places subscription into 'pending_approval' for curator/admin review.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in before applying.")

    user_id = user["sub"]
    user_email = user.get("email", "")

    # Save student ID proof
    clean_fn = f"proof_{user_id}_{uuid.uuid4().hex[:6]}_{proof_file.filename}"
    proof_path = STUDENT_PROOFS_DIR / clean_fn
    with open(proof_path, "wb") as buf:
        shutil.copyfileobj(proof_file.file, buf)

    rel_proof_url = f"/storage/student_proofs/{clean_fn}"

    conn = get_db()
    existing = conn.execute("SELECT id FROM user_subscriptions WHERE user_id = ?", (user_id,)).fetchone()
    sub_id = existing[0] if existing else f"sub_std_{uuid.uuid4().hex[:8]}"

    if existing:
        conn.execute("""
            UPDATE user_subscriptions
            SET tier = 'student', status = 'pending_approval', verification_status = 'pending',
                institution_name = ?, id_proof_url = ?, amount_inr = 350.0,
                billing_cycle = 'monthly'
            WHERE id = ?;
        """, (institution_name, rel_proof_url, sub_id))
    else:
        conn.execute("""
            INSERT INTO user_subscriptions (
                id, user_id, tier, status, verification_status, institution_name,
                id_proof_url, amount_inr, billing_cycle, payment_method
            ) VALUES (?, ?, 'student', 'pending_approval', 'pending', ?, ?, 350.0, 'monthly', 'student_proof');
        """, (sub_id, user_id, institution_name, rel_proof_url))

    conn.close()

    return {
        "status": "success",
        "message": "Student ID submitted successfully! Your ₹350/mo Student tier application is currently under Curator review.",
        "subscription_id": sub_id,
        "tier": "student",
        "verification_status": "pending"
    }

@app.get("/api/admin/student-applications")
def api_get_student_applications(request: Request):
    """
    Admin & Curator review queue for submitted student IDs.
    """
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["admin", "curator"]:
        raise HTTPException(status_code=403, detail="Forbidden: Reserved for Administrators and Curators.")

    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.user_id, u.full_name, u.email, s.institution_name,
               s.id_proof_url, s.verification_status, s.status, s.amount_inr,
               s.created_at, s.verified_by, s.verified_at
        FROM user_subscriptions s
        LEFT JOIN users u ON s.user_id = u.id
        WHERE s.tier = 'student'
        ORDER BY s.created_at DESC;
    """).fetchall()
    conn.close()

    apps = []
    for r in rows:
        apps.append({
            "id": r[0],
            "user_id": r[1],
            "full_name": r[2] or "Scholar Applicant",
            "email": r[3] or "N/A",
            "institution_name": r[4] or "Academic Institution",
            "id_proof_url": r[5],
            "verification_status": r[6] or "pending",
            "status": r[7],
            "amount_inr": r[8] or 350.0,
            "created_at": str(r[9]),
            "verified_by": r[10],
            "verified_at": str(r[11]) if r[11] else None
        })

    return {"status": "success", "count": len(apps), "applications": apps}

class StudentReviewPayload(BaseModel):
    action: str  # 'approve' or 'reject'
    notes: Optional[str] = None

@app.post("/api/admin/student-applications/{sub_id}/review")
def api_review_student_application(sub_id: str, payload: StudentReviewPayload, request: Request):
    """
    Admin & Curator endpoint to approve or reject student ID application.
    """
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["admin", "curator"]:
        raise HTTPException(status_code=403, detail="Forbidden: Reserved for Administrators and Curators.")

    action = payload.action.strip().lower()
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    conn = get_db()
    sub = conn.execute("SELECT id, user_id FROM user_subscriptions WHERE id = ?", (sub_id,)).fetchone()
    if not sub:
        conn.close()
        raise HTTPException(status_code=404, detail="Subscription application not found")

    reviewer_email = user.get("email", "admin@fivemetalmasonry.com")

    if action == "approve":
        # Approval verifies eligibility but does NOT grant access; the applicant must
        # then pay the Student price to activate (status flips to 'active' on payment).
        conn.execute("""
            UPDATE user_subscriptions
            SET verification_status = 'approved',
                status = 'approved',
                verified_by = ?,
                verified_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (reviewer_email, sub_id))
        msg = "Student application approved. The applicant can now pay \u20b9350/mo to activate Student access."
    else:
        conn.execute("""
            UPDATE user_subscriptions
            SET verification_status = 'rejected',
                status = 'rejected',
                verified_by = ?,
                verified_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (reviewer_email, sub_id))
        msg = "Student application rejected."

    conn.close()
    return {"status": "success", "message": msg, "action": action, "sub_id": sub_id}

# ----------------------------------------------------------------------------
# 2. OCR INGESTION & VISUAL APPROVAL STUDIO (ROUTE GUARDED)
# ----------------------------------------------------------------------------

@app.post("/api/ocr/upload")
async def api_ocr_upload(
    request: Request,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    study_slug: str = Form("ganesa-variations-in-iconography"),
    engine: str = Form("gemini_vision")
):
    """
    Guarded route: Multi-file / single-file OCR ingestion for series.
    Requires authenticated Curator or Admin session.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an authorized Curator or Administrator Google account to upload slides."
        )
    if user.get("role") not in ["curator", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Visiting Scholar accounts lack Curator ingestion permissions."
        )

    target_dir = IMAGES_STORAGE_DIR / study_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    # Collect all uploaded files
    upload_list = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="No image file(s) provided for OCR ingestion.")

    results = []
    for f in upload_list:
        safe_filename = f"upload_{uuid.uuid4().hex[:6]}_{f.filename}"
        file_path = target_dir / safe_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        # 1. Gemini Iconography / Shilpa Shastra Domain Validation Guard
        is_valid, validation_reason = validate_iconography_image(str(file_path))
        if not is_valid:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=400,
                detail=f"Upload rejected for '{f.filename}': Image is not related to Shilpa Shastra or sacred iconography. {validation_reason}"
            )

        # 2. Dispatch Dual-Engine OCR (Gemini Vision Default / Windows Native)
        raw_ocr, cleaned_ocr, engine_used = perform_ocr(str(file_path), engine=engine)
        if not raw_ocr:
            raw_ocr = "ICONOGRAPHY SAMPLE EXTRACTED TEXT"
            cleaned_ocr = clean_ocr_text(raw_ocr)

        # 3. Layer 2 Entity Extraction
        proposals = extract_candidate_proposals(cleaned_ocr)
        rel_url = f"/storage/images/{study_slug}/{safe_filename}"

        results.append({
            "filename": safe_filename,
            "original_filename": f.filename,
            "image_url": rel_url,
            "engine_used": engine_used,
            "raw_ocr": raw_ocr,
            "cleaned_ocr": cleaned_ocr,
            "word_count": len(cleaned_ocr.split()),
            "proposals": proposals
        })

    # Backward compatible return: single slide fields at root + uploaded_slides array
    first_res = results[0]
    return {
        "filename": first_res["filename"],
        "image_url": first_res["image_url"],
        "engine_used": first_res["engine_used"],
        "raw_ocr": first_res["raw_ocr"],
        "cleaned_ocr": first_res["cleaned_ocr"],
        "word_count": first_res["word_count"],
        "proposals": first_res["proposals"],
        "uploaded_slides": results,
        "total_uploaded": len(results)
    }

@app.get("/api/ocr/context")
def api_ocr_context():
    """
    Returns available studies, series, and taxonomy categories for OCR Studio.
    """
    return get_ocr_context()

class CreateStudyRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None
    series_id: int = 1
    access_level: Optional[str] = "member_only"

@app.post("/api/ocr/studies/create")
def api_ocr_create_study(req: CreateStudyRequest, request: Request):
    """
    Guarded route: Creates a new study iconograph linked to a valid series_id.
    Default access level is member_only.
    """
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["curator", "admin"]:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an authorized Curator or Administrator account."
        )
    try:
        new_study = create_new_study(
            title=req.title,
            subtitle=req.subtitle,
            series_id=req.series_id,
            access_level=req.access_level or "public"
        )
        return {"status": "success", "study": new_study}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class CreateSeriesRequest(BaseModel):
    name: str
    scope: Optional[str] = None

@app.post("/api/ocr/series/create")
def api_ocr_create_series(req: CreateSeriesRequest, request: Request):
    """
    Guarded route: Creates a new editorial series.
    """
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["curator", "admin"]:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an authorized Curator or Administrator account."
        )
    try:
        new_series = create_new_series(name=req.name, scope=req.scope)
        return {"status": "success", "series": new_series}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class ApproveSlideRequest(BaseModel):
    study_id: str
    slide_number: Optional[int] = None
    slide_title: str
    image_url: str
    raw_ocr: str
    cleaned_ocr: str
    approved_proposals: List[Dict[str, Any]]
    ocr_engine: Optional[str] = LLM_MODEL
    is_public: bool = False
    study_title: Optional[str] = None
    study_number: Optional[str] = None
    access_level: Optional[str] = "member_only"

class ApproveBatchRequest(BaseModel):
    slides: List[ApproveSlideRequest]

@app.post("/api/ocr/approve")
def api_ocr_approve(req: ApproveSlideRequest, request: Request):
    """
    Guarded route: Commits reviewed slide into DuckDB and returns the detailed 'List of Tables Impacted'.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an authorized Curator or Administrator Google account to approve slides."
        )
    if user.get("role") not in ["curator", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only Curators or Administrators can commit changes to the archive taxonomy."
        )

    return commit_curator_approval(
        study_id=req.study_id,
        slide_number=req.slide_number,
        slide_title=req.slide_title,
        image_rel_url=req.image_url,
        raw_ocr=req.raw_ocr,
        cleaned_ocr=req.cleaned_ocr,
        approved_proposals=req.approved_proposals,
        ocr_engine=req.ocr_engine or LLM_MODEL,
        is_public=req.is_public,
        study_title=req.study_title,
        study_number=req.study_number,
        access_level=req.access_level or "member_only"
    )

@app.post("/api/ocr/approve-batch")
def api_ocr_approve_batch(req: ApproveBatchRequest, request: Request):
    """
    Guarded route: Commits multiple reviewed slides into DuckDB in batch for a study.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an authorized Curator or Administrator Google account to approve slides."
        )
    if user.get("role") not in ["curator", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only Curators or Administrators can commit changes to the archive taxonomy."
        )

    if not req.slides:
        raise HTTPException(status_code=400, detail="No slides provided in batch request.")

    committed_slides = []
    combined_tables_impacted = {}
    
    for s in req.slides:
        res = commit_curator_approval(
            study_id=s.study_id,
            slide_number=s.slide_number,
            slide_title=s.slide_title,
            image_rel_url=s.image_url,
            raw_ocr=s.raw_ocr,
            cleaned_ocr=s.cleaned_ocr,
            approved_proposals=s.approved_proposals,
            ocr_engine=s.ocr_engine or LLM_MODEL,
            is_public=s.is_public,
            study_title=s.study_title,
            study_number=s.study_number,
            access_level=s.access_level or "member_only"
        )
        committed_slides.append({
            "slide_id": res.get("slide_id"),
            "effective_slide_number": res.get("effective_slide_number"),
            "image_url": res.get("image_url")
        })
        for item in res.get("tables_impacted", []):
            tbl = item["table_name"]
            if tbl not in combined_tables_impacted:
                combined_tables_impacted[tbl] = {
                    "table_name": tbl,
                    "operation": item["operation"],
                    "rows_impacted": 0
                }
            combined_tables_impacted[tbl]["rows_impacted"] += item["rows_impacted"]

    tables_impacted_list = [
        {
            "table_name": v["table_name"],
            "operation": v["operation"],
            "rows_impacted": v["rows_impacted"],
            "description": f"{v['rows_impacted']} records committed across {len(req.slides)} plate(s)"
        }
        for v in combined_tables_impacted.values()
    ]

    distinct_studies = {s.study_id for s in req.slides}
    return {
        "status": "success",
        "message": f"Successfully ingested {len(committed_slides)} plate(s) across {len(distinct_studies)} study/studies.",
        "total_slides_ingested": len(committed_slides),
        "total_studies": len(distinct_studies),
        "slides": committed_slides,
        "tables_impacted": tables_impacted_list
    }

class InferGroupsPlate(BaseModel):
    index: int
    slide_number: Optional[int] = None
    slide_title: Optional[str] = None
    raw_ocr: Optional[str] = ""
    cleaned_ocr: Optional[str] = ""
    image_url: Optional[str] = None

class InferGroupsRequest(BaseModel):
    series_id: Optional[int] = None
    plates: List[InferGroupsPlate]

@app.post("/api/ocr/infer-groups")
def api_ocr_infer_groups(req: InferGroupsRequest, request: Request):
    """
    Curator-guarded: infer how a bulk batch of plates groups into studies.
    Header-primary (TOC optional), attaching to existing studies in the series.
    Gemini when reachable, deterministic heuristic fallback otherwise.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to infer study groupings.")
    if user.get("role") not in ["curator", "admin"]:
        raise HTTPException(status_code=403, detail="Forbidden: Only Curators or Administrators can run study grouping.")

    if not req.plates:
        raise HTTPException(status_code=400, detail="No plates provided for grouping.")

    plates = [p.dict() for p in req.plates]
    return infer_study_groupings(series_id=req.series_id, plates=plates)


# ----------------------------------------------------------------------------
# 3. ARCHIVE DATA STUDIO & ROW EXPLORER (ROUTE GUARDED - ADMIN ONLY)
# ----------------------------------------------------------------------------

class UpdateUserRolePayload(BaseModel):
    email: str
    role: str
    full_name: Optional[str] = None

@app.post("/api/admin/users/role")
def api_admin_update_role(payload: UpdateUserRolePayload, request: Request):
    """
    Super Admin endpoint to grant or modify user roles (admin, curator, scholar).
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only System Administrators can modify user roles.")
    
    clean_email = payload.email.strip().lower()
    clean_role = payload.role.strip().lower()
    if clean_role not in ["admin", "curator", "scholar"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'curator', or 'scholar'.")
    
    conn = get_db()
    existing = conn.execute("SELECT id, full_name FROM users WHERE LOWER(email) = ?;", (clean_email,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET role = ? WHERE LOWER(email) = ?;", (clean_role, clean_email))
        target_name = existing[1]
    else:
        new_id = f"usr_{uuid.uuid4().hex[:10]}"
        target_name = payload.full_name or clean_email.split('@')[0].capitalize()
        conn.execute("""
            INSERT INTO users (id, email, full_name, avatar_url, role)
            VALUES (?, ?, ?, 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80', ?);
        """, (new_id, clean_email, target_name, clean_role))
    
    conn.close()
    return {
        "status": "success",
        "message": f"User '{clean_email}' successfully assigned to '{clean_role}' role.",
        "email": clean_email,
        "role": clean_role
    }


@app.get("/api/archival/telemetry")
def api_archival_telemetry():
    """
    Public route: Returns summary statistics and live table row counts 
    across the 4-tier data architecture for Data Studio telemetry.
    """
    conn = get_db()
    tables = conn.execute("SHOW TABLES;").fetchall()
    table_stats = {}
    for t in tables:
        tname = t[0]
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            table_stats[tname] = count
        except Exception:
            table_stats[tname] = 0
    
    return {
        "status": "success",
        "engine": "duckdb",
        "total_tables": len(tables),
        "tables": table_stats
    }

@app.get("/api/admin/tables")

def api_list_tables(request: Request):
    """
    Guarded route: Lists all archive database tables and row counts.
    Restricted strictly to Administrator role (Curators access Visual OCR Studio only).
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an Administrator account."
        )
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Data Studio is reserved for System Administrators. Curators have access to the Visual OCR Studio."
        )

    conn = get_db()
    tables = conn.execute("SHOW TABLES;").fetchall()
    table_stats = []
    
    # Categorization mapping for organized browsing
    def get_table_category(tname):
        if tname in ["studies", "study_slides", "series", "slide_ocr_data"]:
            return "core", "Core Content", 1
        elif tname in ["taxonomy_terms", "taxonomy_types", "term_aliases", "study_taxonomy_mappings", "ai_metadata_proposals", "dictionary_entries"]:
            return "taxonomy", "Controlled Taxonomy", 2
        elif tname in ["places", "periods_dynasties"]:
            return "geography", "Geography & Eras", 3
        elif tname in ["users", "user_subscriptions", "user_downloads", "user_behavior_logs", "content_access_rules", "premium_download_requests"]:
            return "telemetry", "Access & Telemetry", 4
        return "system", "Internal Schema", 5

    for t in tables:
        tname = t[0]
        count_res = conn.execute(f"SELECT COUNT(*) FROM {tname};").fetchone()
        row_count = count_res[0] if count_res else 0
        cols = conn.execute(f"PRAGMA table_info('{tname}')").fetchall()
        cat_key, cat_label, cat_order = get_table_category(tname)
        table_stats.append({
            "table_name": tname,
            "name": tname,
            "row_count": row_count,
            "category": cat_key,
            "category_label": cat_label,
            "category_order": cat_order,
            "columns": [{"name": c[1], "type": c[2]} for c in cols]
        })
    conn.close()
    
    # Sort tables cleanly by category order then table name
    table_stats.sort(key=lambda x: (x["category_order"], x["table_name"]))
    return {"tables": table_stats}

@app.get("/api/admin/tables/{table_name}")
@app.get("/api/admin/tables/{table_name}/rows")
def api_get_table_rows(
    table_name: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: Optional[str] = Query("asc"),
    filter_col: Optional[str] = None,
    filter_val: Optional[str] = None
):
    """
    Guarded route: Fetches paginated rows for any archive database table.
    Restricted strictly to Administrator role.
    """
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with an Administrator account."
        )
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Data Studio is reserved for System Administrators. Curators have access to the Visual OCR Studio."
        )

    conn = get_db()
    
    valid_tables = [r[0] for r in conn.execute("SHOW TABLES;").fetchall()]
    if table_name not in valid_tables:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")

    cols = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    col_names = [c[1] for c in cols]

    count_sql = f"SELECT COUNT(*) FROM {table_name}"
    where_clauses = []
    params = []

    if search:
        search_terms = []
        for c in col_names:
            search_terms.append(f"CAST({c} AS VARCHAR) ILIKE ?")
            params.append(f"%{search}%")
        where_clauses.append(f"({' OR '.join(search_terms)})")

    if filter_col and filter_val and filter_col in col_names:
        where_clauses.append(f"CAST({filter_col} AS VARCHAR) ILIKE ?")
        params.append(f"%{filter_val}%")

    if where_clauses:
        count_sql += " WHERE " + " AND ".join(where_clauses)

    total_rows = conn.execute(count_sql, params).fetchone()[0]

    select_sql = f"SELECT * FROM {table_name}"
    if where_clauses:
        select_sql += " WHERE " + " AND ".join(where_clauses)

    if sort_by and sort_by in col_names:
        dir_clean = "DESC" if sort_dir and sort_dir.lower() == "desc" else "ASC"
        select_sql += f" ORDER BY {sort_by} {dir_clean}"

    offset = (page - 1) * page_size
    select_sql += f" LIMIT {page_size} OFFSET {offset}"

    raw_rows = conn.execute(select_sql, params).fetchall()
    conn.close()

    result_rows = []
    for r in raw_rows:
        row_dict = {}
        for idx, col in enumerate(col_names):
            val = r[idx]
            if col == "embedding" and val is not None:
                if isinstance(val, (list, tuple)) and len(val) >= 3:
                    row_dict[col] = f"[FLOAT[128]: {val[0]:.2f}, {val[1]:.2f}, {val[2]:.2f}, ...]"
                else:
                    row_dict[col] = str(val)
            else:
                row_dict[col] = str(val) if val is not None else None
        result_rows.append(row_dict)

    return {
        "table_name": table_name,
        "columns": col_names,
        "total_rows": total_rows,
        "page": page,
        "page_size": page_size,
        "rows": result_rows
    }

# ----------------------------------------------------------------------------
# 4. DIGITAL RIGHTS MANAGEMENT & GPAY PREMIUM FLOW
# ----------------------------------------------------------------------------

class GPayPaymentRequest(BaseModel):
    study_id: str
    user_email: str
    transaction_ref: str
    amount_inr: float = 499.0

@app.post("/api/payment/simulate-gpay")
def api_simulate_gpay(req: GPayPaymentRequest, request: Request):
    conn = get_db()
    req_id = f"pay_{uuid.uuid4().hex[:10]}"
    conn.execute("""
        INSERT INTO premium_download_requests VALUES (?, ?, ?, 'gpay', ?, ?, 'approved', CURRENT_TIMESTAMP)
    """, (req_id, req.study_id, req.user_email, req.transaction_ref, req.amount_inr))

    # Phase 2: Track user download license & subscription history
    user = get_current_user_from_request(request)
    user_id = user["sub"] if user else None
    dl_id = f"dl_{uuid.uuid4().hex[:10]}"
    try:
        conn.execute("""
            INSERT INTO user_downloads (id, user_id, study_id, license_ref, resolution, downloaded_at)
            VALUES (?, ?, ?, ?, '300dpi_master', CURRENT_TIMESTAMP);
        """, (dl_id, user_id, req.study_id, req_id))
    except Exception:
        pass

    sub_id = f"sub_{uuid.uuid4().hex[:10]}"
    try:
        conn.execute("""
            INSERT INTO user_subscriptions (id, user_id, tier, status, amount_inr, last_payment_date, payment_method)
            VALUES (?, ?, 'scholar_pro', 'active', ?, CURRENT_TIMESTAMP, 'gpay');
        """, (sub_id, user_id, req.amount_inr))
    except Exception:
        pass

    conn.close()

    return {
        "status": "success",
        "message": "Payment verified successfully via Google Pay UPI.",
        "download_license_id": req_id,
        "license_expiry": "Valid for 72 hours",
        "study_id": req.study_id,
        "notice": "Phase 2 subscription & download record created in DuckDB."
    }

@app.get("/api/gallery/3d-data")
def api_gallery_3d_data():
    """
    Returns slide plates formatted for Three.js WebGL 3D Sacred Bronze Gallery.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT 
            s.id AS slide_id,
            st.id AS study_id,
            st.title AS study_title,
            ser.name AS series_name,
            s.slide_number,
            s.slide_title,
            s.image_url
        FROM study_slides s
        JOIN studies st ON s.study_id = st.id
        JOIN series ser ON st.series_id = ser.id
        ORDER BY s.slide_number
    """).fetchall()

    slides = []
    for r in rows:
        slides.append({
            "slide_id": r[0],
            "study_id": r[1],
            "study_title": r[2],
            "series_name": r[3],
            "slide_number": r[4],
            "slide_title": r[5] or f"Plate {r[4]}",
            "image_url": f"/{r[6]}" if r[6] and not r[6].startswith('/') else r[6]
        })

    conn.close()
    return {
        "status": "success",
        "total_slides": len(slides),
        "slides": slides
    }

@app.get("/api/hero-slides")
def api_hero_slides(limit: int = Query(4, ge=1, le=12)):
    """
    Returns the most recently uploaded slide plates for the landing-page hero
    carousel. Ordered by insertion order (DuckDB rowid DESC) so the newest
    curated uploads always surface first.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT
            s.id AS slide_id,
            s.slide_number,
            s.slide_title,
            s.image_url,
            st.id AS study_id,
            st.title AS study_title,
            st.subtitle AS study_subtitle,
            st.access_level,
            st.total_slides
        FROM study_slides s
        JOIN studies st ON s.study_id = st.id
        ORDER BY s.rowid DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    slides = []
    for r in rows:
        slide_number, slide_title, image_url = r[1], r[2], r[3]
        study_title, study_subtitle, access_level, total_slides = r[5], r[6], r[7], r[8]
        is_public = (access_level or "").lower() == "public"
        if is_public and total_slides:
            badge = f"Public Study \u00b7 Plate {slide_number} of {total_slides}"
        elif is_public:
            badge = "Public Study \u00b7 Featured Plate"
        else:
            badge = "Masterpiece Study \u00b7 Featured Plate"
        slides.append({
            "badge": badge,
            "title": slide_title or study_title or f"Plate {slide_number}",
            "sub": study_subtitle or "Sacred Panchaloha Bronze Iconography",
            "img": f"/{image_url}" if image_url and not image_url.startswith('/') else image_url,
            "study_id": r[4]
        })

    return {"status": "success", "count": len(slides), "slides": slides}

# ----------------------------------------------------------------------------
# 5. FRONTEND SPA SERVING
# ----------------------------------------------------------------------------

# Serve Frontend Index
@app.get("/")
def serve_frontend_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "FMM Iconography Archive API is running. Angular UI loading..."}

# Mount frontend directory for static assets

# ==============================================================================
# CURATORIAL CRUD MAINTENANCE & AUDIT ROUTES
# ==============================================================================
import crud_service

@app.get("/api/crud/audit/logs")
def api_list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    table_name: Optional[str] = None
):
    """Fetches chronological audit trail of all curatorial CRUD operations."""
    logs = crud_service.list_audit_logs(limit=limit, offset=offset, table_name=table_name)
    return {"status": "success", "count": len(logs), "logs": logs}

@app.get("/api/crud/fk-options/{field_name}")
def api_crud_fk_options(field_name: str):
    """Returns dropdown options for a foreign key field."""
    try:
        options = crud_service.get_fk_options(field_name)
        return {"field": field_name, "options": options}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/crud/cascade/{entity}/{record_id}")
async def cascade_impact(entity: str, record_id: str):
    """Return cascade impact tree for a record — used before confirming delete."""
    try:
        impact = crud_service.get_cascade_impact(entity, record_id)
        return impact
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crud/{entity}")
def api_crud_list(
    entity: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = "desc"
):
    """Lists paginated records for series, studies, dictionary, or catalog."""
    try:
        data = crud_service.list_records(entity, page=page, page_size=page_size,
                                         search=search, sort_by=sort_by, sort_dir=sort_dir)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/crud/{entity}/{record_id}")
def api_crud_get(entity: str, record_id: str):
    """Gets a single record by ID."""
    try:
        rec = crud_service.get_record(entity, record_id)
        if not rec:
            raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found in {entity}.")
        return {"status": "success", "record": rec}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/crud/{entity}")
async def api_crud_create(entity: str, request: Request):
    """Creates a new record with automatic audit tracking."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["curator", "admin"]:
        raise HTTPException(status_code=401, detail="Authentication required. Sign in as Curator or Administrator.")
    
    try:
        body = await request.json()
        new_rec = crud_service.create_record(
            entity=entity,
            data=body,
            user_email=user.get("email", "curator@fivemetalmasonry.com"),
            user_role=user.get("role", "curator")
        )
        return {"status": "success", "message": f"Created new {entity} record successfully.", "record": new_rec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/crud/{entity}/{record_id}")
async def api_crud_update(entity: str, record_id: str, request: Request):
    """Updates an existing record and logs changes in audit trail."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["curator", "admin"]:
        raise HTTPException(status_code=401, detail="Authentication required. Sign in as Curator or Administrator.")
    
    try:
        body = await request.json()
        updated_rec = crud_service.update_record(
            entity=entity,
            record_id=record_id,
            data=body,
            user_email=user.get("email", "curator@fivemetalmasonry.com"),
            user_role=user.get("role", "curator")
        )
        return {"status": "success", "message": f"Updated {entity} record '{record_id}' successfully.", "record": updated_rec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/crud/{entity}/{record_id}")
def api_crud_delete(entity: str, record_id: str, request: Request, cascade: bool = False):
    """Deletes a record with relational safeguards and logs audit trail."""
    user = get_current_user_from_request(request)
    if not user or user.get("role") not in ["curator", "admin"]:
        raise HTTPException(status_code=401, detail="Authentication required. Sign in as Curator or Administrator.")
    
    try:
        result = crud_service.delete_record(
            entity=entity,
            record_id=record_id,
            cascade=cascade,
            user_email=user.get("email", "curator@fivemetalmasonry.com"),
            user_role=user.get("role", "curator")
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend_static")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting FMM Iconography Archive server on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)


