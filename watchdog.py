#!/usr/bin/env python3
"""
project-b81494 Watchdog
=========================
实时监控 A/B/C 三个 workflow 状态，挂了自动拉起。
每 30 秒轮询一次。
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

# Config
REPO = "wake875/project-b81494"
WORKFLOWS = {
    "A": "pnation_flood_a.yml",  # v2 domain
    "B": "pnation_flood_b.yml",  # v2 domain
    "C": "pnation_flood_c.yml",  # v2 domain
    "D": "pnation_flood_d.yml",  # v3 origin IP
    "E": "pnation_flood_e.yml",  # v3 origin IP
    "F": "pnation_flood_f.yml",  # v3 origin IP
}

# Get token from env: PAT > GITHUB_TOKEN > local file
TOKEN = os.environ.get("PAT") or os.environ.get("GITHUB_TOKEN") or ""
if not TOKEN:
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            TOKEN = f.read().strip()
if not TOKEN:
    print("ERROR: No token found. Set PAT env var or create .token file")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}
API_BASE = f"https://api.github.com/repos/{REPO}"

CST = timezone(timedelta(hours=8))
CHECK_INTERVAL = 300  # seconds
STALE_THRESHOLD = 3600  # 1 hour - queued runs may wait a long time for runners
ANTI_SPAM = 120  # seconds - don't trigger if any run created in last 2min

stats = {"triggered": 0, "checks": 0}


def now_str():
    return datetime.now(CST).strftime("%H:%M:%S")


def get_latest_runs():
    """Get latest workflow runs, return dict {name: status_list}"""
    url = f"{API_BASE}/actions/runs?per_page=50&event=workflow_dispatch"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        runs = data.get("workflow_runs", [])
        return runs
    except Exception as e:
        print(f"[{now_str()}] WARN: API error: {e}")
        return []


def trigger_workflow(wf_name, wf_file):
    """Trigger a workflow_dispatch"""
    url = f"{API_BASE}/actions/workflows/{wf_file}/dispatches"
    try:
        r = requests.post(url, json={"ref": "main"}, headers=HEADERS, timeout=10)
        if r.status_code == 204:
            stats["triggered"] += 1
            return True
        else:
            print(f"[{now_str()}] FAIL: Trigger {wf_name} failed: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"[{now_str()}] FAIL: Trigger {wf_name} error: {e}")
        return False


def clean_own_old_queues():
    """Cancel old queued watchdog runs (keep only latest)"""
    url = f"{API_BASE}/actions/workflows/pnation_watchdog.yml/runs?per_page=10&status=queued"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        queued = r.json().get("workflow_runs", [])
        if len(queued) <= 1:
            return
        ids = sorted([q["id"] for q in queued], reverse=True)
        for old_id in ids[1:]:
            requests.post(f"{API_BASE}/actions/runs/{old_id}/cancel", headers=HEADERS, timeout=5)
            print(f"[{now_str()}] Cleaned old watchdog run {old_id}")
    except Exception as e:
        pass  # Non-critical


def check_and_heal():
    """Main watchdog loop"""
    stats["checks"] += 1
    runs = get_latest_runs()
    if not runs:
        return

    now_utc = datetime.now(timezone.utc)
    health = {wf: {"running": False, "queued": False, "last_seen": None} for wf in WORKFLOWS}

    for run in runs:
        name = run.get("name", "")
        for wf_id in WORKFLOWS:
            if wf_id in name.replace("pnation-flood-", ""):
                status = run.get("status", "")
                created = run.get("created_at", "")
                if created:
                    ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if health[wf_id]["last_seen"] is None or ct > health[wf_id]["last_seen"]:
                        health[wf_id]["last_seen"] = ct

                if status == "in_progress":
                    health[wf_id]["running"] = True
                elif status == "queued":
                    health[wf_id]["queued"] = True
                # Don't break: process ALL runs, not just the latest one

    # Build status line (ASCII only for Windows compat)
    status_parts = []
    all_healthy = True

    for wf_id in WORKFLOWS:
        h = health[wf_id]
        if h["running"]:
            status_parts.append(f"{wf_id}:RUNNING")
        elif h["queued"]:
            status_parts.append(f"{wf_id}:queued ")
        else:
            if h["last_seen"]:
                age = (now_utc - h["last_seen"]).total_seconds()
                if age > STALE_THRESHOLD:
                    status_parts.append(f"{wf_id}:DEAD({int(age)}s)")
                    all_healthy = False
                else:
                    status_parts.append(f"{wf_id}:wait({int(age)}s)")
            else:
                status_parts.append(f"{wf_id}:???    ")
                all_healthy = False

    line = f"[{now_str()}] #{stats['checks']:03d} | {' | '.join(status_parts)}"
    if all_healthy:
        line += " | OK"
    else:
        line += " | HEALING"

    print(line)

    if not all_healthy:
        for wf_id, wf_file in WORKFLOWS.items():
            h = health[wf_id]
            if not h["running"] and not h["queued"]:
                # Anti-spam: don't trigger if any recent run exists
                if h["last_seen"] and (now_utc - h["last_seen"]).total_seconds() < ANTI_SPAM:
                    continue
                if h["last_seen"] is None or (now_utc - h["last_seen"]).total_seconds() > STALE_THRESHOLD:
                    print(f"  -> Triggering {wf_id}...")
                    trigger_workflow(wf_id, wf_file)
                    time.sleep(2)


def main():
    once = "--once" in sys.argv
    print("=" * 55)
    print("  pnation.com DB Flood Watchdog")
    print(f"  Interval: {CHECK_INTERVAL}s | Stale: {STALE_THRESHOLD}s | Auto-heal: ON")
    print(f"  Mode: {'single-check (GitHub Actions)' if once else 'continuous'}")
    print(f"  Started: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} CST")
    print("=" * 55)

    clean_own_old_queues()  # Clean previous watchdog queued runs

    try:
        if once:
            check_and_heal()
        else:
            while True:
                check_and_heal()
                time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] Stopped. Checks: {stats['checks']}, Triggered: {stats['triggered']}")


if __name__ == "__main__":
    main()
