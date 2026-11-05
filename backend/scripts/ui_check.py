"""UI evidence for v2: 3 routes at 1440/390, overflow, tokens, screenshots, print media.

Usage: cd backend && uv run python scripts/ui_check.py
Writes backend/docs/screenshots/<route>-<width>.png
"""

from __future__ import annotations

import asyncio
import base64
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
SHOTS = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
ROUTES = {
    "upload": "/",
    "hasil": "/hasil/EVD-CONTOH-A",
    "laporan": "/laporan/EVD-CONTOH-A",
    "pengaturan": "/pengaturan",
    "unknown": "/tidak-ada",
}
VIEWPORTS = [(1440, 900), (390, 844)]


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


async def main() -> int:
    base = "http://localhost:5173"
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    SHOTS.mkdir(parents=True, exist_ok=True)

    chrome = None
    if not port_open(PORT):
        chrome = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={PROFILE}",
                "--no-first-run",
                "--no-default-browser-check",
                "--hide-scrollbars",
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
        version = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version"))
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
            await send("Page.enable", session=session)
            await send("Runtime.enable", session=session)

            async def js(expression: str):
                res = await send(
                    "Runtime.evaluate",
                    session=session,
                    expression=expression,
                    returnByValue=True,
                    awaitPromise=True,
                )
                return res.get("result", {}).get("value")

            results = []
            for width, height in VIEWPORTS:
                await send(
                    "Emulation.setDeviceMetricsOverride",
                    session=session,
                    width=width,
                    height=height,
                    deviceScaleFactor=1,
                    mobile=width < 500,
                )
                for name, path in ROUTES.items():
                    await send("Page.navigate", session=session, url=f"{base}{path}")
                    await asyncio.sleep(2.0)
                    probe = await js("""(() => {
                      const cs = getComputedStyle(document.body);
                      const btn = document.querySelector('.btn-primary');
                      const mono = document.querySelector('.font-mono, .data-mono');
                      const card = document.querySelector('.card, .card-hero');
                      return {
                        overflowX: document.documentElement.scrollWidth - window.innerWidth,
                        bodyFont: cs.fontFamily.split(',')[0],
                        surface: cs.backgroundColor,
                        primaryBg: btn ? getComputedStyle(btn).backgroundColor : null,
                        cardRadius: card ? getComputedStyle(card).borderRadius : null,
                        monoFont: mono ? getComputedStyle(mono).fontFamily.split(',')[0] : null,
                        text: document.body.innerText,
                      };
                    })()""")
                    shot = await send(
                        "Page.captureScreenshot", session=session, format="png", captureBeyondViewport=True
                    )
                    file = SHOTS / f"{name}-{width}.png"
                    file.write_bytes(base64.b64decode(shot["data"]))
                    results.append(
                        {
                            "route": name,
                            "path": path,
                            "viewport": width,
                            **{
                                k: probe[k]
                                for k in ("overflowX", "bodyFont", "surface", "primaryBg", "cardRadius")
                            },
                            "monoFont": (probe["monoFont"] or "").strip('"'),
                            "textChars": len(probe["text"]),
                            "head": " | ".join(line for line in probe["text"].split("\n") if line.strip())[
                                :220
                            ],
                            "shot": str(file),
                        }
                    )

            # print media: nav/buttons must vanish, disclaimer must stay
            await send(
                "Emulation.setDeviceMetricsOverride",
                session=session,
                width=1440,
                height=900,
                deviceScaleFactor=1,
                mobile=False,
            )
            await send("Page.navigate", session=session, url=f"{base}/laporan/EVD-CONTOH-A")
            await asyncio.sleep(2.0)
            await send("Emulation.setEmulatedMedia", session=session, media="print")
            await asyncio.sleep(0.4)
            print_probe = await js("""(() => ({
              headerHidden: getComputedStyle(document.querySelector('header')).display === 'none',
              buttonsHidden: [...document.querySelectorAll('button')].every(b => b.closest('.no-print') || getComputedStyle(b).display === 'none'),
              disclaimer: document.querySelector('[data-testid="disclaimer"]')?.innerText.includes('DISCLAIMER'),
              bodyBg: getComputedStyle(document.body).backgroundColor,
            }))()""")
            shot = await send(
                "Page.captureScreenshot", session=session, format="png", captureBeyondViewport=True
            )
            (SHOTS / "laporan-print-1440.png").write_bytes(base64.b64decode(shot["data"]))
            await send("Emulation.setEmulatedMedia", session=session, media="screen")

            print(json.dumps({"pages": results, "print": print_probe}, indent=1, ensure_ascii=False))
            await send("Target.closeTarget", targetId=target["targetId"])
    finally:
        if chrome is not None:
            chrome.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
