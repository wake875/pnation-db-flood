#!/usr/bin/env python3
"""
pnation.com 恢复监控
每 30 秒检测一次，一旦网站恢复就通知
"""
import requests, urllib3, time, datetime
urllib3.disable_warnings()

print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 监控中... pnation.com 当前瘫痪")

while True:
    try:
        r = requests.get("https://pnation.com/", verify=False, timeout=10)
        if r.status_code == 200 and len(r.text) > 10000:
            now = datetime.datetime.now().strftime('%H:%M:%S')
            print(f"\n[{now}] 🔔 pnation.com 已恢复！")
            print(f"    HTTPS: 200 OK | {len(r.text)} 字节")
            
            # Test DB
            try:
                r2 = requests.post("https://pnation.com/bbs/login_check.php",
                    data={"mb_id": "admin", "mb_password": "x", "url": "https://pnation.com"},
                    verify=False, timeout=8, allow_redirects=False)
                if "Connect Error" not in r2.text and len(r2.text) > 1000:
                    print(f"    DB: 已恢复！可以开始爆破")
                else:
                    print(f"    DB: 尚未恢复")
            except:
                print(f"    DB: 超时")
            break
    except:
        pass
    
    time.sleep(30)
