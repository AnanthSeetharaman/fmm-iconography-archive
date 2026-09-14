import hmac
import hashlib
import json
import base64
import time
import uuid
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from config import GOOGLE_CLIENT_ID, JWT_SECRET_KEY, SESSION_COOKIE_NAME
from database import get_db

TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)

def create_session_token(user: Dict[str, Any]) -> str:
    """
    Creates a secure, tamper-proof HMAC-SHA256 session token.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["full_name"],
        "avatar_url": user.get("avatar_url", ""),
        "role": user.get("role", "scholar"),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS
    }
    
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    
    signature = hmac.new(JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies the HMAC-SHA256 signature and expiration of a session token.
    """
    if not token or token.count('.') != 2:
        return None
    
    parts = token.split('.')
    header_b64, payload_b64, sig_b64 = parts
    
    try:
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(JWT_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_json = base64url_decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        if payload.get("exp", 0) < time.time():
            return None  # Expired
            
        return payload
    except Exception:
        return None

def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    """
    Verifies a Google OAuth 2.0 ID Token using Google's public tokeninfo endpoint.
    Returns user info (email, name, picture, sub).
    """
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FMM-Archive/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
            # If a client ID is configured, verify the audience
            if GOOGLE_CLIENT_ID and data.get("aud") != GOOGLE_CLIENT_ID:
                raise ValueError(f"Audience mismatch: expected {GOOGLE_CLIENT_ID}, got {data.get('aud')}")
                
            return {
                "google_sub": data.get("sub"),
                "email": data.get("email"),
                "email_verified": data.get("email_verified") == "true" or data.get("email_verified") is True,
                "name": data.get("name", "Scholar"),
                "picture": data.get("picture", "")
            }
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        raise ValueError(f"Google token verification failed: {err_msg}")
    except Exception as e:
        raise ValueError(f"Could not connect to Google token verification service: {str(e)}")

def upsert_user(email: str, full_name: str, avatar_url: str = "", google_sub: str = "", role: Optional[str] = None) -> Dict[str, Any]:
    """
    Upserts user record in DuckDB users table.
    """
    from database import ensure_users_table
    conn = get_db()
    ensure_users_table(conn)
    existing = conn.execute("SELECT id, email, full_name, avatar_url, role FROM users WHERE LOWER(email) = LOWER(?);", (email,)).fetchone()
    
    SUPER_ADMIN_EMAILS = {"ananth.seetharaman@gmail.com"}
    is_super_admin = email.lower() in SUPER_ADMIN_EMAILS

    if existing:
        user_id, email, current_name, current_avatar, current_role = existing
        new_avatar = avatar_url or current_avatar
        new_name = full_name or current_name
        assigned_role = "admin" if is_super_admin else (role or current_role)
        
        conn.execute("""
            UPDATE users
            SET full_name = ?, avatar_url = ?, role = ?, last_login_at = CURRENT_TIMESTAMP, google_sub = COALESCE(?, google_sub)
            WHERE id = ?;
        """, (new_name, new_avatar, assigned_role, google_sub, user_id))
        
        user_obj = {
            "id": user_id,
            "email": email,
            "full_name": new_name,
            "avatar_url": new_avatar,
            "role": assigned_role
        }
    else:
        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        assigned_role = "admin" if is_super_admin else (role or ("curator" if "curator" in email.lower() or "admin" in email.lower() else "scholar"))
        
        conn.execute("""
            INSERT INTO users (id, email, full_name, avatar_url, role, google_sub)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (user_id, email, full_name, avatar_url, assigned_role, google_sub))
        
        user_obj = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "role": assigned_role
        }
        
    conn.close()
    return user_obj

def get_current_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extracts and validates current user from Authorization header or Cookie.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif SESSION_COOKIE_NAME in request.cookies:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        
    if not token:
        return None
        
    return verify_session_token(token)
