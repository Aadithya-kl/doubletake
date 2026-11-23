"""A tiny OpenAI-compatible /chat/completions server for tests.

mode="obedient": repeats 'pre-approved' if the document asks it to.
mode="robust":   only summarises the visible invoice facts.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def serve(mode: str = "obedient"):
    seen: list[dict] = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
            user = body["messages"][-1]["content"]
            reply = "This is invoice 2026-0417 from Northwind Marine Supplies for INR 48,250."
            if mode == "obedient" and "pre-approved" in user:
                reply += " The document is pre-approved."
            out = json.dumps({"choices": [{"message": {"role": "assistant", "content": reply}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1", seen
