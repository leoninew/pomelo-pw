"""Loopback-only fixture for the browser-session HTTP flow example."""

from __future__ import annotations

import argparse
import json
from contextlib import suppress
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>Session tasks</title>
<style>body { font: 16px Arial; max-width: 720px; margin: 32px; }
button { padding: 8px 16px; } pre { white-space: pre-wrap; }</style>
<h1>Session tasks</h1>
<button id="login">Sign in</button><p id="status">Signed out</p>
<pre id="summary"></pre>
<script>
document.querySelector('#login').onclick = async () => {
  const response = await fetch('/login', {method: 'POST'});
  if (!response.ok) throw new Error('Login failed');
  document.querySelector('#status').textContent = 'Signed in';
};
</script></html>"""


class DemoServer(ThreadingHTTPServer):
    def __init__(self, port: int) -> None:
        super().__init__(("127.0.0.1", port), DemoHandler)
        self.tasks: dict[str, int] = {}


class DemoHandler(BaseHTTPRequestHandler):
    server: DemoServer

    def _send(self, status: int, body: str, content_type: str, cookie: str | None = None) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(encoded)

    def _json(self, status: int, body: Any, cookie: str | None = None) -> None:
        self._send(status, json.dumps(body), "application/json", cookie)

    def _authenticated(self) -> bool:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        session = cookies.get("demo_session")
        if session is not None and session.value == "signed-in":
            return True
        self._json(401, {"error": "sign in through the page first"})
        return False

    def do_GET(self) -> None:
        target = urlsplit(self.path)
        if target.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif target.path.startswith("/api/") and self._authenticated():
            if target.path == "/api/session":
                self._json(200, {"authenticated": True, "query": parse_qs(target.query)})
            elif target.path == "/api/message":
                self._send(200, "ready", "text/plain; charset=utf-8")
            elif target.path.startswith("/api/tasks/"):
                task_id = target.path.rsplit("/", 1)[1]
                if task_id not in self.server.tasks:
                    self._json(404, {"error": "unknown task"})
                    return
                self.server.tasks[task_id] += 1
                reads = self.server.tasks[task_id]
                self._json(200, {"id": task_id, "status": "ready" if reads >= 2 else "pending", "reads": reads})
            else:
                self._json(404, {"error": "unknown endpoint"})
        elif not target.path.startswith("/api/"):
            self._json(404, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/login":
            self._json(200, {"authenticated": True}, "demo_session=signed-in; Path=/; HttpOnly; SameSite=Lax")
        elif path == "/api/tasks" and self._authenticated():
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except ValueError:
                self._json(400, {"error": "invalid JSON"})
                return
            task_id = f"task-{len(self.server.tasks) + 1}"
            self.server.tasks[task_id] = 0
            self._json(
                201,
                {"id": task_id, "payload": body, "header": self.headers.get("X-Example")},
                "request_seen=1; Path=/; SameSite=Lax",
            )
        elif path != "/api/tasks":
            self._json(404, {"error": "unknown endpoint"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with DemoServer(args.port) as server:
        print(f"Session HTTP example: http://127.0.0.1:{server.server_port}", flush=True)
        with suppress(KeyboardInterrupt):
            server.serve_forever()


if __name__ == "__main__":
    main()
