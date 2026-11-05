#!/usr/bin/env python3
"""Scan ExifTool archives to find cameras with ≥2 samples."""

import json
from pathlib import Path
from collections import defaultdict

from PIL import Image
from PIL.ExifTags import TAGS


PROJECT_ROOT = Path(__file__).parent.parent.parent
EXIFTOOL_DIR = PROJECT_ROOT / "datasets/exiftool_samples"


def extract_camera_info(jpg_path: Path) -> tuple[str | None, str | None]:
    """Extract Make and Model from EXIF."""
    try:
        img = Image.open(jpg_path)
        exif = img._getexif()
        if not exif:
            return None, None
        
        make = model = None
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "Make":
                make = str(value).strip('\x00').strip()
            elif tag == "Model":
                model = str(value).strip('\x00').strip()
        
        return make, model
    except Exception:
        return None, None


def main():
    """Scan all archives and group by camera."""
    print("=== Scanning ExifTool Archives ===\n")
    
    # Group files by (Make, Model)
    cameras = defaultdict(list)
    
    for brand_dir in sorted(EXIFTOOL_DIR.iterdir()):
        if not brand_dir.is_dir():
            continue
        
        print(f"Scanning {brand_dir.name}...")
        
        for jpg_file in brand_dir.glob("*.jpg"):
            make, model = extract_camera_info(jpg_file)
            
            if make and model:
                key = (make, model)
                cameras[key].append(jpg_file)
    
    # Filter cameras with ≥2 samples
    print(f"\n=== Filtering cameras with ≥2 samples ===\n")
    
    qualified_cameras = []
    for (make, model), files in sorted(cameras.items()):
        if len(files) >= 2:
            qualified_cameras.append({
                "make": make,
                "model": model,
                "sample_count": len(files),
                "files": [str(f) for f in files[:2]]  # Keep first 2
            })
    
    print(f"Total cameras found: {len(cameras)}")
    print(f"Cameras with ≥2 samples: {len(qualified_cameras)}")
    
    # Save to JSON for next step
    output_file = EXIFTOOL_DIR / "qualified_cameras.json"
    output_file.write_text(json.dumps(qualified_cameras, indent=2))
    print(f"\nSaved to: {output_file}")
    
    # Show top 50
    print(f"\n=== Top 50 cameras by sample count ===\n")
    sorted_cameras = sorted(qualified_cameras, key=lambda x: x["sample_count"], reverse=True)[:50]
    
    for i, cam in enumerate(sorted_cameras, 1):
        print(f"{i:2d}. {cam['make']} {cam['model']} ({cam['sample_count']} samples)")


if __name__ == "__main__":
    main()
