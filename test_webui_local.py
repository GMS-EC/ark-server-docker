import os, sys, json, base64, time, re, threading, http.client
from unittest.mock import patch, MagicMock

TEST_PORT  = 19080
ADMIN_PASS = "testpass123"

os.environ.update({
    "ADMIN_PASSWORD": ADMIN_PASS,
    "SESSION_NAME":   "Test ARK Server",
    "WORLD":          "TheIsland_Test",
    "MAX_PLAYERS":    "20",
})

os.system("")
G="\033[92m"; R="\033[91m"; Y="\033[93m"; C="\033[96m"; D="\033[2m"; W="\033[0m"
passed, failed = [], []

def ok(msg):
    print(f"  {G}+PASS{W}  {msg}")
    passed.append(msg)

def err(msg, detail=""):
    print(f"  {R}-FAIL{W}  {msg}" + (f"\n         {Y}-> {detail}{W}" if detail else ""))
    failed.append(msg)

def check(label, cond, detail=""):
    if cond:
        ok(label)
    else:
        err(label, detail)
    return cond

def _mock_run(cmd, *a, **kw):
    r = MagicMock(); r.returncode = 1; r.stdout = b""; r.stderr = b""; return r

print(f"\n{C}=== ARK WebUI Local Integration Test ==={W}")
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

with patch("subprocess.run", side_effect=_mock_run), \
     patch("subprocess.check_output", side_effect=Exception("mocked")):
    import webui

import subprocess as _sub
_sub.run = _mock_run

print(f"  Starting server on 127.0.0.1:{TEST_PORT}...")
try:
    srv = webui.ThreadedHTTPServer(("127.0.0.1", TEST_PORT), webui.WebUIHandler)
except OSError as e:
    print(f"  {R}ERROR binding port {TEST_PORT}: {e}{W}"); sys.exit(1)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)
print(f"  {G}Server ready.{W}\n")

def b64(pw):
    return "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()

def req(method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", TEST_PORT, timeout=5)
    h = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=h)
    else:
        conn.request(method, path, headers=h)
    r = conn.getresponse()
    return r.status, r.read()

def find_token(html):
    m = re.search(r"const WEBUI_TOKEN\s*=\s*'([0-9a-f]+)'", html)
    return m.group(1) if m else None

print(f"{C}-- 1. HTTP Basic Auth Tests --{W}")
s, _ = req("GET", "/"); check("No credentials -> 401", s == 401, f"Got HTTP {s}")
s, _ = req("GET", "/", headers={"Authorization": b64("hackerpass")}); check("Wrong password -> 401", s == 401, f"Got HTTP {s}")
s, raw = req("GET", "/", headers={"Authorization": b64(ADMIN_PASS)})
html_ok = check("Correct Basic Auth -> 200 HTML", s == 200, f"Got HTTP {s}")
html = raw.decode(errors="replace") if html_ok else ""
if html_ok:
    check("Response contains <html>", "<html" in html.lower())

print(f"\n{C}-- 2. Token Injection Tests --{W}")
token = None
if html_ok:
    check("No raw {{TOKEN}} in HTML", "{{TOKEN}}" not in html, "Placeholder not replaced")
    token = find_token(html)
    if check("WEBUI_TOKEN JS var present", token is not None, "const WEBUI_TOKEN not found in HTML"):
        is_hex = all(c in "0123456789abcdef" for c in token)
        check(f"Token is 64-char hex ({token[:12]}...)", len(token) == 64 and is_hex, f"len={len(token)}")
        check("Token matches server _SESSION_TOKEN", token == webui._SESSION_TOKEN, "Mismatch!")

print(f"\n{C}-- 3. /api/stats Tests --{W}")
if token:
    s, raw = req("GET", "/api/stats", headers={"X-WebUI-Token": token})
    if check("/api/stats with token -> 200", s == 200, f"Got HTTP {s}"):
        try:
            data = json.loads(raw)
        except Exception as e:
            err("Valid JSON", str(e)); data = {}
        for field in ["cpu_percent","mem_used_bytes","mem_limit_bytes","mem_percent","server_status","players_online","max_players","session_name","world"]:
            check(f"  field '{field}'", field in data)
        check("  session_name == Test ARK Server", data.get("session_name") == "Test ARK Server", f"Got '{data.get('session_name')}'")
        check("  world == TheIsland_Test", data.get("world") == "TheIsland_Test", f"Got '{data.get('world')}'")
        check("  max_players == 20", data.get("max_players") == "20", f"Got '{data.get('max_players')}'")
        check("  cpu_percent is numeric", isinstance(data.get("cpu_percent"), (int, float)))
        check("  players_online is int", isinstance(data.get("players_online"), int))
        print(f"  {D}status={data.get('server_status')}  cpu={data.get('cpu_percent')}%  mem={data.get('mem_used_bytes',0)//1048576}MB/{data.get('mem_limit_bytes',0)//1048576}MB{W}")

print(f"\n{C}-- 4. /api/logs Tests --{W}")
if token:
    s, raw = req("GET", "/api/logs", headers={"X-WebUI-Token": token})
    if check("/api/logs with token -> 200", s == 200, f"Got HTTP {s}"):
        try:
            logs = json.loads(raw)
            check("  Is a JSON list", isinstance(logs, list))
            check("  List not empty", len(logs) > 0)
            if logs: print(f"  {D}First: {str(logs[0])[:80]}{W}")
        except Exception as e:
            err("  Valid JSON", str(e))

print(f"\n{C}-- 5. Security Tests --{W}")
s, _ = req("GET", "/api/stats", headers={"X-WebUI-Token": "a"*64}); check("Wrong token -> 401", s == 401, f"Got HTTP {s}")
if token:
    s, _ = req("GET", "/api/stats", headers={"X-WebUI-Token": token[:32]}); check("Truncated token -> 401", s == 401, f"Got HTTP {s}")
for path in ["/api/stats", "/api/logs"]:
    s, _ = req("GET", path); check(f"No auth on {path} -> 401", s == 401, f"Got HTTP {s}")
s, _ = req("POST", "/api/action", body={"action": "saveworld"}); check("POST /api/action no auth -> 401", s == 401, f"Got HTTP {s}")
if token:
    s, _ = req("GET", "/nonexistent", headers={"X-WebUI-Token": token}); check("Unknown path -> 404", s == 404, f"Got HTTP {s}")

srv.shutdown()
total = len(passed) + len(failed)
print(f"\n{C}=== Results ==={W}")
print(f"  {G}{len(passed)}{W}/{total} passed   {R}{len(failed)}{W} failed")
if failed:
    print(f"\n  {R}Failed:{W}")
    for f in failed: print(f"    * {f}")
    print(); sys.exit(1)
else:
    print(f"\n  {G}All {total} tests passed! webui.py is working correctly.{W}\n"); sys.exit(0)
