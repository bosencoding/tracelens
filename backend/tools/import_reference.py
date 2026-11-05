#!/usr/bin/env python3
"""Import camera reference rows from any folder of JPEGs.

Groups files by EXIF (make, model), picks a representative quantization-table pair
(per-element median), and writes one reference_cameras row per group. Idempotent.

    uv run python -m tools.import_reference --dir ~/datasets/SOCRatES --dry-run
    uv run python -m tools.import_reference --list files.txt --label-prefix soc

EXIF and table reading come from `app.analyze` (identity / qtable_pair), so the importer
sees exactly the fields and tables the analyzer scores at upload time.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app import analyze, db, jpeg
from app.config import settings

EXTS = {".jpg", ".jpeg"}
COLUMNS = (
    "id",
    "label",
    "make",
    "model",
    "encoder",
    "note",
    "qtable_luma",
    "qtable_chroma",
    "fingerprint_hex",
    "subsampling",
    "what_if",
)


def collect(args) -> list[Path]:
    if args.list:
        text = Path(args.list).read_text()
        return [Path(line.strip()) for line in text.splitlines() if line.strip()]
    root = Path(args.dir).expanduser()
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in EXTS and p.is_file())


def clean(value: str | None) -> str:
    """EXIF strings arrive NUL-padded or space-padded ('Sigma BF\\x00\\x00', 'PENTAX …   ')."""
    if not value:
        return ""
    return " ".join(value.replace("\x00", " ").split())


def group_key(make: str, model: str) -> tuple[str, str]:
    """Compare case- and whitespace-insensitively; the label keeps the original spelling."""
    return (make.casefold(), model.casefold())


SCANNER_MAKES = ("noritsu", "frontier", "qss", "ez controller")


def is_scanner(make: str, model: str) -> bool:
    """Lab scanners write plausible EXIF too — they must never look like a camera row."""
    probe = f"{make} {model}".casefold()
    return any(marker in probe for marker in SCANNER_MAKES)


def read_one(path: Path, max_bytes: int) -> dict | None:
    """One file -> its identity and tables, or {'skip': reason}. Never raises.

    max_bytes = 0 means no size cap: a reference import is not an API upload.
    """
    try:
        if max_bytes and path.stat().st_size > max_bytes:
            return {"skip": f"lebih dari {max_bytes // 1024 // 1024} MB"}
        raw = path.read_bytes()
    except OSError as exc:
        return {"skip": f"tidak terbaca: {exc}"}

    try:
        with Image.open(io.BytesIO(raw)) as img:
            exif = analyze.identity(img)
            luma, chroma, complete = analyze.qtable_pair(img)
    except (OSError, UnidentifiedImageError) as exc:
        return {"skip": f"bukan JPEG terbaca: {exc}"}
    if not complete:
        return {"skip": "bukan JPEG berwarna / tabel kuantisasi tidak lengkap"}

    make = clean(exif.get("make"))
    model = clean(exif.get("model"))
    quality, delta = analyze.estimate_quality(luma, chroma)
    return {
        "make": make or "TANPA-MAKE",
        "model": model or f"TANPA-EXIF/{path.parent.name}",
        "raw_make": make,
        "raw_model": model,
        "folder": path.parent.name,
        "luma": luma,
        "chroma": chroma,
        "subsampling": jpeg.scan(raw)["subsampling"],
        "encoder": (f"libjpeg (tabel IJG q{quality})" if delta <= 2 else "tabel non-IJG (kamera/Adobe)"),
    }


def median(values: list[int]) -> int:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) // 2


def median_table(rows: list[list[int]]) -> list[int]:
    """Per-position median, so a table stays 64 values wide."""
    width = len(rows[0])
    return [median([row[i] for row in rows]) for i in range(width)]


def group(files: list[Path], max_bytes: int) -> tuple[dict[tuple[str, str], list[dict]], list[str]]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    skipped: list[str] = []
    for path in files:
        item = read_one(path, max_bytes)
        if not item or "skip" in item:
            skipped.append(f"{path}: {item['skip'] if item else 'tidak dikenal'}")
            continue
        groups[group_key(item["make"], item["model"])].append(item)
    return groups, skipped


def display_identity(items: list[dict]) -> tuple[str, str, str]:
    """Most common original spelling for a group, plus the kind marker (camera/scan/no-exif)."""
    make = Counter(item["raw_make"] for item in items if item["raw_make"]).most_common(1)
    model = Counter(item["raw_model"] for item in items if item["raw_model"]).most_common(1)
    make_text = make[0][0] if make else ""
    model_text = model[0][0] if model else ""

    if not make_text:
        return "TANPA-MAKE", f"TANPA-EXIF/{items[0]['folder']}", "tanpa-exif"
    if is_scanner(make_text, model_text):
        return make_text, model_text, "scan"
    return make_text, model_text, "kamera"


def build_rows(groups, prefix: str) -> list[dict]:
    rows = []
    for _, items in sorted(groups.items()):
        make, model, kind = display_identity(items)
        luma = median_table([item["luma"] for item in items])
        chroma = median_table([item["chroma"] for item in items])
        subsampling = Counter(item["subsampling"] for item in items).most_common(1)[0][0]
        encoder = Counter(item["encoder"] for item in items).most_common(1)[0][0]
        digest = hashlib.sha1(f"{make}|{model}".casefold().encode()).hexdigest()[:8].upper()

        if kind == "tanpa-exif":
            label = model
            what_if = (
                "Tanpa Make/Model: ini hanya kemiripan tabel, bukan identitas kamera. "
                "Jangan dipakai untuk menyimpulkan model."
            )
        elif kind == "scan":
            label = f"SCAN/{make} {model}".strip()
            what_if = (
                "Tabel berasal dari scanner lab (bukan sensor kamera); cocok berarti berkas "
                "melewati pemindaian, bukan dipotret dengan kamera ini."
            )
        else:
            label = f"{prefix} {make} {model}".strip()
            what_if = "Tabel dataset eksternal; verdict bergantung kecocokan tabel, bukan EXIF."

        rows.append(
            {
                "id": f"REF-{digest}",
                "label": label,
                "make": make,
                "model": model,
                "encoder": encoder,
                "note": (
                    f"Impor dataset: {len(items)} sampel, subsampling dominan {subsampling}, jenis {kind}."
                ),
                "qtable_luma": db.dumps(luma),
                "qtable_chroma": db.dumps(chroma),
                "fingerprint_hex": analyze.fingerprint(luma, chroma),
                "subsampling": subsampling,
                "what_if": what_if,
                "_samples": len(items),
                "_kind": kind,
                "_label": label,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dir", help="folder rekursif berisi JPEG")
    source.add_argument("--list", help="file teks berisi path JPEG per baris")
    parser.add_argument("--label-prefix", default="", help="awalan label, mis. 'socrates'")
    parser.add_argument(
        "--max-mb",
        type=int,
        default=0,
        help="batas ukuran per berkas dalam MB; 0 = tanpa batas (default). "
        "Impor referensi bukan upload API, jadi batas upload tidak berlaku.",
    )
    parser.add_argument("--dry-run", action="store_true", help="cetak rencana, jangan tulis DB")
    parser.add_argument("--update", action="store_true", help="timpa baris dengan id yang sama")
    args = parser.parse_args()

    # Hasselblad-class files (150 MP) trip Pillow's bomb warning; we only read tables, not pixels.
    warnings.simplefilter("ignore", Image.DecompressionBombWarning)

    files = collect(args)
    if not files:
        print("tidak ada JPEG ditemukan", file=sys.stderr)
        return 1

    max_bytes = args.max_mb * 1024 * 1024 if args.max_mb > 0 else 0
    groups, skipped = group(files, max_bytes)
    rows = build_rows(groups, args.label_prefix)

    # dry-run must not create the database file either
    db_ready = settings().db_path.exists()
    if not args.dry_run and not db_ready:
        db.init_db()
        db_ready = True
    existing = {r["id"] for r in db.rows("SELECT id FROM reference_cameras")} if db_ready else set()

    plan: Counter = Counter()
    for row in rows:
        state = "baru" if row["id"] not in existing else ("ditimpa" if args.update else "tetap")
        plan[state] += 1
        print(
            f"{state:9} {row['id']:<16} {row['_label'][:44]:<44} n={row['_samples']:<3} "
            f"{row['subsampling']:<8} {row['_kind']:<10} {row['fingerprint_hex'][:12]}"
        )
        if state in {"baru", "ditimpa"} and not args.dry_run:
            placeholders = ",".join("?" * len(COLUMNS))
            db.execute(
                f"INSERT INTO reference_cameras ({','.join(COLUMNS)}) VALUES ({placeholders})"
                " ON CONFLICT(id) DO UPDATE SET "
                + ", ".join(f"{c}=excluded.{c}" for c in COLUMNS if c != "id"),
                tuple(row[column] for column in COLUMNS),
            )

    kinds = Counter(row["_kind"] for row in rows)
    summary = " ".join(f"{k}={v}" for k, v in plan.items())
    print(
        f"\nfile={len(files)} grup={len(rows)} berkas_dilewati={len(skipped)} {summary} "
        f"| kamera={kinds['kamera']} scan={kinds['scan']} tanpa-exif={kinds['tanpa-exif']}"
    )
    for line in skipped:
        print(f"  lewat {line}")
    if kinds["tanpa-exif"]:
        print(
            f"  PERINGATAN: {kinds['tanpa-exif']} grup tanpa Make/Model diberi label "
            "'TANPA-EXIF/<folder>' — bukan referensi kamera."
        )
    if kinds["scan"]:
        print(
            f"  PERINGATAN: {kinds['scan']} grup berasal dari scanner lab (label 'SCAN/…') — "
            "bukan sensor kamera."
        )
    if args.dry_run:
        print("dry-run: tidak ada perubahan DB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
