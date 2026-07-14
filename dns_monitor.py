#!/usr/bin/env python3
"""DNS Monitor: track pnation.com origin IP, auto-update v3 target"""
import socket, subprocess, os, re, json, time

TARGET_FILE = "pnation_db_flood_v3.py"
DOMAIN = "pnation.com"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def get_current_ip():
    """Resolve pnation.com A record"""
    try:
        ips = socket.gethostbyname_ex(DOMAIN)
        return ips[2][0]  # First IP
    except:
        return None

def get_target_ip():
    """Read hardcoded IP from v3 script"""
    path = os.path.join(REPO_DIR, TARGET_FILE)
    try:
        with open(path) as f:
            for line in f:
                m = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if m and 'TARGET' in f.read()[:100]:
                    pass
        # Re-read
        with open(path) as f:
            content = f.read()
        m = re.search(r'TARGET\s*=\s*"https://(\d+\.\d+\.\d+\.\d+)"', content)
        if m:
            return m.group(1)
    except:
        pass
    return None

def update_target(new_ip):
    """Update v3 script with new IP"""
    path = os.path.join(REPO_DIR, TARGET_FILE)
    with open(path) as f:
        content = f.read()
    
    old_pattern = r'TARGET\s*=\s*"https://\d+\.\d+\.\d+\.\d+"'
    new_line = f'TARGET = "https://{new_ip}"  # auto-tracked DNS'
    
    if re.search(old_pattern, content):
        new_content = re.sub(old_pattern, new_line, content)
    else:
        return False
    
    with open(path, 'w') as f:
        f.write(new_content)
    return True

def git_commit_push():
    """Commit and push changes"""
    cmds = [
        ['git', 'config', 'user.email', 'dns-monitor@auto.local'],
        ['git', 'config', 'user.name', 'DNS Monitor Bot'],
        ['git', 'add', TARGET_FILE],
        ['git', 'diff', '--cached', '--quiet'],
    ]
    
    try:
        # Check if there are changes
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO_DIR)
        if result.returncode == 0:
            print("No changes to commit")
            return
        
        subprocess.run(['git', 'config', 'user.email', 'dns-monitor@auto.local'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'config', 'user.name', 'DNS Monitor Bot'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'commit', '-m', f'dns: update origin IP to {new_ip}'], cwd=REPO_DIR, check=True)
        
        # Push using PAT
        token = os.environ.get('PAT') or os.environ.get('GITHUB_TOKEN')
        if token:
            subprocess.run(['git', 'push', f'https://x-access-token:{token}@github.com/wake875/project-b81494.git', 'main'],
                          cwd=REPO_DIR, check=True, capture_output=True)
            print(f"Pushed IP update: {new_ip}")
    except Exception as e:
        print(f"Git error: {e}")

if __name__ == "__main__":
    current = get_current_ip()
    target = get_target_ip()
    
    print(f"[DNS Monitor] Domain: {DOMAIN}")
    print(f"  Resolved IP:  {current}")
    print(f"  Script IP:    {target}")
    
    if not current:
        print("  DNS resolution failed - domain might be down")
        exit(0)
    
    if current != target:
        print(f"\n  >>> IP CHANGED! Updating v3 target...")
        if update_target(current):
            new_ip = current
            git_commit_push()
            print("  v3 target updated successfully")
        else:
            print("  Failed to update v3 target")
    else:
        print("  IP unchanged - no action needed")
