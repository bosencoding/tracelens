"""Idempotent seed: 3 synthetic reference profiles + 7 synthetic JPEGs built from one scene.

Nothing here is a real camera profile. Every row is labelled "contoh" in the UI.
Run: uv run python -m app.seed
"""

from __future__ import annotations

import hashlib
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import analyze, db
from .config import settings

SIZE = (1200, 800)
WIB = timezone(timedelta(hours=7), "WIB")

REFERENCES = [
    {
        "id": "REF-A",
        "label": "Contoh Referensi A — mirrorless q92 4:4:4",
        "make": "Contoh Kamera",
        "model": "Ref-A Mark I",
        "encoder": "libjpeg (tabel IJG q92)",
        "note": "Profil contoh dari encode Pillow quality 92 subsampling 4:4:4.",
        "quality": 92,
        "subsampling": 0,
        "what_if": (
            "Jika cocok: berkas paling mungkin keluar dari pipeline kualitas tinggi tanpa subsampling kroma."
        ),
    },
    {
        "id": "REF-B",
        "label": "Contoh Referensi B — ponsel q75 4:2:0",
        "make": "Contoh Ponsel",
        "model": "Ref-B Phone",
        "encoder": "libjpeg (tabel IJG q75)",
        "note": "Profil contoh dari encode Pillow quality 75 subsampling 4:2:0.",
        "quality": 75,
        "subsampling": 2,
        "what_if": "Jika cocok: berkas konsisten dengan pipeline ponsel yang menghemat bitrate kroma.",
    },
    {
        "id": "REF-C",
        "label": "Contoh Referensi C — editor q80 4:4:4",
        "make": "Contoh Editor",
        "model": "Ref-C Desktop",
        "encoder": "Adobe-style (contoh)",
        "note": "Profil contoh untuk pipeline editor desktop; bukan tabel vendor nyata.",
        "quality": 80,
        "subsampling": 0,
        "what_if": "Jika cocok: berkas pernah lewat editor desktop, bukan langsung dari kamera.",
    },
]

FIXTURES = [
    {
        "id": "EVD-CONTOH-A",
        "filename": "contoh_kamera_a_kualitas_tinggi.jpg",
        "quality": 92,
        "subsampling": 0,
        "exif": {
            "make": "Contoh Kamera",
            "model": "Ref-A Mark I",
            "lens": "Contoh 35mm f/1.8",
            "software": "Pillow contoh 1.0",
            "serial": "SN-CONTOH-A-0001",
            "captured": "2025:10:14 13:10:00",
        },
        "note": "EXIF lengkap, q92 4:4:4 — kasus paling mudah.",
    },
    {
        "id": "EVD-CONTOH-B",
        "filename": "contoh_ponsel_kualitas_sedang.jpg",
        "quality": 75,
        "subsampling": 2,
        "exif": {
            "make": "Contoh Ponsel",
            "model": "Ref-B Phone",
            "lens": "Contoh wide 26mm",
            "software": "Pillow contoh 1.0",
            "serial": "SN-CONTOH-B-0002",
            "captured": "2025:10:14 13:22:00",
        },
        "note": "EXIF lengkap, q75 4:2:0 — fingerprint khas ponsel.",
    },
    {
        "id": "EVD-CONTOH-C",
        "filename": "contoh_editor_desktop.jpg",
        "quality": 80,
        "subsampling": 0,
        "exif": {
            "make": "Contoh Editor",
            "model": "Ref-C Desktop",
            "lens": None,
            "software": "Pillow contoh 1.0",
            "serial": None,
            "captured": "2025:10:14 13:30:00",
        },
        "note": "Mirip profil C; tanpa lens dan serial.",
    },
    {
        "id": "EVD-CONTOH-D",
        "filename": "contoh_exif_dihapus.jpg",
        "quality": 85,
        "subsampling": 2,
        "exif": None,
        "note": "EXIF sengaja dihapus: harus jatuh ke band 'tidak dapat dipastikan'.",
    },
    {
        "id": "EVD-CONTOH-E",
        "filename": "contoh_exif_palsu.jpg",
        "quality": 92,
        "subsampling": 0,
        "exif": {
            "make": "Canon",
            "model": "Canon EOS R5",
            "lens": "RF24-105mm F4 L IS USM",
            "software": "Adobe Photoshop 25.1",
            "serial": "SN-PALSU-0005",
            "captured": "2025:10:14 13:10:00",
            "modified": "2025:10:14 18:45:00",
        },
        "note": "EXIF mengklaim Canon + Software Photoshop setelah waktu rekam.",
    },
    {
        "id": "EVD-CONTOH-F",
        "filename": "contoh_pasangan_tabel_tak_sepadan.jpg",
        "quality": 90,
        "chroma_quality": 55,
        "subsampling": 2,
        "exif": {
            "make": "Contoh Ponsel",
            "model": "Ref-B Phone",
            "lens": "Contoh wide 26mm",
            "software": "Pillow contoh 1.0",
            "serial": "SN-CONTOH-F-0006",
            "captured": "2025:10:14 13:40:00",
        },
        "note": "Luma q90 + kroma q55: memicu jejak kompresi ganda.",
    },
    {
        "id": "EVD-CONTOH-G",
        "filename": "contoh_tanpa_makernote.jpg",
        "quality": 70,
        "subsampling": 2,
        "exif": {
            "make": "Contoh Ponsel",
            "model": "Ref-B Phone",
            "lens": None,
            "software": None,
            "serial": None,
            "captured": "2025:10:14 13:50:00",
            "no_makernote": True,
        },
        "note": "Make ada, MakerNote tidak — jejak pembersih metadata.",
    },
]


def scene() -> Image.Image:
    """One synthetic photo, drawn with Pillow: horizon, grid, two shapes, a label."""
    img = Image.new("RGB", SIZE, (28, 42, 66))
    draw = ImageDraw.Draw(img)
    for y in range(SIZE[1]):
        shade = int(28 + 120 * (y / SIZE[1]))
        draw.line([(0, y), (SIZE[0], y)], fill=(shade // 2, shade // 2 + 20, shade))
    draw.rectangle([80, 520, 520, 740], fill=(196, 122, 46), outline=(240, 200, 120), width=6)
    draw.ellipse([700, 160, 1060, 520], fill=(36, 110, 170), outline=(140, 200, 255), width=6)
    for x in range(0, SIZE[0], 120):
        draw.line([(x, 0), (x, SIZE[1])], fill=(52, 66, 92), width=1)
    for y in range(0, SIZE[1], 120):
        draw.line([(0, y), (SIZE[0], y)], fill=(52, 66, 92), width=1)
    font = ImageFont.load_default(size=34)
    draw.text((90, 120), "TRACELENS — GAMBAR SINTETIS", font=font, fill=(240, 244, 255))
    draw.text(
        (90, 170),
        "bukan foto kamera nyata",
        font=ImageFont.load_default(size=24),
        fill=(200, 214, 236),
    )
    return img


def exif_bytes(spec: dict | None) -> bytes:
    if spec is None:
        return b""
    exif = Image.Exif()
    exif[0x010F] = spec["make"]
    exif[0x0110] = spec["model"]
    if spec.get("lens"):
        exif[0xA434] = spec["lens"]
    if spec.get("software"):
        exif[0x0131] = spec["software"]
    if spec.get("serial"):
        exif[0xA431] = spec["serial"]
    exif.get_ifd(0x8769)[0x9003] = spec["captured"]
    if spec.get("modified") and spec.get("software"):
        exif[0x0132] = spec["modified"]
    else:
        exif[0x0132] = spec["captured"]
    if not spec.get("no_makernote"):
        exif.get_ifd(0x8769)[0x927C] = b"TraceLens synthetic makernote"
    return exif.tobytes()


def encode(
    img: Image.Image, quality: int, subsampling: int, exif: bytes, chroma_quality: int | None = None
) -> bytes:
    buf = io.BytesIO()
    if chroma_quality is None:
        img.save(buf, "JPEG", quality=quality, subsampling=subsampling, exif=exif, optimize=False)
    else:
        luma_table = analyze._standard_tables(quality)[0]
        chroma_table = analyze._standard_tables(chroma_quality)[1]
        img.save(
            buf,
            "JPEG",
            qtables=[luma_table, chroma_table],
            subsampling=subsampling,
            exif=exif,
            optimize=False,
        )
    return buf.getvalue()


def seed_references() -> list[dict]:
    base = scene()
    rows = []
    db.execute("delete from matches")
    db.execute("delete from reference_cameras")
    for spec in REFERENCES:
        raw = encode(base, spec["quality"], spec["subsampling"], b"")
        with Image.open(io.BytesIO(raw)) as probe:
            tables = probe.quantization
        luma = list(tables[0])
        chroma = list(tables.get(1, tables[0]))
        db.execute(
            """insert into reference_cameras (id, label, make, model, encoder, note, qtable_luma,
                   qtable_chroma, fingerprint_hex, subsampling, what_if)
               values (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                spec["id"],
                spec["label"],
                spec["make"],
                spec["model"],
                spec["encoder"],
                spec["note"],
                db.dumps(luma),
                db.dumps(chroma),
                analyze.fingerprint(luma, chroma),
                analyze.jpeg_markers.scan(raw)["subsampling"],
                spec["what_if"],
            ),
        )
        rows.append({"id": spec["id"], "luma": luma, "chroma": chroma, **spec})
    return rows


def main() -> None:
    settings()
    db.init_db()
    base = scene()
    references = seed_references()

    db.execute("delete from evidence")
    for fixture in FIXTURES:
        raw = encode(
            base,
            fixture["quality"],
            fixture["subsampling"],
            exif_bytes(fixture["exif"]),
            fixture.get("chroma_quality"),
        )
        path = Path(settings().upload_dir) / f"{fixture['id']}.jpg"
        path.write_bytes(raw)
        result = analyze.analyze(raw, references)
        verdict = result["verdict"]
        now = datetime(2025, 10, 14, 13, 0, tzinfo=WIB).isoformat(timespec="seconds")
        digest = hashlib.sha256(raw).hexdigest()
        db.execute(
            """insert or replace into evidence (id, filename, byte_size, mime_type, sha256,
                   stored_path, uploaded_at, verdict_label, verdict_text, confidence, camera_guess,
                   encoder_guess, width, height) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fixture["id"],
                fixture["filename"],
                len(raw),
                "image/jpeg",
                digest,
                str(path),
                now,
                verdict["label"],
                verdict["text"],
                verdict["confidence"],
                verdict["camera_guess"],
                verdict["encoder_guess"],
                result["meta"]["width"],
                result["meta"]["height"],
            ),
        )
        sig = result["signature"]
        db.execute(
            """insert or replace into signatures (evidence_id, exif_json, qtable_luma, qtable_chroma,
                   fingerprint_hex, subsampling, restart_interval, huffman_tables, app_markers,
                   edit_traces, components, computed_at)
               values (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fixture["id"],
                db.dumps(sig["exif"]),
                db.dumps(sig["qtable"]["luma"]),
                db.dumps(sig["qtable"]["chroma"]),
                sig["fingerprint_hex"],
                sig["encoder"]["subsampling"],
                sig["encoder"]["restart_interval"],
                sig["encoder"]["huffman_tables"],
                db.dumps(
                    {
                        "guess": sig["encoder"]["guess"],
                        "confidence": sig["encoder"]["confidence"],
                        "note": sig["encoder"]["note"],
                        "markers": sig["encoder"]["app_markers"],
                    }
                ),
                db.dumps(sig["edit_traces"]),
                db.dumps(sig["components"]),
                now,
            ),
        )
        for match in result["matches"]:
            db.execute(
                "insert into matches (evidence_id, rank, reference_id, similarity, explanation)"
                " values (?,?,?,?,?)",
                (
                    fixture["id"],
                    match["rank"],
                    match["reference_id"],
                    match["similarity"],
                    match["explanation"],
                ),
            )
        print(
            f"{fixture['id']:<14} {verdict['label']:<22} conf={verdict['confidence']:.3f} "
            f"enc={sig['encoder']['guess']}"
        )

    print(f"references: {len(references)}, fixtures: {len(FIXTURES)}")
    print(f"note: {FIXTURES[0]['note']}")


if __name__ == "__main__":
    main()
