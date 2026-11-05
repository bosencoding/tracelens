#!/usr/bin/env python3
"""Download sample JPEG photos from Wikimedia Commons."""
import argparse
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


def download_file(url: str, dest: Path, delay: float = 1.0) -> dict:
    """Download a file from URL to destination path."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        
        # Verify EXIF
        img = Image.open(dest)
        exif = img._getexif()
        make = model = None
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "Make":
                    make = str(value).strip('\x00').strip()
                elif tag == "Model":
                    model = str(value).strip('\x00').strip()
        
        return {
            "url": url,
            "filename": dest.name,
            "size": dest.stat().st_size,
            "make": make,
            "model": model,
            "status": "success"
        }
    except Exception as e:
        return {
            "url": url,
            "filename": dest.name,
            "error": str(e),
            "status": "failed"
        }
    finally:
        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Download sample JPEG photos from Wikimedia Commons")
    parser.add_argument("--output-dir", default="datasets/dpreview", help="Output directory")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    results = []
    
    # Canon EOS R5 sample URLs from Wikimedia Commons
    canon_r5_urls = [
        "https://upload.wikimedia.org/wikipedia/commons/7/7e/Canon_EOS_R5%2BR_RF_100-500mm_f4.5-7.1L_IS_USM%281%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/f/f4/Canon_EOS_R5%2BR_RF_100-500mm_f4.5-7.1L_IS_USM%282%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3b/Canon_EOS_R5%2BR_RF_100-500mm_f4.5-7.1L_IS_USM%283%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/8/82/Canon_EOS_R5%2BR_RF_100-500mm_f4.5-7.1L_IS_USM%284%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/a7/Canon_EOS_R5%2BR_RF_100-500mm_f4.5-7.1L_IS_USM%285%29.jpg",
    ]
    
    # Sony A7 IV sample URLs (to be found)
    sony_a7iv_urls = [
        # Will add after finding working URLs
    ]
    
    # Download Canon EOS R5
    brand = "Canon"
    model = "EOS-R5"
    model_dir = output_dir / brand / model
    
    print(f"\n=== Downloading {brand} {model} ===")
    for i, url in enumerate(canon_r5_urls, start=1):
        dest = model_dir / f"{i:02d}.jpg"
        
        if dest.exists():
            print(f"SKIP: {dest} already exists")
            continue
        
        print(f"DOWNLOADING: {url}")
        result = download_file(url, dest)
        results.append(result)
        
        if result["status"] == "success":
            print(f"  ✓ {dest.name} ({result['size']} bytes)")
            print(f"    Make: {result['make']}, Model: {result['model']}")
        else:
            print(f"  ✗ FAILED: {result['error']}")
    
    # Summary
    print("\n=== SUMMARY ===")
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"Downloaded: {success}, Failed: {failed}")
    
    if results:
        log_file = output_dir / "download_log_wikimedia.json"
        log_file.write_text(json.dumps(results, indent=2))
        print(f"Log: {log_file}")


if __name__ == "__main__":
    main()