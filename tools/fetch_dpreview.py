#!/usr/bin/env python3
"""Download the DPReview sample set (5 images x 20 brands) into datasets/dpreview/."""
import concurrent.futures as cf
import json
import csv
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "datasets" / "dpreview"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SET = json.loads((Path(__file__).resolve().parent / "dpreview_urls.json").read_text())


def fetch(brand: str, idx: int, url: str) -> dict:
    dest = ROOT / brand / f"{idx:02d}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.dpreview.com/sample-galleries/"})
        with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
            fh.write(resp.read())
    with Image.open(dest) as img:
        exif = img.getexif()
        return {
            "brand": brand,
            "file": str(dest),
            "bytes": dest.stat().st_size,
            "size": f"{img.width}x{img.height}",
            "make": (exif.get(0x010F) or "").strip(),
            "model": (exif.get(0x0110) or "").strip(),
        }


def main() -> None:
    jobs = [(b, i + 1, u) for b, urls in SET.items() for i, u in enumerate(urls)]
    rows = []
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        for row in pool.map(lambda a: fetch(*a), jobs):
            rows.append(row)
            print(f"{row['brand']:<11} {row['bytes']/1e6:5.1f}MB {row['size']:<11} {row['make']}/{row['model']}")
    with (ROOT / "manifest.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    total = sum(r["bytes"] for r in rows)
    print(f"\n{len(rows)} file, {total/1e6:.0f} MB, {len({r['brand'] for r in rows})} merek")
    print("tanpa EXIF:", sorted({r["brand"] for r in rows if not r["make"]}) or "tidak ada")


if __name__ == "__main__":
    main()
