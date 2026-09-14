#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
Raw Image Asset & Metadata Synchronization (populate_raw_images.py)

Organizes all high quality sacred bronze image plates into C:\\Users\\anant\\Downloads\\FMM\\raw\\,
downloads high-res remote plate assets, and updates JSON metadata across all 4 taxonomy tiers.
"""

import os
import sys
import shutil
import json
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path(r"C:\Users\anant\Downloads\FMM\raw")
IMAGES_ARCHIEVE_DIR = Path(r"C:\Users\anant\Downloads\FMM\Images-archieve")
STORAGE_IMAGES_DIR = Path(r"C:\Users\anant\Downloads\FMM\app\backend\storage\images\ganesa-variations-in-iconography")

RAW_DIR.mkdir(parents=True, exist_ok=True)

def sync_raw_assets():
    print(f"[FMM Raw Image Sync Pipeline]")
    print(f"Target Directory: {RAW_DIR}")

    # 1. Copy slide plates from Images-archieve & backend storage
    slide_sources = []
    if IMAGES_ARCHIEVE_DIR.exists():
        slide_sources.extend(sorted(list(IMAGES_ARCHIEVE_DIR.glob("*.jpeg")) + list(IMAGES_ARCHIEVE_DIR.glob("*.jpg"))))
    if STORAGE_IMAGES_DIR.exists():
        slide_sources.extend(sorted(list(STORAGE_IMAGES_DIR.glob("*.png")) + list(STORAGE_IMAGES_DIR.glob("*.jpeg"))))

    print(f"Found {len(slide_sources)} local high-res plate source files.")

    copied_images = []
    for idx, src_file in enumerate(slide_sources, 1):
        target_name = f"fb_iconography_plate_{idx}{src_file.suffix}"
        target_path = RAW_DIR / target_name
        shutil.copy2(src_file, target_path)
        copied_images.append(target_name)
        print(f"  [+] Copied HQ Plate: {target_name} ({target_path.stat().st_size} bytes)")

    # 2. Download sample remote bronze plates if available
    remote_samples = [
        ("fb_nataraja_chola_001.jpeg", "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?w=1200&auto=format&fit=crop&q=80"),
        ("fb_krishna_kaliya_002.jpeg", "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=1200&auto=format&fit=crop&q=80")
    ]

    for filename, url in remote_samples:
        target_path = RAW_DIR / filename
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp, open(target_path, "wb") as f:
                f.write(resp.read())
            copied_images.append(filename)
            print(f"  [+] Downloaded Remote HQ Plate: {filename}")
        except Exception as e:
            print(f"  [-] Note downloading {filename}: {e}")

    # 3. Update Master Raw Index JSON
    master_index_path = RAW_DIR / "raw_master_index.json"
    if master_index_path.exists():
        with open(master_index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["total_images_saved"] = len(copied_images)
        data["saved_image_files"] = copied_images

        with open(master_index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nRaw Asset Population Complete!")
    print(f"Total High Quality Images in {RAW_DIR}: {len(list(RAW_DIR.glob('*')))} files.\n")

if __name__ == "__main__":
    sync_raw_assets()
