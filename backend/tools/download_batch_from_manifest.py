#!/usr/bin/env python3
"""Batch download 50 cameras from manifest using single browser session."""

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright


# Use absolute paths based on project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
MANIFEST_FILE = PROJECT_ROOT / "datasets/dpreview/camera_manifest.json"
DATASET_DIR = PROJECT_ROOT / "datasets/dpreview"


def load_manifest() -> dict:
    """Load manifest file."""
    if not MANIFEST_FILE.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_FILE}")
        sys.exit(1)
    return json.loads(MANIFEST_FILE.read_text())


def save_manifest(manifest: dict):
    """Save manifest file."""
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


async def download_camera(
    page,
    brand: str,
    model: str,
    gallery_url: str,
    max_photos: int = 2
) -> dict:
    """Download photos from a single camera gallery."""
    
    output_dir = DATASET_DIR / brand / model
    output_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    
    try:
        # Navigate to gallery
        await page.goto(gallery_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)  # Wait for JS rendering
        
        # Extract image URLs via JavaScript
        img_urls = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                return images
                    .map(img => img.src)
                    .filter(src => src && src.includes('dpreview') && src.includes('.jpg') && !src.includes('pixel.wp.com'))
                    .map(src => src.split('?')[0])
                    .filter((url, index, self) => self.indexOf(url) === index);
            }
        """)
        
        if not img_urls:
            return {"status": "failed", "error": "No images found", "downloaded": 0}
        
        # Download first max_photos
        for i, url in enumerate(img_urls[:max_photos]):
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.ok:
                    content = await response.body()
                    
                    # Save file (WebP or JPEG, both OK for quantization analysis)
                    dest = output_dir / f"{i+1:02d}.jpg"
                    dest.write_bytes(content)
                    
                    downloaded.append({
                        "filename": dest.name,
                        "size": len(content),
                    })
                    
                    print(f"    ✓ {dest.name} ({len(content)//1024} KB)")
                    
                    # Rate limit
                    await page.wait_for_timeout(1500)
                else:
                    print(f"    ✗ HTTP {response.status if response else 'unknown'}")
                    
            except Exception as e:
                print(f"    ✗ {url}: {e}")
        
    except Exception as e:
        return {"status": "failed", "error": str(e), "downloaded": 0}
    
    status = "done" if len(downloaded) == max_photos else "partial"
    return {"status": status, "downloaded": len(downloaded), "photos": downloaded}


async def main():
    """Main batch download function."""
    
    manifest = load_manifest()
    cameras = manifest["cameras"]
    
    print(f"=== Batch Download: {len(cameras)} cameras ===\n")
    
    # Track progress
    completed = 0
    failed = 0
    
    async with async_playwright() as p:
        # Launch browser once for all cameras
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        # Add consent cookie
        await context.add_cookies([{
            'name': 'consent',
            'value': 'true',
            'domain': '.dpreview.com',
            'path': '/',
        }])
        
        page = await context.new_page()
        
        # Process each camera
        for idx, camera in enumerate(cameras, 1):
            brand = camera["brand"]
            model = camera["model"]
            url = camera["url"]
            
            # Skip if already downloaded
            if camera.get("status") == "done":
                print(f"[{idx}/{len(cameras)}] SKIP: {brand} {model} (already done)\n")
                completed += 1
                continue
            
            print(f"[{idx}/{len(cameras)}] {brand} {model}")
            
            # Download photos
            result = await download_camera(page, brand, model, url, max_photos=2)
            
            # Update manifest
            camera["status"] = result["status"]
            camera["downloaded_count"] = result["downloaded"]
            
            if result["status"] == "done":
                completed += 1
                print(f"  ✓ Complete: {result['downloaded']} photos\n")
            elif result["status"] == "partial":
                completed += 1
                print(f"  ⚠ Partial: {result['downloaded']} photos\n")
            else:
                failed += 1
                camera["error"] = result.get("error", "Unknown error")
                print(f"  ✗ Failed: {camera['error']}\n")
            
            # Save manifest after each camera
            save_manifest(manifest)
            
            # Brief pause between cameras
            await page.wait_for_timeout(1000)
        
        await browser.close()
    
    # Final summary
    print("\n" + "="*50)
    print(f"SUMMARY")
    print("="*50)
    print(f"Total cameras: {len(cameras)}")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    print(f"Total photos: {sum(c.get('downloaded_count', 0) for c in cameras)}")
    print(f"Manifest: {MANIFEST_FILE}")
    print(f"Dataset: {DATASET_DIR}")
    
    # Verify folder count
    folder_count = sum(1 for _ in DATASET_DIR.rglob('*') if _.is_dir() and any(_.glob('*.jpg')))
    print(f"Folders with photos: {folder_count}")


if __name__ == "__main__":
    asyncio.run(main())
