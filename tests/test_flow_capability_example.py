"""Focused checks for the public P0/P1 flow and its independent server audit."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

import pytest

from pomelo_pw.executor import FlowExecutor

if TYPE_CHECKING:
    from example.support.flow_capability_server import CapabilityServer

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "example/public/flow-capability-example.yaml"
SPEC = importlib.util.spec_from_file_location(
    "pomelo_pw_capability_fixture", ROOT / "example/support/flow_capability_server.py"
)
assert SPEC is not None
assert SPEC.loader is not None
capability_fixture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capability_fixture
SPEC.loader.exec_module(capability_fixture)
MATERIALS = capability_fixture.MATERIALS


@pytest.fixture
def server() -> Iterator[CapabilityServer]:
    with capability_fixture.CapabilityServer() as fixture:
        thread = Thread(target=fixture.serve_forever, daemon=True)
        thread.start()
        try:
            yield fixture
        finally:
            fixture.shutdown()
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_flow_uses_current_contract() -> None:
    assert FlowExecutor().validate_flow_file(FLOW) == []


def test_login_creates_independent_runs(server: CapabilityServer) -> None:
    url = f"http://127.0.0.1:{server.server_port}/login"
    for scenario in ("mixed", "empty"):
        with urlopen(Request(f"{url}?scenario={scenario}", method="POST"), timeout=5) as response:
            assert response.status == 200
            assert "HttpOnly" in response.headers["Set-Cookie"]
    with server.lock:
        runs = list(server.runs.values())
        assert [len(run.materials) for run in runs] == [7, 0]
        assert runs[0].tasks and not runs[1].tasks


@pytest.mark.skipif(
    os.environ.get("POMELO_PW_INTEGRATION") != "1", reason="Set POMELO_PW_INTEGRATION=1 for real browser CLI checks"
)
@pytest.mark.parametrize(
    ("scenario", "policy", "exit_code", "error_type"),
    [
        ("mixed", "report", 0, None),
        ("mixed", "fail", 1, "AssertionFailed"),
        ("empty", "report", 0, None),
        ("read-error", "report", 1, "RequestStatusError"),
        ("timeout", "report", 1, "PollTimeoutError"),
    ],
)
def test_real_cli_scenarios(
    server: CapabilityServer,
    tmp_path: Path,
    scenario: str,
    policy: str,
    exit_code: int,
    error_type: str | None,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pomelo_pw",
            "run",
            str(FLOW),
            "--base-url",
            f"http://127.0.0.1:{server.server_port}",
            "--var",
            f"scenario={scenario}",
            "--var",
            f"failure_policy={policy}",
            "--headless",
            "--json",
            "--verbose",
            "--output",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    payload: dict[str, Any] = json.loads(result.stdout)
    (tmp_path / "report.json").write_text(result.stdout, encoding="utf-8")
    (tmp_path / "execution.log").write_text(result.stderr, encoding="utf-8")
    assert result.returncode == exit_code, result.stderr
    assert payload["schema_version"] == 1
    assert payload["status"] == ("passed" if exit_code == 0 else "failed")
    assert "Loading flow" in result.stderr
    assert not {"success", "failed_step", "steps_executed", "row_results"}.intersection(payload)
    with server.lock:
        assert len(server.runs) == 1
        audit = next(iter(server.runs.values())).audit()
        saved = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
        assert saved["cookies"][0]["name"] == "capability_session"
        assert saved["cookies"][0]["httpOnly"] is True
        assert saved["cookies"][0]["value"] in server.runs
    assert audit["violations"] == []
    assert audit["pages"] == ([1] if scenario == "empty" else [1, 2])
    inventory = payload["outputs"]["inventory"]
    assert [item["id"] for item in inventory] == ([] if scenario == "empty" else [item["id"] for item in MATERIALS])
    if scenario != "empty":
        assert inventory[4]["name"] == "Literal {{missing}}"
        assert inventory[0]["task_id"] is None
        assert inventory[1]["file"] is None
        assert inventory[3]["task_id"] == "task-existing"
    submitted = [item["payload"]["material_id"] for item in audit["submissions"]]
    assert submitted == (
        []
        if scenario == "empty"
        else ["fresh-ok"]
        if scenario in {"read-error", "timeout"}
        else ["fresh-ok", "fresh-fail"]
    )
    assert all(
        item["payload"]["options"] == {"priority": 0, "enabled": False, "meta": None} for item in audit["submissions"]
    )
    if error_type:
        error = payload["errors"][0]
        assert error["error_type"] == error_type
        if scenario in {"read-error", "timeout"}:
            assert ".index-" in error["path"]
        else:
            assert error["type"] == "assert"
        assert Path(error["evidence"]["screenshot"]).is_file()
        assert Path(error["evidence"]["html_snapshot"]).is_file()
        assert all(Path(path).is_file() for path in payload["artifacts"]["screenshots"])
    if scenario in {"read-error", "timeout"}:
        assert "outcomes" not in payload["outputs"]
        assert "summary" not in payload["outputs"]
        assert [(item["event"], item["material_id"]) for item in audit["events"]] == [
            ("terminal", "existing"),
            ("submit", "fresh-ok"),
        ]
        polls = payload["errors"][0]["diagnostics"]["polls"]
        assert polls[0]["attempts"] >= 1
        if scenario == "read-error":
            assert audit["reads"]["task-fresh-ok"] == 1
        else:
            assert polls[0]["results"]["task"]["body"]["status"] == "pending"
        return
    outputs = payload["outputs"]
    assert outputs["audit"] == audit
    assert outputs["summary"] == (
        {"total": 0, "ready": 0, "skipped": 0, "failed": 0, "submitted": 0, "resumed": 0}
        if scenario == "empty"
        else {"total": 7, "ready": 3, "skipped": 3, "failed": 1, "submitted": 2, "resumed": 1}
    )
    if scenario == "mixed":
        outcomes = outputs["outcomes"]
        assert [item["id"] for item in outcomes] == [item["id"] for item in MATERIALS]
        assert [item["category"] for item in outcomes] == [
            "ready",
            "skipped",
            "skipped",
            "ready",
            "ready",
            "failed",
            "skipped",
        ]
        assert [item["reason"] for item in outcomes] == [
            "already_ready",
            "missing_file",
            "unsupported_format",
            "resumed",
            "submitted",
            "controlled business failure",
            "previous_failed",
        ]
        assert audit["reads"] == {"task-existing": 2, "task-fresh-ok": 2, "task-fresh-fail": 2}
        assert [(item["event"], item["material_id"]) for item in audit["events"]] == [
            ("terminal", "existing"),
            ("submit", "fresh-ok"),
            ("terminal", "fresh-ok"),
            ("submit", "fresh-fail"),
            ("terminal", "fresh-fail"),
        ]
    else:
        assert outputs["outcomes"] == []
    entries = payload["trace"]["entries"]
    assert all(entry["status"] in {"passed", "failed"} and "output" not in entry for entry in entries)
    assert payload["trace"]["dropped"] == 0
    if not error_type:
        assert (tmp_path / "results.png").is_file()
