"""The signature engine: everything here is computed from the uploaded bytes.

Four things, per PLAN v2:
  1. EXIF identity      -- Pillow getexif(), missing/inconsistent flags
  2. Quantization pair  -- Pillow table 0/1 (64+64 values), cosine similarity vs references,
                           fingerprint hex = sha256 over both tables normalised to their own max
  3. Encoder fingerprint-- APP markers, subsampling, restart interval, DHT count, IJG table match
  4. Edit traces        -- embedded thumbnail vs main tables, mismatched table pair, Software
                           after capture date, MakerNote missing while Make is present
No PRNU, no PCE, no hot pixels, no invented camera data.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from datetime import datetime
from typing import Any

from PIL import Image

from . import jpeg as jpeg_markers

WEIGHTS = {"exif": 0.45, "qtable": 0.35, "encoder": 0.20}

EXIF_TAGS = {
    "make": (0x010F, "Make"),
    "model": (0x0110, "Model"),
    "software": (0x0131, "Software"),
    "datetime": (0x0132, "DateTime"),
    "lens": (0xA434, "LensModel"),
    "serial": (0xA431, "BodySerialNumber"),
    "datetime_original": (0x9003, "DateTimeOriginal"),
    "makernote": (0x927C, "MakerNote"),
}


def cosine(a: list[int], b: list[int]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return round(dot / norm, 4) if norm else 0.0


def similarity(a: list[int], b: list[int]) -> float:
    """Cosine of the tables times a scale term.

    Cosine alone cannot separate JPEG qualities: IJG tables are all near-parallel vectors
    (measured cos ~0.999 between q75 and q92). Multiplying by 1 - |mean_a - mean_b| / max
    keeps the shape comparison and adds the magnitude that actually encodes quality.
    """
    cos = cosine(a, b)
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    scale = 1 - abs(mean_a - mean_b) / max(mean_a, mean_b, 1)
    return round(max(0.0, min(1.0, cos * scale)), 4)


def fingerprint(qtable: list[int], chroma: list[int]) -> str:
    """sha256 over both tables, each normalised by its own maximum (so scale-free)."""

    def norm(values: list[int]) -> list[float]:
        peak = max(values) or 1
        return [round(v / peak, 4) for v in values]

    payload = json.dumps({"luma": norm(qtable), "chroma": norm(chroma)}, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _standard_tables(quality: int) -> tuple[list[int], list[int]]:
    """IJG tables as this libjpeg build writes them for a given quality."""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (128, 128, 128)).save(buf, "JPEG", quality=quality)
    buf.seek(0)
    with Image.open(buf) as probe:
        tables = probe.quantization
    luma = list(tables[0])
    chroma = list(tables.get(1, tables[0]))
    return luma, chroma


def estimate_quality(luma: list[int], chroma: list[int]) -> tuple[int, float]:
    """Closest IJG quality by summed absolute difference over the 128 values."""
    best = (75, 1e9)
    for quality in range(1, 101):
        ref_l, ref_c = _standard_tables(quality)
        diff = sum(abs(a - b) for a, b in zip(luma, ref_l, strict=False))
        diff += sum(abs(a - b) for a, b in zip(chroma, ref_c, strict=False))
        if diff < best[1]:
            best = (quality, diff)
    return best[0], round(best[1] / 128, 2)


def identity(img: Image.Image) -> dict[str, Any]:
    """EXIF identity of an opened image. Bytes are decoded, empty tags become None.

    Public so tools (the dataset importer) read EXIF the same way the analyzer does.
    """
    exif = img.getexif()
    out: dict[str, Any] = {}
    for key, (tag, _) in EXIF_TAGS.items():
        value = exif.get(tag)
        if value is None:
            try:
                value = exif.get_ifd(0x8769).get(tag)
            except Exception:  # noqa: BLE001 - malformed EXIF is data, not a crash
                value = None
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace").strip("\x00").strip()
        out[key] = value if value not in ("", None) else None
    return out


def qtable_pair(img: Image.Image) -> tuple[list[int], list[int], bool]:
    """Luma and chroma quantization tables, plus whether the file carried both.

    A grayscale JPEG has one table; the pair is completed with that same table, which is how
    the analyzer already scores such files. `complete` tells tools if that fallback was used.
    """
    tables = img.quantization or {}
    luma = list(tables.get(0, []))
    chroma = list(tables.get(1, tables[0] if luma else []))
    return luma, chroma, len(tables) >= 2 and bool(luma)


def _exif_dict(img: Image.Image, raw: bytes) -> tuple[dict[str, Any], Any]:
    return identity(img), _thumbnail_qtable(raw)


def _thumbnail_qtable(raw: bytes) -> dict[str, Any]:
    """Find an embedded JPEG thumbnail in the EXIF block and read its tables."""
    start = raw.find(b"Exif\x00\x00")
    if start < 0:
        return {"present": False, "luma": None}
    blob = raw[start:]
    second = blob.find(b"\xff\xd8\xff", 6)
    if second < 0:
        return {"present": False, "luma": None}
    try:
        with Image.open(io.BytesIO(blob[second:])) as thumb:
            tables = thumb.quantization
            return {"present": True, "luma": list(tables[0])}
    except Exception:  # noqa: BLE001
        return {"present": False, "luma": None}


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def analyze(raw: bytes, references: list[dict]) -> dict:
    """Return the full signature payload plus the top-3 matches. Pure function of the bytes."""
    img = Image.open(io.BytesIO(raw))
    exif_raw = img.info.get("exif", b"")
    exif, thumb = _exif_dict(img, exif_raw)
    exif["has_thumbnail"] = thumb["present"]
    markers = jpeg_markers.scan(raw)

    luma, chroma, _ = qtable_pair(img)
    if not luma:
        luma = _standard_tables(75)[0]
        chroma = _standard_tables(75)[1]

    quality, table_delta = estimate_quality(luma, chroma)
    std_luma, std_chroma = _standard_tables(quality)
    ijg_exact = luma == std_luma and chroma == std_chroma
    pair_mismatch = _pair_quality(luma) != _pair_quality(chroma)

    encoder_guess, encoder_confidence, encoder_note = _encoder(markers, exif, ijg_exact, quality, table_delta)

    exif_fields, exif_score = _exif_fields(exif, markers)
    traces = _edit_traces(exif, thumb, luma, pair_mismatch, markers)

    scored = _matches(luma, chroma, references, encoder_guess, exif)
    best = scored[0] if scored else None
    qtable_score = round(best["similarity"], 4) if best else 0.0
    encoder_score = {"kuat": 1.0, "sedang": 0.6, "lemah": 0.25}[encoder_confidence]

    components = [
        {
            "key": "exif",
            "label": "Identitas EXIF",
            "score": round(exif_score, 2),
            "weight": WEIGHTS["exif"],
            "contribution": round(exif_score * WEIGHTS["exif"], 4),
            "reason": _exif_reason(exif),
        },
        {
            "key": "qtable",
            "label": "Kemiripan tabel kuantisasi",
            "score": qtable_score,
            "weight": WEIGHTS["qtable"],
            "contribution": round(qtable_score * WEIGHTS["qtable"], 4),
            "reason": (
                f"kemiripan tertinggi {qtable_score:.3f} terhadap "
                f"{best['label'] if best else 'tidak ada referensi'}"
            ),
        },
        {
            "key": "encoder",
            "label": "Fingerprint encoder",
            "score": encoder_score,
            "weight": WEIGHTS["encoder"],
            "contribution": round(encoder_score * WEIGHTS["encoder"], 4),
            "reason": encoder_note,
        },
    ]
    confidence = round(sum(c["contribution"] for c in components), 4)
    label, text = _verdict(confidence, best["label"] if best else None, encoder_guess)

    return {
        "signature": {
            "exif": exif_fields,
            "qtable": {"luma": luma, "chroma": chroma},
            "fingerprint_hex": fingerprint(luma, chroma),
            "encoder": {
                "guess": encoder_guess,
                "confidence": encoder_confidence,
                "subsampling": markers["subsampling"],
                "restart_interval": markers["restart_interval"],
                "huffman_tables": markers["huffman_tables"],
                "app_markers": markers["app"],
                "note": encoder_note,
            },
            "edit_traces": traces,
            "components": components,
        },
        "matches": scored[:3],
        "verdict": {
            "label": label,
            "text": text,
            "confidence": confidence,
            "camera_guess": best["label"] if best else "tidak ada di tabel referensi",
            "encoder_guess": encoder_guess,
        },
        "meta": {
            "quality": quality,
            "ijg_exact": ijg_exact,
            "table_delta": table_delta,
            "width": img.width,
            "height": img.height,
        },
    }


def _pair_quality(table: list[int]) -> int:
    return estimate_quality(table, table)[0]


def _encoder(markers: dict, exif: dict, ijg_exact: bool, quality: int, delta: float):
    apps = markers["app"]
    if any("APP14/Adobe" in a for a in apps):
        return (
            "Adobe (penanda APP14)",
            "kuat",
            "APP14 dengan penanda Adobe; tabel kuantisasi Adobe, bukan IJG.",
        )
    software = (exif.get("software") or "").lower()
    if any(name in software for name in ("photoshop", "lightroom", "adobe")):
        return (
            "Adobe (tag Software)",
            "sedang",
            f"Tag Software menyebut '{exif.get('software')}'; penanda APP14 tidak ada.",
        )
    if any(name in software for name in ("apple", "ios", "iphone")):
        return (
            "Apple / iOS (tag Software)",
            "sedang",
            f"Tag Software '{exif.get('software')}' menunjuk pipeline Apple; tidak diverifikasi vendor.",
        )
    if ijg_exact:
        return (
            "libjpeg / libjpeg-turbo (tabel IJG)",
            "kuat" if delta < 0.5 else "sedang",
            f"128 nilai tabel identik dengan tabel IJG kualitas {quality}; libjpeg dan "
            "libjpeg-turbo tidak dibedakan oleh tabel.",
        )
    return (
        "libjpeg-compatible (tabel mendekati IJG)",
        "sedang" if delta < 6 else "lemah",
        f"Tabel terdekat IJG q{quality} dengan selisih rata-rata {delta} per nilai; "
        "kemungkinan re-encode atau aplikasi lain.",
    )


def _exif_fields(exif: dict, markers: dict) -> tuple[dict, float]:
    fields = []
    present = sum(1 for k in ("make", "model", "lens", "software", "datetime_original") if exif.get(k))
    for key, (_, tag_name) in EXIF_TAGS.items():
        if key == "datetime":
            continue
        value = exif.get(key)
        state = "ok" if value else "missing"
        if key == "software" and value and exif.get("datetime_original"):
            state = "ok"
        if key == "makernote":
            value = "ada" if value else None
        fields.append({"tag": tag_name, "value": value, "state": state})

    if exif.get("make") and not exif.get("makernote"):
        for field in fields:
            if field["tag"] == "MakerNote":
                field["state"] = "inconsistent"

    score = 0.15
    if present >= 4:
        score = 0.95
    elif present >= 2:
        score = 0.6
    elif present == 1:
        score = 0.3
    if not exif.get("make"):
        score = min(score, 0.15)
    return (
        {
            "fields": fields,
            "make": exif.get("make"),
            "model": exif.get("model"),
            "lens": exif.get("lens"),
            "software": exif.get("software"),
            "serial": exif.get("serial"),
            "datetime_original": exif.get("datetime_original"),
            "has_thumbnail": bool(exif.get("has_thumbnail", False)),
            "makernote_present": bool(exif.get("makernote")),
        },
        score,
    )


def _edit_traces(exif: dict, thumb: dict, luma: list[int], pair_mismatch: bool, markers: dict):
    traces = []

    if not thumb["present"]:
        traces.append(
            {
                "key": "thumbnail",
                "label": "Thumbnail EXIF",
                "detected": False,
                "detail": (
                    "Tidak ada thumbnail tertanam — normal untuk hasil re-encode atau "
                    "aplikasi yang membuang thumbnail."
                ),
            }
        )
    else:
        same = thumb["luma"] == luma
        traces.append(
            {
                "key": "thumbnail",
                "label": "Thumbnail vs gambar utama",
                "detected": not same,
                "detail": "Tabel kuantisasi thumbnail sama dengan gambar utama."
                if same
                else (
                    "Tabel thumbnail berbeda dari gambar utama: thumbnail berasal dari versi lain berkas ini."
                ),
            }
        )

    traces.append(
        {
            "key": "double_compression",
            "label": "Kompresi ganda / pasangan tabel",
            "detected": pair_mismatch,
            "detail": "Tabel luma dan kroma setara kualitas yang sama."
            if not pair_mismatch
            else (
                "Kualitas tabel luma dan kroma tidak sepadan — indikasi dua tahap kompresi "
                "atau editor berbeda."
            ),
        }
    )

    captured, modified = _dt(exif.get("datetime_original")), _dt(exif.get("datetime"))
    software_after = bool(exif.get("software")) and bool(modified and captured and modified > captured)
    traces.append(
        {
            "key": "software_after_capture",
            "label": "Software setelah waktu rekam",
            "detected": software_after,
            "detail": (
                f"DateTime ({exif.get('datetime')}) lebih baru dari DateTimeOriginal "
                f"({exif.get('datetime_original')}) dengan Software '{exif.get('software')}'."
                if software_after
                else "Tidak ada bukti penyuntingan setelah waktu rekam."
            ),
        }
    )

    missing_makernote = bool(exif.get("make")) and not exif.get("makernote")
    traces.append(
        {
            "key": "makernote",
            "label": "MakerNote vendor",
            "detected": missing_makernote,
            "detail": "MakerNote ada."
            if not missing_makernote
            else "Tag Make ada tetapi MakerNote hilang — metadata bisa sudah dilewati editor.",
        }
    )

    if "APP1/EXIF-XMP" in markers["app"] and not exif.get("make"):
        traces.append(
            {
                "key": "xmp_without_exif",
                "label": "XMP tanpa EXIF",
                "detected": True,
                "detail": "Blok XMP ada tanpa tag kamera EXIF — jejak pipeline pengolah.",
            }
        )
    return traces


def _matches(
    luma: list[int], chroma: list[int], references: list[dict], encoder_guess: str, exif: dict
) -> list[dict]:
    scored = []
    for ref in references:
        sim = round((similarity(luma, ref["luma"]) + similarity(chroma, ref["chroma"])) / 2, 4)
        same_make = (exif.get("make") or "").strip().lower() == ref["make"].lower()
        same_model = (exif.get("model") or "").strip().lower() == ref["model"].lower()
        reason = [f"kemiripan tabel {sim:.3f}"]
        if same_model:
            reason.append("model EXIF sama persis")
        elif same_make:
            reason.append("merek EXIF sama")
        if encoder_guess.split(" ")[0] in ref["encoder"]:
            reason.append("encoder sejalan")
        scored.append(
            {
                "reference_id": ref["id"],
                "label": ref["label"],
                "make": ref["make"],
                "model": ref["model"],
                "encoder": ref["encoder"],
                "note": ref["note"],
                "similarity": sim,
                "explanation": "; ".join(reason),
            }
        )
    scored.sort(key=lambda item: item["similarity"], reverse=True)
    for index, item in enumerate(scored, start=1):
        item["rank"] = index
    return scored


def _exif_reason(exif: dict) -> str:
    if exif.get("make") and exif.get("model"):
        return f"Make/Model terbaca: {exif['make']} {exif['model']} (EXIF dapat dipalsukan)."
    if exif.get("make"):
        return f"Hanya Make yang terbaca: {exif['make']}."
    return "Tidak ada tag kamera — EXIF dihapus atau tidak pernah ditulis."


def _verdict(confidence: float, best_label: str | None, encoder: str) -> tuple[str, str]:
    camera = best_label or "tidak ada di tabel referensi"
    if confidence >= 0.75:
        return (
            "kuat",
            f"Signature paling mungkin dari {camera} dengan encoder {encoder}.",
        )
    if confidence >= 0.55:
        return (
            "sedang",
            f"Indikasi ke {camera} ({encoder}); bukti belum saling menguatkan penuh.",
        )
    if confidence >= 0.45:
        return (
            "lemah",
            f"Petunjuk ke {camera}, tetapi komponen saling bertentangan — perlakukan sebagai dugaan.",
        )
    return (
        "tidak dapat dipastikan",
        "Metadata dan tabel kuantisasi tidak cukup untuk menetapkan kamera; "
        "hanya encoder yang bisa ditegaskan.",
    )
