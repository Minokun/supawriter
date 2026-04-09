import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import start_unified


def test_windows_port_cleanup_avoids_shell_pipeline(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))

        class Result:
            stdout = ""

        result = Result()
        if args == ["netstat", "-ano"]:
            result.stdout = (
                "TCP    127.0.0.1:49677   127.0.0.1:3000   ESTABLISHED   1111\n"
                "TCP    0.0.0.0:3000     0.0.0.0:0        LISTENING     4321\n"
            )
        return result

    monkeypatch.setattr(start_unified.sys, "platform", "win32")
    monkeypatch.setattr(start_unified.subprocess, "run", fake_run)
    monkeypatch.setattr(start_unified.time, "sleep", lambda *_args, **_kwargs: None)

    start_unified.kill_process_on_port(3000)

    assert calls, "expected subprocess.run to be invoked on Windows"
    first_args, first_kwargs = calls[0]
    taskkill_calls = [call_args for call_args, _ in calls[1:]]

    assert first_args == ["netstat", "-ano"]
    assert not first_kwargs.get("shell", False)
    assert all("|" not in call_args for call_args, _ in calls)
    assert all("findstr" not in call_args for call_args, _ in calls)
    assert taskkill_calls == [["taskkill", "/F", "/PID", "4321"]]


def test_posix_port_cleanup_uses_lsof_and_terminates_each_pid(monkeypatch):
    calls = []
    killed = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="123\n456\n")

    monkeypatch.setattr(start_unified.sys, "platform", "linux")
    monkeypatch.setattr(start_unified.subprocess, "run", fake_run)
    monkeypatch.setattr(start_unified.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(start_unified.time, "sleep", lambda *_args, **_kwargs: None)

    start_unified.kill_process_on_port(8501)

    assert calls[0][0] == ["lsof", "-ti", ":8501"]
    assert killed == [
        (123, start_unified.signal.SIGTERM),
        (456, start_unified.signal.SIGTERM),
    ]


def test_check_port_available_closes_socket_when_bind_fails(monkeypatch):
    class FakeSocket:
        def __init__(self):
            self.closed = False

        def bind(self, _address):
            raise OSError("in use")

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    monkeypatch.setattr(start_unified.socket, "socket", lambda *_args, **_kwargs: fake_socket)

    assert start_unified.check_port_available(3000) is False
    assert fake_socket.closed is True


def test_start_service_uses_inherited_stdio(monkeypatch):
    popen_calls = []
    stdout_marker = SimpleNamespace(fileno=lambda: 1)
    stderr_marker = SimpleNamespace(fileno=lambda: 2)

    class FakeProcess:
        pid = 4321

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(start_unified, "check_port_available", lambda _port: True)
    monkeypatch.setattr(start_unified.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(start_unified.sys, "stdout", stdout_marker)
    monkeypatch.setattr(start_unified.sys, "stderr", stderr_marker)

    config = {
        "enabled": True,
        "name": "demo",
        "port": 3000,
        "command": ["demo", "serve"],
        "cwd": start_unified.PROJECT_ROOT,
        "url": "http://localhost:3000",
    }

    process = start_unified.start_service("demo", config)

    assert process.pid == 4321
    assert popen_calls
    _, kwargs = popen_calls[0]
    assert kwargs["stdout"] is stdout_marker
    assert kwargs["stderr"] is stderr_marker


def test_check_dependencies_uses_uv_runtime_for_streamlit(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="1.2.3\n")

    monkeypatch.setattr(start_unified.shutil, "which", lambda name: "/opt/homebrew/bin/uv" if name == "uv" else None)
    monkeypatch.setattr(start_unified.subprocess, "run", fake_run)
    monkeypatch.setitem(start_unified.SERVICES["frontend"], "enabled", False)

    assert start_unified.check_dependencies() is True
    assert calls[0][0][:3] == ["uv", "run", "python"]
