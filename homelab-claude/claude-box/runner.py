#!/usr/bin/env python3
"""claude-runner: the single door between automations (n8n, Home Assistant, cron) and Claude.

  POST /run/<job>   Authorization: Bearer $RUNNER_TOKEN   body -> job's stdin
  GET  /healthz     liveness + which job is running
  GET  /metrics     Prometheus metrics (runs, duration, tokens, estimated cost per job)

Rules that protect your Claude Pro limits:
  * only executable scripts in $JOBS_DIR whose names match [a-z0-9-] can run (no free-form prompts)
  * one job at a time (a second call gets HTTP 409 instead of queueing up usage)
  * a daily cap on total runs (HTTP 429), so a looping workflow cannot drain the week
Every run is appended to $JOB_LOG as one JSON line: the audit trail of your automation flow.
"""
import datetime as dt
import hmac
import json
import os
import re
import signal
import subprocess
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

JOBS_DIR = os.environ.get("JOBS_DIR", "/opt/claude-jobs")
LOG_FILE = os.environ.get("JOB_LOG", "/var/log/claude/jobs.jsonl")
TOKEN = os.environ.get("RUNNER_TOKEN", "")
TIMEOUT = int(os.environ.get("JOB_TIMEOUT", "900"))
MAX_PER_DAY = int(os.environ.get("JOB_MAX_RUNS_PER_DAY", "40"))
PORT = int(os.environ.get("RUNNER_PORT", "8787"))
MAX_INPUT = 200_000  # bytes. Big inputs = big token bills; pre-filter in n8n instead.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
TOKEN_TYPES = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

job_lock = threading.Lock()
state_lock = threading.Lock()
state = {"running": None, "day": dt.date.today(), "runs_today": 0}
m_runs = defaultdict(int)       # (job, status) -> count
m_seconds = defaultdict(float)  # job -> total seconds
m_tokens = defaultdict(int)     # (job, type) -> tokens
m_cost = defaultdict(float)     # job -> estimated USD (Pro is flat-rate; useful as a "weight")
m_last = {}                     # job -> unix time of last finish


def parse_result(stdout: str) -> dict:
    """Find the `claude -p --output-format json` result object in a job's stdout."""
    text = stdout.strip()
    candidates = [text] + [ln.strip() for ln in reversed(text.splitlines())]
    for c in candidates:
        if not c.startswith("{"):
            continue
        try:
            obj = json.loads(c)
        except ValueError:
            continue
        if isinstance(obj, dict) and (obj.get("type") == "result" or "usage" in obj):
            return obj
    return {}


def run_job(name: str, payload: str) -> dict:
    path = os.path.join(JOBS_DIR, f"{name}.sh")
    started = time.time()
    status, out, err = "ok", "", ""
    proc = subprocess.Popen(
        [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd="/workspace", start_new_session=True,
    )
    try:
        out, err = proc.communicate(payload, timeout=TIMEOUT)
        if proc.returncode != 0:
            status = "error"
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)  # kill the whole job tree, claude included
        out, err = proc.communicate()
        status = "timeout"

    seconds = round(time.time() - started, 2)
    res = parse_result(out or "")
    if res.get("is_error"):
        status = "error"
    usage = {k: int((res.get("usage") or {}).get(k) or 0) for k in TOKEN_TYPES}
    cost = float(res.get("total_cost_usd") or 0.0)
    result_text = res.get("result", out if not res else "")

    with state_lock:
        m_runs[(name, status)] += 1
        m_seconds[name] += seconds
        m_cost[name] += cost
        m_last[name] = time.time()
        for k, v in usage.items():
            m_tokens[(name, k)] += v

    record = {
        "ts": dt.datetime.now().isoformat(timespec="seconds"), "job": name, "status": status,
        "seconds": seconds, "turns": res.get("num_turns"), "usage": usage,
        "est_cost_usd": round(cost, 5), "session_id": res.get("session_id"),
        "result_preview": (result_text or "")[:400],
        "stderr_tail": (err or "")[-800:] if status != "ok" else "",
    }
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[runner] cannot write log: {exc}", flush=True)

    return {**record, "result": result_text}


def metrics_text() -> str:
    lines = []

    def emit(name, mtype, help_text, rows):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {mtype}")
        for labels, value in rows:
            lab = ",".join(f'{k}="{v}"' for k, v in labels.items())
            lines.append(f"{name}{{{lab}}} {value}" if lab else f"{name} {value}")

    with state_lock:
        emit("claude_job_runs_total", "counter", "Job runs by status",
             [({"job": j, "status": s}, n) for (j, s), n in m_runs.items()])
        emit("claude_job_duration_seconds_total", "counter", "Total seconds spent per job",
             [({"job": j}, v) for j, v in m_seconds.items()])
        emit("claude_job_tokens_total", "counter", "Tokens used by jobs, by type",
             [({"job": j, "type": t.replace("_input_tokens", "").replace("_tokens", "")}, v)
              for (j, t), v in m_tokens.items()])
        emit("claude_job_cost_usd_total", "counter", "List-price estimate (Pro is flat-rate)",
             [({"job": j}, round(v, 6)) for j, v in m_cost.items()])
        emit("claude_job_last_finish_timestamp_seconds", "gauge", "Unix time of last finish",
             [({"job": j}, int(v)) for j, v in m_last.items()])
        emit("claude_job_running", "gauge", "1 while a job is running", [({}, int(bool(state["running"])))])
        emit("claude_job_runs_today", "gauge", "Runs counted against the daily cap", [({}, state["runs_today"])])
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    server_version = "claude-runner/1"

    def _send(self, code: int, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (
            json.dumps(body, ensure_ascii=False).encode() if ctype == "application/json" else body.encode())
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # quieter access log
        print(f"[runner] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, {"ok": True, "running": state["running"], "runs_today": state["runs_today"]})
        if self.path == "/metrics":
            return self._send(200, metrics_text(), ctype="text/plain; version=0.0.4")
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not TOKEN:
            return self._send(503, {"error": "RUNNER_TOKEN is not configured"})
        auth = self.headers.get("Authorization", "")
        if not hmac.compare_digest(auth.encode(), f"Bearer {TOKEN}".encode()):
            return self._send(401, {"error": "unauthorized"})

        m = re.fullmatch(r"/run/([^/?#]+)", self.path)
        if not m or not NAME_RE.match(m.group(1)):
            return self._send(404, {"error": "unknown route or bad job name"})
        name = m.group(1)
        path = os.path.join(JOBS_DIR, f"{name}.sh")
        if not (os.path.isfile(path) and os.access(path, os.X_OK)):
            return self._send(404, {"error": f"no executable job '{name}'"})

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_INPUT:
            return self._send(413, {"error": f"input over {MAX_INPUT} bytes; filter it before sending"})
        payload = self.rfile.read(length).decode("utf-8", "replace") if length else ""

        with state_lock:
            if state["day"] != dt.date.today():
                state["day"], state["runs_today"] = dt.date.today(), 0
            if state["runs_today"] >= MAX_PER_DAY:
                return self._send(429, {"error": "daily job cap reached", "cap": MAX_PER_DAY})
        if not job_lock.acquire(blocking=False):
            return self._send(409, {"error": "busy", "running": state["running"]})
        try:
            with state_lock:
                state["running"] = name
                state["runs_today"] += 1
            result = run_job(name, payload)
        finally:
            with state_lock:
                state["running"] = None
            job_lock.release()
        return self._send(200 if result["status"] == "ok" else 500, result)


if __name__ == "__main__":
    print(f"[runner] listening on :{PORT}, jobs from {JOBS_DIR}, cap {MAX_PER_DAY}/day", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
