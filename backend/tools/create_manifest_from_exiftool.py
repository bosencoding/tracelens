#!/usr/bin/env python3
"""Create new manifest from ExifTool cameras with ≥2 samples and copy photos."""

import json
import shutil
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


PROJECT_ROOT = Path(__file__).parent.parent.parent
EXIFTOOL_DIR = PROJECT_ROOT / "datasets/exiftool_samples"
MANIFEST_FILE = PROJECT_ROOT / "datasets/dpreview/camera_manifest.json"
DATASET_DIR = PROJECT_ROOT / "datasets/dpreview"


def verify_exif(jpg_path: Path) -> tuple[str | None, str | None]:
    """Verify JPEG has EXIF data and return Make/Model."""
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
    except Exception as e:
        print(f"  EXIF error: {e}")
        return None, None


def main():
    """Create manifest and copy photos."""
    print("=== Creating New Manifest from ExifTool Samples ===\n")
    
    # Load qualified cameras
    qualified_file = EXIFTOOL_DIR / "qualified_cameras.json"
    if not qualified_file.exists():
        print(f"ERROR: {qualified_file} not found. Run scan_exiftool_cameras.py first.")
        return
    
    qualified_cameras = json.loads(qualified_file.read_text())
    print(f"Found {len(qualified_cameras)} cameras with ≥2 samples\n")
    
    # Create new manifest
    new_manifest = {
        "task": "Download 50 camera samples (2 photos each) from ExifTool archive",
        "source": "https://exiftool.org/sample_images.html",
        "note": "Authentic JPEG files with valid EXIF Make/Model metadata",
        "cameras": [],
        "total_cameras": len(qualified_cameras),
        "photos_per_camera": 2,
        "total_photos": len(qualified_cameras) * 2
    }
    
    # Process each camera
    total_copied = 0
    cameras_processed = 0
    
    for idx, cam in enumerate(qualified_cameras, 1):
        make = cam["make"]
        model = cam["model"]
        sample_files = cam["files"]
        
        # Clean brand/model for directory names (remove null bytes and invalid chars)
        brand_clean = make.replace("\x00", "").replace("/", "-").replace("\\", "-").strip()
        model_clean = model.replace("\x00", "").replace("/", "-").replace("\\", "-").replace("<", "").replace(">", "").strip()
        
        # Skip if empty after cleaning
        if not brand_clean or not model_clean:
            print(f"  ✗ Invalid brand/model after cleaning, skipping\n")
            continue
        
        print(f"[{idx}/{len(qualified_cameras)}] {make} {model}")
        
        # Create output directory
        output_dir = DATASET_DIR / brand_clean / model_clean
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy first 2 samples
        copied = 0
        for i, src_file in enumerate(sample_files[:2]):
            src_path = Path(src_file)
            dest = output_dir / f"{i+1:02d}.jpg"
            
            # Verify EXIF before copying
            exif_make, exif_model = verify_exif(src_path)
            
            if not exif_make or not exif_model:
                print(f"  ✗ {src_path.name}: No EXIF data, skipping")
                continue
            
            # Copy file
            shutil.copy2(src_path, dest)
            
            size_kb = dest.stat().st_size // 1024
            print(f"  ✓ {dest.name} ({size_kb} KB, {exif_make} | {exif_model})")
            
            copied += 1
            total_copied += 1
        
        if copied == 2:
            cameras_processed += 1
            status = "done"
        elif copied > 0:
            cameras_processed += 1
            status = "partial"
        else:
            status = "failed"
        
        # Add to manifest
        new_manifest["cameras"].append({
            "brand": make,
            "model": model,
            "brand_clean": brand_clean,
            "model_clean": model_clean,
            "source": "ExifTool",
            "status": status,
            "downloaded_count": copied
        })
        
        print(f"  Status: {status} ({copied} photos)\n")
    
    # Save manifest
    MANIFEST_FILE.write_text(json.dumps(new_manifest, indent=2))
    
    # Final summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total cameras in manifest: {len(new_manifest['cameras'])}")
    print(f"Cameras processed: {cameras_processed}")
    print(f"Total photos copied: {total_copied}")
    print(f"Target: {len(qualified_cameras)} cameras × 2 photos = {len(qualified_cameras) * 2} photos")
    print(f"\nManifest: {MANIFEST_FILE}")
    print(f"Dataset: {DATASET_DIR}")
    
    # Verify folder count
    folder_count = sum(1 for _ in DATASET_DIR.rglob('*') if _.is_dir() and any(_.glob('*.jpg')))
    print(f"Folders with photos: {folder_count}")


if __name__ == "__main__":
    main()
