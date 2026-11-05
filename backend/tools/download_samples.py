#!/usr/bin/env python3
"""Download sample JPEG photos from public sources.

Usage:
  # Download from provided URLs
  uv run python -m tools.download_samples --url-file urls.txt

  # URLs file format (one per line):
  # <brand>/<model>|<url>
  # Example:
  # Samsung/Galaxy-S24-Ultra|https://example.com/sample1.jpg
  # Canon/EOS-R5|https://example.com/sample2.jpg
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


def download_file(url: str, dest: Path, delay: float = 1.0) -> dict:
    """Download a file from URL to destination path."""
    try:
        # Download
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
    parser = argparse.ArgumentParser(description="Download sample JPEG photos")
    parser.add_argument("--url-file", required=True, help="File with URLs to download")
    parser.add_argument("--output-dir", default="datasets/dpreview", help="Output directory")
    parser.add_argument("--max-per-model", type=int, default=10, help="Max photos per model")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't download")
    args = parser.parse_args()
    
    url_file = Path(args.url_file)
    if not url_file.exists():
        print(f"ERROR: URL file not found: {url_file}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir)
    results = []
    
    # Parse URL file
    urls_by_model = {}
    for line in url_file.read_text().strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        if '|' not in line:
            print(f"SKIP: Invalid line format: {line}")
            continue
        model_key, url = line.split('|', 1)
        if model_key not in urls_by_model:
            urls_by_model[model_key] = []
        urls_by_model[model_key].append(url.strip())
    
    # Download
    for model_key, urls in urls_by_model.items():
        brand, model = model_key.split('/')
        model_dir = output_dir / brand / model
        
        for i, url in enumerate(urls[:args.max_per_model], start=1):
            ext = url.split(".")[-1].split('?')[0].lower()
            if ext not in ['jpg', 'jpeg']:
                ext = 'jpg'
            dest = model_dir / f"{i:02d}.{ext}"
            
            if dest.exists():
                print(f"SKIP: {dest} already exists")
                continue
            
            if args.dry_run:
                print(f"WOULD DOWNLOAD: {model_key} → {url} → {dest}")
                continue
            
            print(f"DOWNLOADING: {model_key} → {url}")
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
        # Write log
        log_file = output_dir / "download_log.json"
        log_file.write_text(json.dumps(results, indent=2))
        print(f"Log: {log_file}")


if __name__ == "__main__":
    main()