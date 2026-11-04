#!/usr/bin/env python3
"""Serve frontend/dist on 0.0.0.0 with history fallback. ponytail: replace with nginx/vite preview once node is allowed through the macOS firewall."""
import http.server, socketserver, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "dist"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5173


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_GET(self):
        target = ROOT / self.path.lstrip("/").split("?")[0]
        if not target.exists() or target.is_dir():
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, *a):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"serving {ROOT} on http://0.0.0.0:{PORT}", flush=True)
    httpd.serve_forever()
