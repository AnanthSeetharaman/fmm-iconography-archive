import os
from pathlib import Path

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
STORAGE_DIR = BACKEND_DIR / "storage"
IMAGES_STORAGE_DIR = STORAGE_DIR / "images"
FRONTEND_DIR = APP_DIR / "frontend"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# DuckDB Database file path
DB_FILE = str(DATA_DIR / "fmm_archive.duckdb")

# Host / Port (Dynamic for Google Cloud Run / App Engine)
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))

# Google OAuth 2.0 Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "740115620155-q7r0g6cak77kul4u3te9visjlsiqiluj.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fmm_archival_sacred_secret_key_2026_gcp")
SESSION_COOKIE_NAME = "fmm_auth_token"

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_TdycTlhey80HVM")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "Wr8gZk9Vft5dDAS1wRwxdAVe")

# LLM & Vision Model Configuration
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
LLM_LODEL = LLM_MODEL  # Compatibility alias

PROMPT_OCR = (
    "You are an expert epigraphist and Shilpa Shastra scholar specializing in South Indian bronze iconography. "
    "Transcribe all text from this iconography plate with 100% precision and scholarly fidelity. "
    "Preserve Sanskrit IAST transliteration diacritics (such as Gaṇeśa, Āsīna, Mūṣika, Triśuṇḍa, Lalitāsana, etc.). "
    "Extract study titles, numbered classification points, mudras, attributes, and regional notes exactly as they appear. "
    "Output only the transcribed text without conversational preamble or commentary."
)

PROMPT_ICONOGRAPHY_VALIDATION = (
    "You are a strict domain verifier and epigraphist for the Five Metal Masonry (FMM) Sacred Iconography Archive. "
    "Analyze the provided image and determine whether it belongs to the domain of South Asian sacred iconography, "
    "Shilpa Shastra, Hindu/Buddhist/Jain sculptures, sacred bronzes (Panchaloha), temple art, stone reliefs, "
    "iconographic diagrams, mudras, asanas, temple architecture, manuscript illustrations, or epigraphic study plates. "
    "If the image is completely unrelated—such as a personal portrait/selfie, everyday personal photo, modern clothing/fashion, "
    "domestic animal, modern vehicle, food, commercial receipt, computer screenshot, cartoon, or general unrelated photograph—it must be strictly rejected.\n\n"
    "Respond ONLY with a valid JSON object in this exact format:\n"
    "{\n"
    '  "is_valid": true,\n'
    '  "reason": "Clear scholarly explanation of why the image is accepted as sacred iconography/Shilpa Shastra or why it is rejected as unrelated content."\n'
    "}"
)
PROMPT_VALIDATION = PROMPT_ICONOGRAPHY_VALIDATION

