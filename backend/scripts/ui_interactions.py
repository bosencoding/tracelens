"""Interaction evidence for v2: upload through the real file input, tab contents, rejections.

Usage: cd backend && uv run python scripts/ui_interactions.py
"""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9222
PROFILE = "/tmp/tracelens-cdp"
ROOT = Path(__file__).resolve().parent.parent
JPEG = ROOT / "data" / "uploads" / "EVD-CONTOH-C.jpg"
BAD = Path("/tmp/tracelens-notjpeg.txt")


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


async def run(base: str) -> dict:
    version = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version"))
    out: dict = {}
    async with websockets.connect(version["webSocketDebuggerUrl"], max_size=30_000_000) as ws:
        seq = 0

        async def send(method: str, session: str | None = None, **params):
            nonlocal seq
            seq += 1
            msg: dict = {"id": seq, "method": method, "params": params}
            if session:
                msg["sessionId"] = session
            await ws.send(json.dumps(msg))
            while True:
                reply = json.loads(await ws.recv())
                if reply.get("id") == seq:
                    if "error" in reply:
                        raise RuntimeError(f"{method}: {reply['error']}")
                    return reply.get("result", {})

        target = await send("Target.createTarget", url="about:blank")
        session = (await send("Target.attachToTarget", targetId=target["targetId"], flatten=True))[
            "sessionId"
        ]
        for domain in ("Page", "Runtime", "DOM"):
            await send(f"{domain}.enable", session=session)
        await send("Browser.grantPermissions", permissions=["clipboardReadWrite"])
        await send(
            "Emulation.setDeviceMetricsOverride",
            session=session,
            width=1440,
            height=900,
            deviceScaleFactor=1,
            mobile=False,
        )

        async def js(expression: str):
            res = await send(
                "Runtime.evaluate",
                session=session,
                expression=expression,
                returnByValue=True,
                awaitPromise=True,
            )
            return res.get("result", {}).get("value")

        async def goto(path: str, wait: float = 2.2):
            await send("Page.navigate", session=session, url=f"{base}{path}")
            await asyncio.sleep(wait)

        async def set_file(path: Path):
            doc = await send("DOM.getDocument", session=session, depth=-1)
            node = await send(
                "DOM.querySelector",
                session=session,
                nodeId=doc["root"]["nodeId"],
                selector='input[type="file"]',
            )
            await send(
                "DOM.setFileInputFiles",
                session=session,
                files=[str(path)],
                nodeId=node["nodeId"],
            )
            await asyncio.sleep(2.5)

        # A3 — rejection: wrong mime through the real input
        await goto("/")
        await set_file(BAD)
        out["A3_reject_txt"] = await js(
            """(() => {
              const el = document.querySelector('[data-testid="upload-error"]');
              return el ? el.innerText : null;
            })()"""
        )

        # A3 — accepted JPEG navigates to /hasil/:id with a verdict
        await goto("/")
        await set_file(JPEG)
        await asyncio.sleep(1.5)
        out["A3_upload"] = {
            "url": await js("location.pathname"),
            "confidence": await js("document.querySelector('[data-testid=\"confidence\"]')?.innerText"),
            "verdict": await js("document.querySelector('.card-hero .text-headline-lg')?.innerText"),
        }
        new_path = out["A3_upload"]["url"]
        new_id = new_path.split("/")[-1]

        # A4 — four tabs, each with its own panel and data
        tabs = {}
        for key in ("exif", "qtable", "trace", "summary"):
            await js(f"document.querySelector('[data-result-tab=\"{key}\"]').click()")
            await asyncio.sleep(0.35)
            tabs[key] = await js(
                f"""(() => {{
                  const panel = document.querySelector('[data-panel="{key}"]');
                  if (!panel) return null;
                  return {{
                    firstQtable: panel.querySelector('[data-qtable]')?.innerText ?? null,
                    components: panel.querySelectorAll('[data-component]').length,
                    traces: panel.querySelectorAll('[data-trace]').length,
                    exifRows: panel.querySelectorAll('[data-exif-tag]').length,
                    textChars: panel.innerText.length,
                  }};
                }})()"""
            )
        out["A4_tabs"] = tabs
        await js("document.querySelector('[data-result-tab=\"qtable\"]').click()")
        await asyncio.sleep(0.35)
        out["A4_fingerprint"] = await js("document.querySelector('[data-testid=\"fingerprint\"]')?.innerText")
        out["A4_first_cell"] = await js("document.querySelector('[data-qtable=\"luma-0\"]')?.innerText")
        api = json.load(urllib.request.urlopen(f"http://127.0.0.1:8001/api/evidence/{new_id}/signature"))
        out["api_fingerprint"] = api["fingerprint_hex"]
        out["api_qtable_first"] = api["qtable"]["luma"][0]
        await js("document.querySelector('[data-result-tab=\"summary\"]').click()")
        await asyncio.sleep(0.35)
        out["matches_page"] = await js(
            "[...document.querySelectorAll('[data-match]')].map(e => e.innerText.split('\\n').pop())"
        )

        # A1 — unknown id renders an error page, not a blank one
        await goto("/hasil/TIDAK-ADA")
        out["A1_unknown"] = {
            "notFoundCard": await js("!!document.querySelector('[data-testid=\"not-found\"]')"),
            "chars": await js("document.body.innerText.length"),
        }

        # A6 — print layout keeps the disclaimer, drops chrome
        await goto(f"/laporan/{new_id}")
        out["A6_before_print"] = {
            "disclaimer": await js(
                "document.querySelector('[data-testid=\"disclaimer\"]')?.innerText.slice(0, 60)"
            ),
            "printButton": await js("!!document.querySelector('[data-testid=\"print\"]')"),
        }

        await send("Target.closeTarget", targetId=target["targetId"])
    return out


async def main() -> dict:
    base = "http://localhost:5173"
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    chrome = None
    if not port_open(PORT):
        chrome = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={PROFILE}",
                "--no-first-run",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            time.sleep(0.5)
            if port_open(PORT):
                break
    try:
        return await run(base)
    finally:
        if chrome is not None:
            chrome.terminate()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), indent=1, ensure_ascii=False))
