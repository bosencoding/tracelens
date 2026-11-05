#!/usr/bin/env python3
"""Download sample JPEG photos using Playwright to avoid bot detection."""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright
from PIL import Image
from PIL.ExifTags import TAGS


async def download_gallery(
    gallery_url: str,
    output_dir: Path,
    brand: str,
    model: str,
    max_photos: int = 5,
) -> dict:
    """Download photos from DPReview gallery using Playwright."""
    
    model_dir = output_dir / brand / model
    model_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    errors = []
    
    async with async_playwright() as p:
        # Launch browser with anti-bot settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        
        # Add realistic headers
        await context.add_cookies([
            {
                'name': 'consent',
                'value': 'true',
                'domain': '.dpreview.com',
                'path': '/',
            }
        ])
        
        page = await context.new_page()
        
        try:
            # Navigate to gallery
            print(f"Navigating to: {gallery_url}")
            await page.goto(gallery_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(2000)  # Wait for JS to render
            
            # Extract image URLs
            print("Extracting image URLs...")
            img_elements = await page.query_selector_all('img[src*=".jpg"]')
            
            urls = []
            for img in img_elements[:max_photos * 3]:  # Get more than needed, filter later
                src = await img.get_attribute('src')
                if src and 'dpreview' in src and '.jpg' in src and 'pixel.wp.com' not in src:
                    # Get full resolution URL (remove resize params)
                    full_url = src.split('?')[0]
                    if full_url not in urls:
                        urls.append(full_url)
            
            print(f"Found {len(urls)} image URLs, downloading first {max_photos}...")
            
            # Download images
            for i, url in enumerate(urls[:max_photos], start=1):
                try:
                    # Download via page context (same session)
                    response = await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    if response and response.ok:
                        content = await response.body()
                        
                        dest = model_dir / f"{i:02d}.jpg"
                        dest.write_bytes(content)
                        
                        # Verify EXIF
                        img = Image.open(dest)
                        exif = img._getexif()
                        make = model_name = None
                        if exif:
                            for tag_id, value in exif.items():
                                tag = TAGS.get(tag_id, tag_id)
                                if tag == "Make":
                                    make = str(value).strip('\x00').strip()
                                elif tag == "Model":
                                    model_name = str(value).strip('\x00').strip()
                        
                        downloaded.append({
                            "filename": dest.name,
                            "url": url,
                            "size": len(content),
                            "make": make,
                            "model": model_name,
                        })
                        
                        print(f"  ✓ {dest.name} ({len(content)//1024} KB, {make} | {model_name})")
                        
                        # Rate limiting
                        await page.wait_for_timeout(1000)
                    else:
                        errors.append({"url": url, "error": f"HTTP {response.status if response else 'unknown'}"})
                        print(f"  ✗ {url}: HTTP {response.status if response else 'unknown'}")
                        
                except Exception as e:
                    errors.append({"url": url, "error": str(e)})
                    print(f"  ✗ {url}: {e}")
            
        except Exception as e:
            errors.append({"url": gallery_url, "error": str(e)})
            print(f"Error: {e}")
        finally:
            await browser.close()
    
    return {
        "gallery_url": gallery_url,
        "brand": brand,
        "model": model,
        "downloaded": downloaded,
        "errors": errors,
        "total_downloaded": len(downloaded),
        "total_errors": len(errors),
    }


async def main():
    parser = argparse.ArgumentParser(description="Download sample JPEG photos with Playwright")
    parser.add_argument("--url", required=True, help="DPReview gallery URL")
    parser.add_argument("--brand", required=True, help="Camera brand (e.g., Google)")
    parser.add_argument("--model", required=True, help="Camera model (e.g., Pixel-11-Pro)")
    parser.add_argument("--output-dir", default="datasets/dpreview", help="Output directory")
    parser.add_argument("--max-photos", type=int, default=5, help="Max photos to download")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    result = await download_gallery(
        gallery_url=args.url,
        output_dir=output_dir,
        brand=args.brand,
        model=args.model,
        max_photos=args.max_photos,
    )
    
    print("\n=== SUMMARY ===")
    print(f"Downloaded: {result['total_downloaded']}")
    print(f"Failed: {result['total_errors']}")
    
    if result['total_downloaded'] > 0:
        print(f"\nPhotos saved to: {output_dir / args.brand / args.model}/")
    
    # Write log
    log_file = output_dir / f"download_{args.brand}_{args.model}.json"
    log_file.write_text(json.dumps(result, indent=2))
    print(f"Log: {log_file}")


if __name__ == "__main__":
    asyncio.run(main())