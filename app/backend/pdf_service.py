import io
from pathlib import Path
from typing import Dict, Any, List, Optional

from PIL import Image

STORAGE_DIR = Path(__file__).resolve().parent / "storage"
MAX_DIMENSION = 2200  # cap very large images to keep PDF size reasonable


def _resolve_image_path(image_url: Optional[str]) -> Optional[Path]:
    """Map a stored image_url (e.g. '/storage/images/<slug>/slide_1.png') to a file on disk."""
    if not image_url:
        return None

    # Absolute path already on disk
    try:
        p = Path(image_url)
        if p.is_absolute() and p.exists():
            return p
    except Exception:
        pass

    clean = image_url.lstrip("/")
    if clean.startswith("storage/"):
        clean = clean.replace("storage/", "", 1)

    candidates = [
        STORAGE_DIR / clean,
        STORAGE_DIR / "images" / clean,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _load_image_for_pdf(path: Path) -> Optional[Image.Image]:
    """Open an image, flatten transparency onto white, convert to RGB, downscale if huge."""
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        print(f"[pdf] Could not open image {path}: {e}")
        return None

    # Flatten alpha / palette transparency onto white
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Downscale oversized images
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    return img


def generate_image_only_pdf(image_urls: List[str]) -> io.BytesIO:
    """
    Build a PDF containing ONLY the images — one image per page, no text,
    borders, watermarks, or templates. Each page is sized to its image.
    """
    pages: List[Image.Image] = []
    for url in image_urls:
        path = _resolve_image_path(url)
        if not path:
            print(f"[pdf] Skipping missing image: {url}")
            continue
        img = _load_image_for_pdf(path)
        if img is not None:
            pages.append(img)

    buffer = io.BytesIO()
    if not pages:
        # Nothing resolved — emit a single blank page so the response is a valid PDF
        Image.new("RGB", (1240, 1754), (255, 255, 255)).save(buffer, format="PDF")
        buffer.seek(0)
        return buffer

    pages[0].save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=150.0,
    )
    buffer.seek(0)
    return buffer


def generate_study_pdf(study_data: Dict[str, Any], user_email: str = "") -> io.BytesIO:
    """
    Images-only PDF for a single study: every slide/plate image, one per page,
    in slide order. No captions, OCR text, metadata tables, or watermarks.
    (user_email kept for call-site compatibility; not rendered.)
    """
    slides = study_data.get("slides", []) or []
    image_urls = [sl.get("image_url") for sl in slides if sl.get("image_url")]
    return generate_image_only_pdf(image_urls)
