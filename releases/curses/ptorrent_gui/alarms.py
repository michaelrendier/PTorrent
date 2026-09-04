"""Section alarms — user-defined heartbeat / condition alerts.

A rule fires against the live Engine.snapshot(). The canonical case: a job that
has been RUNNING for 12 days should ding once every 3 hours so you know it is
still alive. Rules also cover "running longer than", "idle for", "error count
over", and "all done".

evaluate(rules, snapshot, state, now) -> list[{rule, message}]   (mutates state)
fire(action, message, notif_cfg)                                  (bell/desktop/-)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time

WHEN = {
    "periodic_while_running": "ding every <interval> for as long as any/each job is RUNNING",
    "job_running_longer_than": "fire when a job has been RUNNING past <threshold> (then every <interval> if repeat)",
    "job_idle_for":            "fire when a RUNNING job's progress has not advanced for <threshold>",
    "error_count_over":        "fire when a job's error item count exceeds <count>",
    "all_done":                "fire once when every job has reached DONE",
}
UNITS = {"minutes": 60, "hours": 3600, "days": 86400}


def _secs(spec: dict) -> float:
    return float(spec.get("n", 1)) * UNITS.get(spec.get("unit", "hours"), 3600)


def _running(snapshot: dict) -> list[dict]:
    return [j for j in snapshot.get("jobs", []) if j.get("status") == "RUNNING"]


def _progress_key(job: dict) -> tuple:
    p = job.get("progress", {}) or {}
    return (p.get("studied"), p.get("skipped"), p.get("row_count"),
            (p.get("items") or {}).get("OK"))


def evaluate(rules: list[dict], snapshot: dict, state: dict, now: float | None = None) -> list[dict]:
    now = now or time.time()
    fired: list[dict] = []
    state.setdefault("last", {})       # rule/job -> last fire ts
    state.setdefault("seen", {})       # job -> (progress_key, ts)
    state.setdefault("started", {})    # job -> first-seen-RUNNING ts

    running = _running(snapshot)
    for j in running:
        state["started"].setdefault(j["id"], now)
        pk = _progress_key(j)
        prev = state["seen"].get(j["id"])
        if not prev or prev[0] != pk:
            state["seen"][j["id"]] = (pk, now)
    live_ids = {j["id"] for j in snapshot.get("jobs", [])}
    for d in ("started", "seen"):
        for gone in [k for k in state[d] if k not in live_ids]:
            state[d].pop(gone, None)

    for ri, rule in enumerate(rules):
        if not rule.get("enabled", True):
            continue
        when = rule.get("when", "periodic_while_running")
        every = _secs(rule.get("every", {"n": 3, "unit": "hours"}))
        thr = _secs(rule.get("threshold", {"n": 1, "unit": "hours"}))
        rkey = rule.get("name") or f"rule{ri}"
        targets = running if rule.get("scope", "any_job") == "each_job" else (
            running[:1] if running else [])

        def _due(key: str, interval: float) -> bool:
            last = state["last"].get(key, 0.0)
            if now - last >= interval:
                state["last"][key] = now
                return True
            return False

        if when == "periodic_while_running":
            if not running:
                continue
            if rule.get("scope") == "each_job":
                for j in running:
                    if _due(f"{rkey}:{j['id']}", every):
                        fired.append({"rule": rule,
                                      "message": _msg(rule, j, now, state)})
            else:
                if _due(rkey, every):
                    fired.append({"rule": rule,
                                  "message": _msg(rule, running[0], now, state,
                                                  extra=f"{len(running)} job(s) running")})

        elif when == "job_running_longer_than":
            for j in running:
                age = now - state["started"].get(j["id"], now)
                if age < thr:
                    continue
                key = f"{rkey}:{j['id']}"
                if not state["last"].get(key) or (rule.get("repeat") and _due(key, every)):
                    if not state["last"].get(key):
                        state["last"][key] = now
                    fired.append({"rule": rule, "message": _msg(rule, j, now, state)})

        elif when == "job_idle_for":
            for j in running:
                pk, since = state["seen"].get(j["id"], (None, now))
                if now - since >= thr and _due(f"{rkey}:{j['id']}", every):
                    fired.append({"rule": rule,
                                  "message": _msg(rule, j, now, state,
                                                  extra="no progress")})

        elif when == "error_count_over":
            want = int(rule.get("count", 5))
            for j in snapshot.get("jobs", []):
                errs = (j.get("progress", {}).get("items", {}) or {}).get("ERROR", 0)
                if errs > want and _due(f"{rkey}:{j['id']}", every):
                    fired.append({"rule": rule,
                                  "message": _msg(rule, j, now, state,
                                                  extra=f"{errs} errors")})

        elif when == "all_done":
            jobs = snapshot.get("jobs", [])
            if jobs and all(j.get("status") == "DONE" for j in jobs):
                if not state["last"].get(rkey):
                    state["last"][rkey] = now
                    fired.append({"rule": rule,
                                  "message": f"{rule.get('name','alarm')}: all {len(jobs)} job(s) DONE"})
            else:
                state["last"].pop(rkey, None)

    return fired


def _fmt_age(secs: float) -> str:
    d, r = divmod(int(secs), 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _msg(rule: dict, job: dict, now: float, state: dict, extra: str = "") -> str:
    age = now - state["started"].get(job.get("id"), now)
    p = job.get("progress", {}) or {}
    prog = ""
    if p.get("studied") is not None:
        prog = f"  studied {p['studied']} skipped {p.get('skipped', 0)}"
    elif p.get("row_count") is not None:
        prog = f"  rows {p['row_count']}"
    tail = f"  ({extra})" if extra else ""
    return (f"{rule.get('name', 'alarm')}: {job.get('name', '?')} still running "
            f"({_fmt_age(age)}){prog}{tail}")


# ── firing ─────────────────────────────────────────────────────────────────

def fire(action: str, message: str, notif_cfg: dict) -> None:
    if not notif_cfg.get("enabled", True):
        return
    chan = notif_cfg.get("channel", "bell")
    act = action or "bell"
    if act == "status":
        return                                  # caller renders it on the status line
    if act in ("bell",) and chan in ("bell", "both"):
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:  # noqa: BLE001
            pass
    if act in ("desktop", "bell") and chan in ("desktop", "both"):
        _desktop(message)


def _desktop(message: str) -> None:
    for tool in ("notify-send", "kdialog"):
        if shutil.which(tool):
            try:
                if tool == "notify-send":
                    subprocess.Popen([tool, "PTorrent", message],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen([tool, "--passivepopup", message, "6"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:  # noqa: BLE001
                pass
            return
