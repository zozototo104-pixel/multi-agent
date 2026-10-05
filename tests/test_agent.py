"""اختبارات المرحلة الثانية بدون إنترنت وبدون Docker حقيقي."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent import coder, jsonutil, loop, sandbox, workspace
from agent.schemas import FileContent, FileSpec, Plan, RunResult


def sample_plan() -> Plan:
    return Plan(
        project_name="calculator",
        language="python",
        description="آلة حاسبة",
        files=[FileSpec("calculator.py", "التطبيق"), FileSpec("test_calculator.py", "الاختبارات")],
        dependencies=[],
        test_command="pytest -q",
        run_command="python calculator.py",
    )


def test_extract_json_from_text_and_fence():
    reply = 'ممتاز\n```json\n{"project_name":"demo"}\n```\nانتهى'
    assert jsonutil.extract_json(reply) == {"project_name": "demo"}


@pytest.mark.parametrize("bad_path", ["../x", "/etc/passwd"])
def test_workspace_rejects_path_traversal(tmp_path, bad_path):
    with pytest.raises(ValueError, match="مسار"):
        workspace.safe_path(tmp_path, bad_path)


def test_loop_stops_on_first_success(monkeypatch, tmp_path):
    plan = sample_plan()
    calls = {"run": 0, "fix": 0}
    monkeypatch.setattr(loop, "make_plan", lambda request: plan)
    monkeypatch.setattr(loop, "write_code", lambda plan: [FileContent("calculator.py", "pass"), FileContent("test_calculator.py", "def test_ok(): assert True")])
    monkeypatch.setattr(loop, "write_files", lambda name, files: tmp_path)
    monkeypatch.setattr(loop, "usage_summary", lambda: {"calls": 2, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2})
    monkeypatch.setattr(loop, "_write_report", lambda project_dir, report: None)

    def run(project_dir, plan):
        calls["run"] += 1
        return RunResult(0, "1 passed", "", 0.1)

    monkeypatch.setattr(loop, "run_in_sandbox", run)
    monkeypatch.setattr(loop, "fix_code", lambda *args: calls.__setitem__("fix", calls["fix"] + 1))
    report = loop.build("calculator")
    assert report["success"] is True
    assert report["attempts_count"] == 1
    assert calls == {"run": 1, "fix": 0}


def test_loop_stops_after_exactly_five_failures(monkeypatch, tmp_path):
    plan = sample_plan()
    calls = {"run": 0, "fix": 0}
    files = [FileContent("calculator.py", "pass"), FileContent("test_calculator.py", "def test_no(): assert False")]
    monkeypatch.setattr(loop, "make_plan", lambda request: plan)
    monkeypatch.setattr(loop, "write_code", lambda plan: files)
    monkeypatch.setattr(loop, "write_files", lambda name, changed: tmp_path)
    monkeypatch.setattr(loop, "read_project_files", lambda project_dir: files)
    monkeypatch.setattr(loop, "usage_summary", lambda: {"calls": 6, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    monkeypatch.setattr(loop, "_write_report", lambda project_dir, report: None)

    def run(project_dir, plan):
        calls["run"] += 1
        return RunResult(1, "", "failed", 0.1)

    def fix(*args):
        calls["fix"] += 1
        return [FileContent("calculator.py", "pass")]

    monkeypatch.setattr(loop, "run_in_sandbox", run)
    monkeypatch.setattr(loop, "fix_code", fix)
    report = loop.build("calculator", max_attempts=5)
    assert report["success"] is False
    assert report["attempts_count"] == 5
    assert calls == {"run": 5, "fix": 4}


def test_fix_code_receives_error_output(monkeypatch):
    captured = {}

    def fake_ask_json(ask_fn, role, prompt, system):
        captured["prompt"] = prompt
        return {"files": [{"path": "calculator.py", "content": "fixed = True"}]}

    monkeypatch.setattr(coder, "ask_json", fake_ask_json)
    result = RunResult(1, "STDOUT marker", "STDERR marker", 0.2)
    changed = coder.fix_code(sample_plan(), [FileContent("calculator.py", "broken")], result)
    assert changed[0].content == "fixed = True"
    assert "STDOUT marker" in captured["prompt"]
    assert "STDERR marker" in captured["prompt"]
    assert "exit_code: 1" in captured["prompt"]


def test_clear_error_when_docker_missing(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Docker غير موجود"):
        sandbox.run_in_sandbox(Path("/tmp/project"), sample_plan())


def test_sandbox_uses_network_none_for_tests(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "/usr/bin/docker")

    def fake_run(args, capture_output, text, timeout, check):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(sandbox.subprocess, "run", fake_run)
    result = sandbox.run_in_sandbox(tmp_path, sample_plan())
    assert result.exit_code == 0
    assert len(calls) == 2
    assert "--network" not in calls[0]
    assert calls[1][calls[1].index("--network") + 1] == "none"
