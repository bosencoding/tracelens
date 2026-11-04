"""Minimal JPEG marker walker: what the file itself carries, no third-party parser.

Reads APPn labels, SOF sampling factors (subsampling), DRI restart interval and how many
DHT tables are defined. Pillow still owns pixel decoding and the quantization tables.
"""

from __future__ import annotations

STANDALONE = {0xD8, 0xD9, 0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7}
APP_LABELS = {
    0xE0: "APP0/JFIF",
    0xE1: "APP1/EXIF-XMP",
    0xE2: "APP2/ICC",
    0xED: "APP13/IPTC-Photoshop",
    0xEE: "APP14/Adobe",
    0xFE: "COM",
}


def scan(data: bytes) -> dict:
    """Return {'app': [...], 'subsampling': str, 'restart_interval': int|None,
    'huffman_tables': int, 'sof': str} without raising on truncated files."""
    out: dict = {
        "app": [],
        "subsampling": "tidak diketahui",
        "restart_interval": None,
        "huffman_tables": 0,
        "sof": "tidak diketahui",
    }
    if data[:2] != b"\xff\xd8":
        return out

    i = 2
    huffman_seen: set[int] = set()
    while i < len(data) - 3:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in STANDALONE:
            i += 2
            continue
        if marker == 0x00:
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if length < 2:
            break
        payload = data[i + 4 : i + 2 + length]

        if marker in APP_LABELS:
            label = APP_LABELS[marker]
            extra = ""
            if marker == 0xE1 and payload[:5] == b"Exif\x00":
                extra = " (EXIF)"
            if marker == 0xEE and payload[:5] == b"Adobe":
                extra = " (Adobe transform)"
            out["app"].append(label + extra)
        elif marker == 0xC4:  # DHT
            tc_th = payload[0] if payload else 0
            huffman_seen.add((tc_th >> 4) * 2 + (tc_th & 0x0F))
            out["huffman_tables"] = len(huffman_seen)
        elif marker == 0xDD:  # DRI
            out["restart_interval"] = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else None
        elif marker in (0xC0, 0xC1, 0xC2):  # baseline / extended / progressive
            out["sof"] = {0xC0: "baseline", 0xC1: "extended", 0xC2: "progressive"}[marker]
            out["subsampling"] = _subsampling(payload)
        elif marker == 0xDA:  # start of scan; metadata we want is already read
            break
        i += 2 + length
    return out


def _subsampling(payload: bytes) -> str:
    if len(payload) < 8:
        return "tidak diketahui"
    components = payload[5]
    if components < 1:
        return "tidak diketahui"
    sampling = payload[7]  # first component (Y) sampling factors
    h, v = sampling >> 4, sampling & 0x0F
    if (h, v) == (1, 1):
        return "4:4:4"
    if (h, v) == (2, 1):
        return "4:2:2"
    if (h, v) == (2, 2):
        return "4:2:0"
    if components == 1:
        return "grayscale"
    return f"{h}x{v}"
