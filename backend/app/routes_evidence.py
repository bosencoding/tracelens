"""Evidence CRUD: upload, list, read, signature, matches, delete."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from . import analyze, db, runtime_settings
from .config import settings
from .errors import ApiError, NotFound, TooLarge, UnsupportedMedia
from .models import (
    EncoderInfo,
    EvidenceDetail,
    EvidenceOut,
    MatchOut,
    QTables,
    SignatureOut,
)

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

ALLOWED_MIME = {"image/jpeg", "image/jpg"}
ALLOWED_EXT = {".jpg", ".jpeg"}


def _out(row: dict) -> EvidenceOut:
    return EvidenceOut(
        id=row["id"],
        filename=row["filename"],
        byte_size=row["byte_size"],
        mime_type=row["mime_type"],
        sha256=row["sha256"],
        uploaded_at=row["uploaded_at"],
        verdict_label=row["verdict_label"],
        verdict_text=row["verdict_text"],
        confidence=row["confidence"],
        camera_guess=row["camera_guess"],
        encoder_guess=row["encoder_guess"],
        width=row["width"],
        height=row["height"],
    )


def _row(evidence_id: str) -> dict:
    found = db.row("select * from evidence where id = ?", (evidence_id,))
    if found is None:
        raise NotFound(f"bukti {evidence_id} tidak ditemukan")
    return found


def _matches(evidence_id: str) -> list[MatchOut]:
    rows = db.rows(
        """select m.rank, m.similarity, m.explanation, r.id as reference_id, r.label, r.make,
                  r.model, r.encoder, r.note
           from matches m join reference_cameras r on r.id = m.reference_id
           where m.evidence_id = ? order by m.rank""",
        (evidence_id,),
    )
    return [MatchOut(**row) for row in rows]


def _signature(evidence_id: str) -> SignatureOut:
    row = db.row("select * from signatures where evidence_id = ?", (evidence_id,))
    if row is None:
        raise NotFound(f"signature untuk {evidence_id} tidak ditemukan")
    encoder = db.loads(row["app_markers"], {})
    return SignatureOut(
        evidence_id=evidence_id,
        exif=db.loads(row["exif_json"], {}),
        qtable=QTables(luma=db.loads(row["qtable_luma"], []), chroma=db.loads(row["qtable_chroma"], [])),
        fingerprint_hex=row["fingerprint_hex"],
        encoder=EncoderInfo(
            guess=encoder.get("guess", "tidak diketahui"),
            confidence=encoder.get("confidence", "lemah"),
            subsampling=row["subsampling"],
            restart_interval=row["restart_interval"],
            huffman_tables=row["huffman_tables"],
            app_markers=encoder.get("markers", []),
            note=encoder.get("note", ""),
        ),
        edit_traces=db.loads(row["edit_traces"], []),
        components=db.loads(row["components"], []),
        computed_at=row["computed_at"],
    )


@router.post("", response_model=EvidenceDetail, status_code=201)
async def upload(file: UploadFile = File(...)) -> EvidenceDetail:
    suffix = Path(file.filename or "").suffix.lower()
    if (file.content_type or "") not in ALLOWED_MIME or suffix not in ALLOWED_EXT:
        raise UnsupportedMedia(
            f"berkas '{file.filename or 'tanpa nama'}' bukan JPEG. Hanya .jpg/.jpeg yang diterima."
        )

    raw = await file.read()
    limit_mb = runtime_settings.max_upload_mb()
    limit = limit_mb * 1024 * 1024
    if len(raw) == 0:
        raise ApiError("berkas kosong", "empty_file", 422)
    if len(raw) > limit:
        raise TooLarge(f"berkas {len(raw) / 1024 / 1024:.1f} MB melebihi batas {limit_mb} MB")

    digest = hashlib.sha256(raw).hexdigest()
    evidence_id = f"EVD-{digest[:10].upper()}"

    try:
        with Image.open(__import__("io").BytesIO(raw)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiError(f"berkas tidak dapat dibaca sebagai JPEG: {exc}", "invalid_image", 422) from exc

    stored = Path(settings().upload_dir) / f"{evidence_id}.jpg"
    stored.write_bytes(raw)

    references = db.rows("select * from reference_cameras")
    for ref in references:
        ref["luma"] = db.loads(ref["qtable_luma"], [])
        ref["chroma"] = db.loads(ref["qtable_chroma"], [])
    result = analyze.analyze(raw, references)
    verdict = result["verdict"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    db.execute(
        """insert or replace into evidence (id, filename, byte_size, mime_type, sha256, stored_path,
               uploaded_at, verdict_label, verdict_text, confidence, camera_guess, encoder_guess,
               width, height) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            evidence_id,
            file.filename or f"{evidence_id}.jpg",
            len(raw),
            "image/jpeg",
            digest,
            str(stored),
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
    signature = result["signature"]
    db.execute(
        """insert or replace into signatures (evidence_id, exif_json, qtable_luma, qtable_chroma,
               fingerprint_hex, subsampling, restart_interval, huffman_tables, app_markers,
               edit_traces, components, computed_at)
           values (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            evidence_id,
            db.dumps(signature["exif"]),
            db.dumps(signature["qtable"]["luma"]),
            db.dumps(signature["qtable"]["chroma"]),
            signature["fingerprint_hex"],
            signature["encoder"]["subsampling"],
            signature["encoder"]["restart_interval"],
            signature["encoder"]["huffman_tables"],
            db.dumps(
                {
                    "guess": signature["encoder"]["guess"],
                    "confidence": signature["encoder"]["confidence"],
                    "note": signature["encoder"]["note"],
                    "markers": signature["encoder"]["app_markers"],
                }
            ),
            db.dumps(signature["edit_traces"]),
            db.dumps(signature["components"]),
            now,
        ),
    )
    db.execute("delete from matches where evidence_id = ?", (evidence_id,))
    for match in result["matches"]:
        db.execute(
            "insert into matches (evidence_id, rank, reference_id, similarity, explanation)"
            " values (?,?,?,?,?)",
            (
                evidence_id,
                match["rank"],
                match["reference_id"],
                match["similarity"],
                match["explanation"],
            ),
        )
    return detail(evidence_id)


@router.get("", response_model=list[EvidenceOut])
def list_evidence() -> list[EvidenceOut]:
    return [_out(row) for row in db.rows("select * from evidence order by uploaded_at desc, id desc")]


@router.get("/{evidence_id}", response_model=EvidenceDetail)
def detail(evidence_id: str) -> EvidenceDetail:
    row = _row(evidence_id)
    return EvidenceDetail(
        **_out(row).model_dump(), signature=_signature(evidence_id), matches=_matches(evidence_id)
    )


@router.get("/{evidence_id}/signature", response_model=SignatureOut)
def get_signature(evidence_id: str) -> SignatureOut:
    _row(evidence_id)
    return _signature(evidence_id)


@router.get("/{evidence_id}/matches", response_model=list[MatchOut])
def get_matches(evidence_id: str) -> list[MatchOut]:
    _row(evidence_id)
    return _matches(evidence_id)


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: str) -> Response:
    row = _row(evidence_id)
    Path(row["stored_path"]).unlink(missing_ok=True)
    db.execute("delete from evidence where id = ?", (evidence_id,))
    return Response(status_code=204)
