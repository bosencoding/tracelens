#!/usr/bin/env python3
"""Organize ExifTool samples into dataset structure (50 cameras × 2 photos = 100 JPEGs)."""

import json
import shutil
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


# Use absolute paths based on project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
MANIFEST_FILE = PROJECT_ROOT / "datasets/dpreview/camera_manifest.json"
EXIFTOOL_DIR = PROJECT_ROOT / "datasets/exiftool_samples"
DATASET_DIR = PROJECT_ROOT / "datasets/dpreview"


def load_manifest() -> dict:
    """Load manifest file."""
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_FILE}")
        return {"cameras": []}
    return json.loads(MANIFEST_FILE.read_text())


def save_manifest(manifest: dict):
    """Save manifest file."""
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def find_matching_samples(brand: str, model: str) -> list[Path]:
    """Find matching sample files in ExifTool archives."""
    # Map brand names to folder names
    brand_map = {
        "Canon": "Canon",
        "Nikon": "Nikon",
        "Sony": "Sony",
        "Fujifilm": "FujiFilm",
        "Panasonic": "Panasonic",
        "Leica": "Leica",
        "Olympus": "Olympus",
        "OM-System": "Olympus",  # OM System uses Olympus folder
        "Ricoh": "Ricoh",
        "Hasselblad": "Hasselblad",
        "DJI": "DJI",
        "Google": "Google",
        "Apple": "Apple",
        "Xiaomi": "Xiaomi",
        "Nothing": "Nothing",
        "Polaroid": "Polaroid",
        "Sigma": "Sigma",
        "Camera-Intelligence": None,  # Not in ExifTool
    }
    
    folder_name = brand_map.get(brand)
    if not folder_name:
        return []
    
    brand_dir = EXIFTOOL_DIR / folder_name
    if not brand_dir.exists():
        return []
    
    # Search for matching files
    # Clean model name for matching
    model_clean = model.replace("-", "").replace(" ", "").upper()
    
    matches = []
    for jpg_file in brand_dir.glob("*.jpg"):
        # Extract camera model from filename
        # Format: BrandModel.jpg (e.g., CanonEOS5D.jpg, NikonD80.jpg)
        filename = jpg_file.stem
        
        # Remove brand prefix
        if filename.upper().startswith(folder_name.upper()):
            file_model = filename[len(folder_name):]
        else:
            file_model = filename
        
        # Clean for comparison
        file_model_clean = file_model.replace("-", "").replace(" ", "").upper()
        
        # Check if model matches (partial match OK)
        if model_clean in file_model_clean or file_model_clean in model_clean:
            matches.append(jpg_file)
    
    return matches


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
    """Main function to organize samples."""
    manifest = load_manifest()
    cameras = manifest["cameras"]
    
    print(f"=== Organizing ExifTool Samples: {len(cameras)} cameras ===\n")
    
    total_copied = 0
    cameras_with_samples = 0
    
    for idx, camera in enumerate(cameras, 1):
        brand = camera["brand"]
        model = camera["model"]
        
        print(f"[{idx}/{len(cameras)}] {brand} {model}")
        
        # Find matching samples
        samples = find_matching_samples(brand, model)
        
        if not samples:
            print(f"  ✗ No samples found\n")
            camera["status"] = "no_samples"
            continue
        
        print(f"  Found {len(samples)} matching samples")
        
        # Create output directory
        output_dir = DATASET_DIR / brand / model
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy first 2 samples
        copied = 0
        for i, sample_path in enumerate(samples[:2]):
            # Verify EXIF
            make, model_name = verify_exif(sample_path)
            
            # Copy to output
            dest = output_dir / f"{i+1:02d}.jpg"
            shutil.copy2(sample_path, dest)
            
            size_kb = dest.stat().st_size // 1024
            print(f"  ✓ {dest.name} ({size_kb} KB, {make} | {model_name})")
            
            copied += 1
            total_copied += 1
        
        if copied == 2:
            cameras_with_samples += 1
            camera["status"] = "done"
            camera["downloaded_count"] = 2
            print(f"  ✓ Complete: {copied} photos\n")
        elif copied > 0:
            cameras_with_samples += 1
            camera["status"] = "partial"
            camera["downloaded_count"] = copied
            print(f"  ⚠ Partial: {copied} photos\n")
        else:
            camera["status"] = "failed"
            print(f"  ✗ Failed to copy\n")
        
        # Save manifest after each camera
        save_manifest(manifest)
    
    # Final summary
    print("\n" + "="*50)
    print(f"SUMMARY")
    print("="*50)
    print(f"Total cameras: {len(cameras)}")
    print(f"Cameras with samples: {cameras_with_samples}")
    print(f"Total photos copied: {total_copied}")
    print(f"Manifest: {MANIFEST_FILE}")
    print(f"Dataset: {DATASET_DIR}")
    
    # Verify folder count
    folder_count = sum(1 for _ in DATASET_DIR.rglob('*') if _.is_dir() and any(_.glob('*.jpg')))
    print(f"Folders with photos: {folder_count}")


if __name__ == "__main__":
    main()
