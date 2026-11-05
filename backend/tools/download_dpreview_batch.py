#!/usr/bin/env python3
"""Batch download 50 new camera samples from DPReview (2 photos each = 100 total)."""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright
from PIL import Image
from PIL.ExifTags import TAGS


MANIFEST_FILE = Path("datasets/dpreview/download_manifest.json")
DATASET_DIR = Path("datasets/dpreview")

# Existing cameras to skip
EXISTING_CAMERAS = {
    ("Apple", "iPhone 18 Pro Max"),
    ("Canon", "Canon EOS R8 Mark II"),
    ("DJI", "FC8282"),
    ("DJI", "FC8284"),
    ("FUJIFILM", "X-T30 III"),
    ("GoPro", "HERO12 Black"),
    ("Google", "Pixel 11 Pro XL"),
    ("Hasselblad", "X2D II 100C"),
    ("LEICA CAMERA AG", "LEICA Q3"),
    ("NIKON CORPORATION", "NIKON Z 8"),
    ("NORITSU KOKI", "EZ Controller"),
    ("Nothing", "A059"),
    ("OM Digital Solutions", "PEN"),
    ("Panasonic", "DC-S9"),
    ("RICOH IMAGING COMPANY, LTD.", "PENTAX K-3 Mark III"),
    ("RICOH IMAGING COMPANY, LTD.", "RICOH GR IV"),
    ("SONY", "ILCE-9M3"),
    ("Sigma", "Sigma BF"),
    ("Xiaomi", "Xiaomi 17T Pro"),
    ("Xiaomi", "POCO F9 Ultra"),
    ("vivo", "V2114"),
}


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {"cameras": [], "stats": {"downloaded": 0, "failed": 0, "skipped": 0}}


def save_manifest(manifest: dict):
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def is_camera_gallery(title: str) -> bool:
    """Check if gallery is for a camera (not lens)."""
    title_lower = title.lower()
    # Skip lens galleries
    if any(kw in title_lower for kw in ["lens", "nikkor", "fe ", "rf ", "xf ", "mm f"]):
        return False
    # Skip if no camera indicators
    if not any(kw in title_lower for kw in ["sample gallery", "camera", "iphone", "pixel", "galaxy"]):
        return False
    return True


def extract_camera_info(title: str) -> tuple[str, str] | None:
    """Extract brand and model from gallery title."""
    # Common patterns
    patterns = [
        r"^(.+?)\s+(EOS\s+\S+|ILCE-\S+|NIKON\s+\S+|X-\S+|GR\s+\S+|Q\d+|X\d+)",
        r"^(.+?)\s+(iPhone\s+\S+|Pixel\s+\S+|Galaxy\s+\S+|POCO\s+\S+)",
        r"^(.+?)\s+(A\d+|V\d+|HERO\d+|FC\d+)",
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            brand = match.group(1).strip()
            model = match.group(2).strip()
            return brand, model
    
    return None


async def download_gallery_photos(
    page, gallery_url: str, output_dir: Path, max_photos: int = 2
) -> list[dict]:
    """Download photos from a single gallery."""
    downloaded = []
    
    try:
        await page.goto(gallery_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        
        # Extract image URLs
        img_urls = await page.evaluate("""
            () => {
                const urls = [];
                const imgs = document.querySelectorAll('img[src*=".jpg"]');
                for (let img of imgs) {
                    let src = img.src;
                    if (src.includes('dpreview') && !src.includes('pixel.wp.com')) {
                        urls.push(src.split('?')[0]);
                    }
                }
                return urls.slice(0, 10);
            }
        """)
        
        # Download first max_photos
        for i, url in enumerate(img_urls[:max_photos]):
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                
                if response and response.ok:
                    content = await response.body()
                    
                    # Save to output dir
                    dest = output_dir / f"{i+1:02d}.jpg"
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
                    
                    downloaded.append({
                        "url": url,
                        "filename": dest.name,
                        "size": len(content),
                        "make": make,
                        "model": model,
                    })
                    
                    print(f"  ✓ {dest.name} ({len(content)//1024} KB, {make} | {model})")
                    await page.wait_for_timeout(1500)  # Rate limit
                else:
                    print(f"  ✗ HTTP {response.status if response else 'unknown'}")
                    
            except Exception as e:
                print(f"  ✗ {url}: {e}")
                
    except Exception as e:
        print(f"  ✗ Gallery error: {e}")
    
    return downloaded


async def main():
    parser = argparse.ArgumentParser(description="Batch download camera samples from DPReview")
    parser.add_argument("--target", type=int, default=50, help="Target number of cameras")
    parser.add_argument("--resume", action="store_true", help="Resume from manifest")
    args = parser.parse_args()
    
    manifest = load_manifest()
    downloaded_cameras = {c["brand_model"] for c in manifest["cameras"] if c["status"] == "downloaded"}
    
    print(f"Manifest: {len(manifest['cameras'])} cameras tracked")
    print(f"Already downloaded: {len(downloaded_cameras)}")
    print(f"Target: {args.target} new cameras")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        
        page = await context.new_page()
        
        # Navigate to DPReview sample galleries
        print("\n=== Navigating to DPReview sample galleries ===")
        await page.goto("https://www.dpreview.com/sample-galleries/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Extract gallery links
        print("Extracting gallery links...")
        galleries = await page.evaluate("""
            () => {
                const links = [];
                const anchors = document.querySelectorAll('a[href*="/sample-galleries/"]');
                for (let a of anchors) {
                    const href = a.href;
                    const title = a.textContent.trim();
                    if (href.includes('-sample-gallery') && title.length > 0 && title.length < 150) {
                        links.push({title, url: href});
                    }
                }
                return links;
            }
        """)
        
        print(f"Found {len(galleries)} galleries")
        
        # Filter and process galleries
        cameras_downloaded = len(downloaded_cameras)
        
        for gallery in galleries:
            if cameras_downloaded >= args.target:
                print(f"\n=== Target reached: {cameras_downloaded} cameras ===")
                break
            
            title = gallery["title"]
            url = gallery["url"]
            
            # Skip if not a camera gallery
            if not is_camera_gallery(title):
                continue
            
            # Extract camera info
            camera_info = extract_camera_info(title)
            if not camera_info:
                continue
            
            brand, model = camera_info
            brand_model = f"{brand}/{model}"
            
            # Skip existing
            if (brand, model) in EXISTING_CAMERAS:
                print(f"SKIP: {brand_model} (already in dataset)")
                continue
            
            if brand_model in downloaded_cameras:
                print(f"SKIP: {brand_model} (already downloaded)")
                continue
            
            print(f"\n=== Processing: {brand_model} ===")
            
            # Create output directory
            output_dir = DATASET_DIR / brand.replace(" ", "-") / model.replace(" ", "-")
            
            # Download photos
            photos = await download_gallery_photos(page, url, output_dir, max_photos=2)
            
            # Update manifest
            manifest["cameras"].append({
                "brand_model": brand_model,
                "brand": brand,
                "model": model,
                "gallery_url": url,
                "photos_downloaded": len(photos),
                "status": "downloaded" if len(photos) == 2 else "partial",
            })
            
            manifest["stats"]["downloaded"] += len(photos)
            save_manifest(manifest)
            
            if len(photos) == 2:
                cameras_downloaded += 1
                print(f"✓ {brand_model}: {len(photos)} photos")
            else:
                print(f"⚠ {brand_model}: only {len(photos)} photos")
        
        await browser.close()
    
    print(f"\n=== SUMMARY ===")
    print(f"Cameras downloaded: {cameras_downloaded}/{args.target}")
    print(f"Total photos: {manifest['stats']['downloaded']}")
    print(f"Manifest: {MANIFEST_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())