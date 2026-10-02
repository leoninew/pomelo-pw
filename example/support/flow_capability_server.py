"""Loopback fixture for paginated materials and serial asynchronous tasks."""

from __future__ import annotations

import argparse
import json
import time
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

SCENARIOS = ("mixed", "empty", "read-error", "timeout")
MATERIALS: list[dict[str, Any]] = [
    {"id": "done", "name": "Completed material", "status": "ready", "format": "pdf", "file": "/files/done.pdf"},
    {"id": "no-file", "name": "Missing file", "status": "new", "format": "pdf", "file": None},
    {"id": "unsupported", "name": "Unsupported file", "status": "new", "format": "txt", "file": "/files/notes.txt"},
    {
        "id": "existing",
        "name": "Existing task",
        "status": "processing",
        "format": "pdf",
        "file": "/files/existing.pdf",
        "task_id": "task-existing",
    },
    {"id": "fresh-ok", "name": "Literal {{missing}}", "status": "new", "format": "docx", "file": "/files/new.docx"},
    {"id": "fresh-fail", "name": "New failed task", "status": "new", "format": "pdf", "file": "/files/fail.pdf"},
    {"id": "prior-fail", "name": "Previously failed", "status": "failed", "format": "pdf", "file": "/files/prior.pdf"},
]

PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>Material tasks</title>
<style>
body { font: 15px Arial; color: #202520; background: #fafafa; margin: 28px; }
main { max-width: 1000px; } h1 { font-size: 24px; } button { padding: 7px 14px; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }
th, td { border-bottom: 1px solid #d7ddd7; text-align: left; padding: 10px; }
th { color: #405440; } #catalog[data-ready="false"] tbody { opacity: .45; }
pre { white-space: pre-wrap; } nav { display: flex; gap: 20px; align-items: center; }
</style>
<main><h1>Material tasks</h1><button id="login">Sign in</button>
<p id="session">Signed out</p>
<section id="catalog" data-ready="false" data-page="0">
<table><thead><tr><th>Material</th><th>Status</th><th>Format</th><th>File</th></tr></thead>
<tbody></tbody></table><nav><span id="page-label">Page 0</span><button id="next" disabled>Next page</button></nav>
</section><pre id="summary"></pre></main>
<script>
const catalog = document.querySelector('#catalog');
async function jsonRequest(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
async function renderPage(number) {
  catalog.dataset.ready = 'false';
  catalog.dataset.page = String(number);
  location.hash = `page-${number}`;
  document.querySelector('#next').disabled = true;
  const page = await jsonRequest(`/api/materials?page=${number}`);
  const rows = page.items.map(item => {
    const row = document.createElement('tr');
    row.dataset.id = item.id;
    if (item.task_id) row.dataset.taskId = item.task_id;
    for (const key of ['name', 'status', 'format', 'file']) {
      const cell = document.createElement('td');
      cell.className = key;
      if (key === 'file' && item.file) {
        const link = document.createElement('a');
        link.href = item.file;
        link.textContent = item.file.split('/').pop();
        cell.append(link);
      } else {
        cell.textContent = item[key] ?? '';
      }
      row.append(cell);
    }
    return row;
  });
  catalog.querySelector('tbody').replaceChildren(...rows);
  document.querySelector('#page-label').textContent = `Page ${number} of ${page.pages}`;
  document.querySelector('#next').disabled = number === page.pages;
  catalog.dataset.ready = 'true';
}
document.querySelector('#login').onclick = async () => {
  const scenario = new URL(location.href).searchParams.get('scenario') || 'mixed';
  await jsonRequest(`/login?scenario=${encodeURIComponent(scenario)}`, {method: 'POST'});
  await renderPage(1);
  document.querySelector('#session').textContent = 'Signed in';
  document.querySelector('#login').disabled = true;
};
document.querySelector('#next').onclick = () => renderPage(Number(catalog.dataset.page) + 1);
</script></html>"""


@dataclass
class Task:
    material_id: str
    terminal: str = "ready"
    status: str = "pending"
    reads: int = 0


@dataclass
class Run:
    scenario: str
    materials: list[dict[str, Any]] = field(default_factory=list)
    tasks: dict[str, Task] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    submissions: list[dict[str, Any]] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.scenario != "empty":
            self.materials = deepcopy(MATERIALS)
            self.tasks["task-existing"] = Task("existing")

    @property
    def page_count(self) -> int:
        return max(1, (len(self.materials) + 3) // 4)

    def audit(self) -> dict[str, Any]:
        return deepcopy(
            {
                "pages": self.pages,
                "submissions": self.submissions,
                "events": self.events,
                "violations": self.violations,
                "reads": {task_id: task.reads for task_id, task in self.tasks.items()},
            }
        )


class CapabilityServer(ThreadingHTTPServer):
    def __init__(self, port: int = 0) -> None:
        super().__init__(("127.0.0.1", port), CapabilityHandler)
        self.runs: dict[str, Run] = {}
        self.lock = Lock()


class CapabilityHandler(BaseHTTPRequestHandler):
    server: CapabilityServer

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send(self, status: int, body: str, content_type: str, cookie: str | None = None) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        with suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(encoded)

    def _json(self, status: int, body: Any, cookie: str | None = None) -> None:
        self._send(status, json.dumps(body), "application/json", cookie)

    def _run(self) -> Run | None:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        session = cookies.get("capability_session")
        run = self.server.runs.get(session.value) if session is not None else None
        if run is None:
            self._json(401, {"error": "sign in through the page first"})
        return run

    def do_GET(self) -> None:
        target = urlsplit(self.path)
        if target.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        with self.server.lock:
            run = self._run()
            if run is None:
                return
            if target.path == "/api/manifest":
                self._json(
                    200,
                    {
                        "total": len(run.materials),
                        "page_count": run.page_count,
                        "pages": list(range(1, run.page_count + 1)),
                        "supported_formats": ["pdf", "docx"],
                    },
                )
            elif target.path == "/api/materials":
                try:
                    page = int(parse_qs(target.query).get("page", ["1"])[0])
                except ValueError:
                    self._json(400, {"error": "invalid page"})
                    return
                if not 1 <= page <= run.page_count:
                    self._json(400, {"error": "invalid page"})
                    return
                run.pages.append(page)
                # Keep old rows briefly after the route changes to expose stale-page reads.
                time.sleep(0.06)
                self._json(200, {"items": run.materials[(page - 1) * 4 : page * 4], "pages": run.page_count})
            elif target.path == "/api/audit":
                self._json(200, run.audit())
            elif target.path.startswith("/api/tasks/"):
                task_id = target.path.rsplit("/", 1)[1]
                task = run.tasks.get(task_id)
                if task is None:
                    self._json(404, {"error": "unknown task"})
                    return
                task.reads += 1
                if run.scenario == "read-error" and task.material_id == "fresh-ok":
                    self._json(503, {"error": "controlled read failure"})
                    return
                stuck = run.scenario == "timeout" and task.material_id == "fresh-ok"
                if task.status == "pending" and task.reads >= 2 and not stuck:
                    task.status = task.terminal
                    run.events.append({"event": "terminal", "material_id": task.material_id, "status": task.status})
                self._json(
                    200,
                    {
                        "id": task_id,
                        "status": task.status,
                        "reads": task.reads,
                        "error": "controlled business failure" if task.status == "failed" else None,
                    },
                )
            else:
                self._json(404, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        target = urlsplit(self.path)
        with self.server.lock:
            if target.path == "/login":
                scenario = parse_qs(target.query).get("scenario", ["mixed"])[0]
                if scenario not in SCENARIOS:
                    self._json(400, {"error": "unknown scenario"})
                    return
                session = uuid4().hex
                self.server.runs[session] = Run(scenario)
                self._json(
                    200, {"authenticated": True}, f"capability_session={session}; Path=/; HttpOnly; SameSite=Lax"
                )
                return
            run = self._run()
            if run is None:
                return
            if target.path == "/logout":
                self._json(
                    200, {"authenticated": False}, "capability_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"
                )
                return
            if target.path != "/api/tasks":
                self._json(404, {"error": "unknown endpoint"})
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            except ValueError:
                self._json(400, {"error": "invalid JSON"})
                return
            if not isinstance(body, dict) or body.get("material_id") not in {"fresh-ok", "fresh-fail"}:
                self._json(400, {"error": "invalid material"})
                return
            material_id = body["material_id"]
            if any(task.material_id == material_id for task in run.tasks.values()):
                run.violations.append(f"duplicate submission: {material_id}")
                self._json(409, {"error": run.violations[-1]})
                return
            if any(task.status == "pending" for task in run.tasks.values()):
                run.violations.append(f"submission before previous terminal: {material_id}")
                self._json(409, {"error": run.violations[-1]})
                return
            task_id = f"task-{material_id}"
            run.tasks[task_id] = Task(material_id, terminal="failed" if material_id == "fresh-fail" else "ready")
            run.submissions.append({"id": task_id, "payload": body})
            run.events.append({"event": "submit", "material_id": material_id})
            self._json(201, {"id": task_id})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    with CapabilityServer(args.port) as server:
        print(f"Flow capability example: http://127.0.0.1:{server.server_port}", flush=True)
        with suppress(KeyboardInterrupt):
            server.serve_forever()


if __name__ == "__main__":
    main()
