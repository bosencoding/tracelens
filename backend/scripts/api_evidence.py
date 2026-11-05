"""Regenerate docs/api-evidence.txt for TraceLens v2 (multipart upload included).

Usage: cd backend && uv run python scripts/api_evidence.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:8001"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "docs" / "api-evidence.txt"
SAMPLE = ROOT / "data" / "uploads" / "EVD-CONTOH-B.jpg"


def call(method: str, path: str, body: dict | None = None, files: dict | None = None):
    headers = {"Origin": "http://localhost:5173"}
    data = None
    if files:
        boundary = uuid.uuid4().hex
        _, path_obj, ctype = files["file"]
        payload = path_obj.read_bytes()
        data = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                f'filename="{Path(path_obj).name}"\r\nContent-Type: {ctype}\r\n\r\n'
            ).encode()
            + payload
            + f"\r\n--{boundary}--\r\n".encode()
        )
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, res.read(), {k.lower(): v for k, v in res.headers.items()}
    except urllib.error.HTTPError as err:
        return err.code, err.read(), {k.lower(): v for k, v in err.headers.items()}


def describe(status: int, payload: bytes, headers: dict) -> str:
    ctype = headers.get("content-type", "?")
    if not payload:
        return f"{status} 0B"
    if "application/json" not in ctype:
        return f"{status} {len(payload)}B {ctype}"
    body = json.loads(payload)
    if isinstance(body, list):
        return f"{status} {len(payload)}B list[{len(body)}]"
    if "code" in body:
        return f"{status} {len(payload)}B code={body['code']} detail={body['detail'][:60]}"
    if "signature" in body:
        return f"{status} {len(payload)}B verdict={body['verdict_label']} conf={body['confidence']}"
    if "fingerprint_hex" in body:
        return (
            f"{status} {len(payload)}B fp={body['fingerprint_hex'][:12]}… "
            f"q={len(body['qtable']['luma'])}/{len(body['qtable']['chroma'])}"
        )
    return f"{status} {len(payload)}B keys={','.join(list(body)[:6])}"


def main() -> None:
    global BASE
    if "--base" in sys.argv:
        BASE = sys.argv[sys.argv.index("--base") + 1]

    lines = [
        f"# TraceLens v2 API evidence — {datetime.now():%Y-%m-%d %H:%M} local",
        "# reproduced by: cd backend && uv run python scripts/api_evidence.py",
    ]

    def row(label: str, method: str, path: str, body=None, files=None) -> dict:
        status, payload, headers = call(method, path, body=body, files=files)
        lines.append(f"{label:<52} {describe(status, payload, headers)}")
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {}
        return parsed if isinstance(parsed, dict) else {}

    row("GET /api/health", "GET", "/api/health")
    listing = json.loads(call("GET", "/api/evidence")[1])
    lines.append(f"{'GET /api/evidence':<52} 200 list[{len(listing)}]")
    row("GET /api/evidence/EVD-CONTOH-A", "GET", "/api/evidence/EVD-CONTOH-A")
    row("GET /api/evidence/EVD-CONTOH-A/signature", "GET", "/api/evidence/EVD-CONTOH-A/signature")
    matches = call("GET", "/api/evidence/EVD-CONTOH-A/matches")[1]
    scored = json.loads(matches)
    lines.append(
        f"{'GET /api/evidence/EVD-CONTOH-A/matches':<52} 200 list[{len(scored)}] "
        + " ".join(f"{m['reference_id']}={m['similarity']}" for m in scored)
    )
    lines.append(
        "#   nilai similarity mengikuti tabel referensi yang ada di DB saat dijalankan, "
        "bukan konstanta di kode"
    )

    uploaded: dict = {}
    if SAMPLE.exists():
        uploaded = row(
            "POST /api/evidence (multipart jpeg)",
            "POST",
            "/api/evidence",
            files={"file": ("file", SAMPLE, "image/jpeg")},
        )

    lines.append("")
    lines.append("# negative paths")
    txt = Path("/tmp/tracelens-notjpeg.txt")
    txt.write_text("bukan jpeg")
    row("POST /api/evidence (.txt)", "POST", "/api/evidence", files={"file": ("file", txt, "text/plain")})
    png = Path("/tmp/tracelens-fake.png")
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    row("POST /api/evidence (.png)", "POST", "/api/evidence", files={"file": ("file", png, "image/png")})
    big = Path("/tmp/tracelens-big.jpg")
    if not big.exists():
        big.write_bytes(b"\xff\xd8\xff" + b"\x00" * (51 * 1024 * 1024))
    row("POST /api/evidence (51 MB → 413)", "POST", "/api/evidence", files={"file": ("file", big, "image/jpeg")})

    # a real JPEG padded past the old 20 MB limit: must now be accepted (limit is 50 MB)
    medium = Path("/tmp/tracelens-21mb.jpg")
    if not medium.exists() and SAMPLE.exists():
        raw = SAMPLE.read_bytes()
        medium.write_bytes(raw + b"\x00" * (21 * 1024 * 1024 - len(raw)))
    if medium.exists():
        accepted = row(
            "POST /api/evidence (21 MB jpeg → 201)",
            "POST",
            "/api/evidence",
            files={"file": ("file", medium, "image/jpeg")},
        )
        if accepted.get("id"):
            status, payload, headers = call("DELETE", f"/api/evidence/{accepted['id']}")
            lines.append(f"{'DELETE /api/evidence/' + accepted['id']:<52} {describe(status, payload, headers)}")
    row("POST /api/evidence (no file)", "POST", "/api/evidence")
    row("GET /api/evidence/NOPE", "GET", "/api/evidence/NOPE")

    lines.append("")
    lines.append("# image + thumbnail (HEAD and GET)")
    for label, path, method in (
        ("HEAD /api/evidence/EVD-CONTOH-A/image", "/api/evidence/EVD-CONTOH-A/image", "HEAD"),
        ("HEAD /api/evidence/EVD-CONTOH-A/thumbnail", "/api/evidence/EVD-CONTOH-A/thumbnail", "HEAD"),
        ("GET  /api/evidence/EVD-CONTOH-A/image", "/api/evidence/EVD-CONTOH-A/image", "GET"),
        ("GET  /api/evidence/EVD-CONTOH-A/thumbnail", "/api/evidence/EVD-CONTOH-A/thumbnail", "GET"),
        ("GET  /api/evidence/NGARANG/image (404)", "/api/evidence/NGARANG/image", "GET"),
    ):
        status, payload, headers = call(method, path)
        detail = (
            f"{status} {len(payload)}B {headers.get('content-type')} "
            f"len={headers.get('content-length')} cc={headers.get('cache-control')}"
        )
        lines.append(f"{label:<52} {detail}")

    lines.append("")
    lines.append("# settings")
    row("GET /api/settings", "GET", "/api/settings")
    row("PATCH /api/settings max_upload_mb=0", "PATCH", "/api/settings", body={"max_upload_mb": 0})
    row("PATCH /api/settings max_upload_mb=501", "PATCH", "/api/settings", body={"max_upload_mb": 501})

    if uploaded.get("id"):
        new_id = uploaded["id"]
        status, payload, headers = call("DELETE", f"/api/evidence/{new_id}")
        lines.append(f"{'DELETE /api/evidence/' + new_id:<52} {describe(status, payload, headers)}")
        status, payload, headers = call("GET", f"/api/evidence/{new_id}")
        lines.append(f"{'GET deleted id':<52} {describe(status, payload, headers)}")

    status, _, headers = call("GET", "/api/evidence")
    lines.append("")
    lines.append(f"# CORS on :5173 -> {headers.get('access-control-allow-origin')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
