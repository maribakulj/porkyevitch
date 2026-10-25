"""Run a chain of steps on a Colab machine without ever leaving its kernel idle.

Lessons kept here so that no experiment has to relearn them (24-25/10/2026):
- a kernel left idle (a job started in the background, or a machine waiting between two jobs) is reclaimed by Colab and its
  disk is lost: every step runs inside ONE blocking cell, and the cell waits for go-ahead flags by polling, still busy;
- `colab exec` of a long cell ends on the client with "Timeout waiting for reply" while the cell goes on: launch it in the
  background and follow a log file on the machine with `colab download`;
- uploads over about 64 MB fail: send parts of 50 MB and join them on the machine;
- a second `exec` waits for the kernel to be free, so it cannot be used to look at a running chain; `download` and `upload` can.

Usage from an experiment's launcher:

    from porky import colab
    s = colab.Session("caype", gpu="T4")
    s.create()
    s.upload_parts(local_tar, "/content/ext/img.tar")
    s.start_chain([
        colab.Step("pip", "python -m pip install -q timm"),
        colab.Step("smoke", "python /content/run.py --smoke", env={"CAY_SMOKE": "64"}),
        colab.Wait("go_full"),
        colab.Step("full", "python /content/run.py"),
    ])
    s.watch(until=("CHAIN DONE",))   # returns the chain log; raises if the machine is lost
    s.download("/content/out/resultats.json", "results/resultats.json")
    s.stop()
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

CLI = os.environ.get("PORKY_COLAB", str(Path.home() / ".local/bin/colab"))
PART = 50 * 1024 * 1024


@dataclass
class Step:
    name: str
    command: str
    env: dict = field(default_factory=dict)


@dataclass
class Wait:
    flag: str  # waits for /content/<flag>, posted with Session.flag()
    hours: float = 6.0


def _cli(*args: str, stdin: str | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run([CLI, "--auth=adc", *args], input=stdin, capture_output=True, text=True, timeout=timeout)


class Session:
    def __init__(self, name: str, gpu: str = "T4"):
        self.name, self.gpu = name, gpu

    def create(self) -> None:
        r = _cli("new", "-s", self.name, "--gpu", self.gpu)
        if "READY" not in r.stdout + r.stderr:
            raise RuntimeError(r.stdout + r.stderr)
        self.run_short("import os; print('ok')")

    def alive(self) -> bool:
        return f"[{self.name}]" in _cli("sessions").stdout

    def run_short(self, code: str, timeout: float = 180) -> str:
        """A short cell (mkdir, a check). Never use it while a chain runs: it would wait for the kernel."""
        return _cli("exec", "-s", self.name, stdin=code, timeout=timeout).stdout

    def upload(self, local: str | Path, remote: str) -> None:
        r = _cli("upload", "-s", self.name, str(local), remote, timeout=900)
        if "Uploaded" not in r.stdout + r.stderr:
            raise RuntimeError(f"upload of {local} failed: {r.stdout}{r.stderr}")

    def upload_parts(self, local: str | Path, remote: str) -> list[str]:
        """Send a large file as 50 MB parts; the chain joins and checks them with
        Step('join', colab.join_command(remote, parts, colab.sha256(local)))."""
        local = Path(local)
        parts = []
        with open(local, "rb") as f, tempfile.TemporaryDirectory() as tmp:
            k = 0
            while chunk := f.read(PART):
                p = Path(tmp) / f"{local.name}.part{k:03d}"
                p.write_bytes(chunk)
                self.upload(p, f"{remote}.part{k:03d}")
                p.unlink()
                parts.append(f"{remote}.part{k:03d}")
                k += 1
        return parts

    def download(self, remote: str, local: str | Path) -> bool:
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        return "Downloaded" in _cli("download", "-s", self.name, remote, str(local)).stdout

    def flag(self, flag: str) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            pass
        self.upload(f.name, f"/content/{flag}")
        os.unlink(f.name)

    def start_chain(self, steps: list, log: str = "/content/chain.log") -> subprocess.Popen:
        """One blocking cell runs every step in order, waits for flags while staying busy, and stops at the first failure.
        The log is emptied first and the chain ends on 'CHAIN DONE <run id>', so a log left by an earlier chain never counts."""
        self.run_id = f"{int(time.time())}-{os.getpid()}"
        lines = [
            "import subprocess, sys, os, time",
            f"LOG = {log!r}",
            "open(LOG, 'w').close()",
            "def log(m):",
            "    open(LOG, 'a').write(time.strftime('%H:%M:%S ') + m + '\\n')",
            "def run(name, cmd, env):",
            "    log('start ' + name)",
            "    r = subprocess.run(f'{cmd} > /content/{name}.log 2>&1', shell=True, env=dict(os.environ, **env))",
            "    log(f'exit {r.returncode} ({name})')",
            "    return r.returncode == 0",
            "ok = True",
        ]
        for s in steps:
            if isinstance(s, Wait):
                lines += [
                    "if ok:",
                    f"    log('waiting for {s.flag}')",
                    "    t0 = time.time()",
                    f"    while not os.path.exists('/content/{s.flag}') and time.time() - t0 < {s.hours * 3600}:",
                    "        time.sleep(60)",
                    f"    ok = os.path.exists('/content/{s.flag}')",
                ]
            else:
                lines.append(f"ok = ok and run({s.name!r}, {s.command!r}, {s.env!r})")
        lines.append(f"log(f'CHAIN DONE {self.run_id} ok={{ok}}')")
        return _start(self.name, "\n".join(lines))

    def watch(self, until: tuple[str, ...] | None = None, every: float = 240, stall_minutes: float = 40,
              log: str = "/content/chain.log", progress: str | None = None) -> str:
        """Follow the chain until it ends ('CHAIN DONE <run id> ok=True' by default) and return its log.
        Raises if a step fails, the chain ends with ok=False, the machine is lost, or nothing moves."""
        until = until or (f"CHAIN DONE {self.run_id} ok=True",)
        with tempfile.TemporaryDirectory() as tmp:
            dest, prog = Path(tmp) / "chain.log", Path(tmp) / "progress.log"
            last, still = None, 0.0
            while True:
                if not self.alive():
                    raise RuntimeError(f"Colab session {self.name} lost")
                text = dest.read_text() if self.download(log, dest) else ""
                if re.search(r"exit [1-9]", text) or f"CHAIN DONE {getattr(self, 'run_id', '')} ok=False" in text:
                    raise RuntimeError(f"chain failed on {self.name}:\n{text}")
                if any(u in text for u in until):
                    return text
                state = text + (prog.read_text()[-500:] if progress and self.download(progress, prog) else "")
                still = still + every if state == last else 0.0
                last = state
                if still >= stall_minutes * 60:
                    raise RuntimeError(f"no progress for {stall_minutes} min on {self.name}")
                time.sleep(every)

    def stop(self) -> None:
        _cli("stop", "-s", self.name)


def _start(name: str, code: str) -> subprocess.Popen:
    p = subprocess.Popen([CLI, "--auth=adc", "exec", "-s", name], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, text=True)
    p.stdin.write(code)
    p.stdin.close()
    return p


def sha256(path: str | Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def join_command(remote: str, parts: list[str], expected_sha256: str) -> str:
    """Join the parts, check the whole against the local file's sha256, and only then remove the parts."""
    return (f"cat {' '.join(parts)} > {remote} && echo '{expected_sha256}  {remote}' | sha256sum -c - "
            f"&& rm {' '.join(parts)}")
