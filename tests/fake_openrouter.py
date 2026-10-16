"""A key-free fake OpenRouter server for local smoke tests.

Serves GET /api/v1/credits and POST /api/v1/chat/completions with a fixed
observe proposal, so the real worker + tick can run end-to-end without touching
the network or the $100 budget. Bind on 127.0.0.1 only.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROPOSAL = {"action": "observe", "notes": "smoke test observation"}


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/v1/credits":
            self._json({"data": {"total_credits": 100.0, "total_usage": 0.0}})
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/v1/chat/completions":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self._json(
                {"choices": [{"message": {"role": "assistant", "content": json.dumps(PROPOSAL)}}]}
            )
            return
        self.send_error(404)


def serve(host: str = "127.0.0.1", port: int = 9991) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    server = serve()
    print(f"fake openrouter on http://127.0.0.1:{server.server_address[1]}")
    server.serve_forever()
