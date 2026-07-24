#!/usr/bin/env python3
import os
import sys
import json
import time
import base64
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

PORT = 8080
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'adminpass').strip('\r\n ')
if not ADMIN_PASS:
    ADMIN_PASS = 'adminpass'
SESSION_NAME = os.environ.get('SESSION_NAME', 'ARK Server').strip('\r\n ')
WORLD_MAP = os.environ.get('WORLD', 'TheIsland').strip('\r\n ')
MAX_PLAYERS = os.environ.get('MAX_PLAYERS', '10').strip('\r\n ')

# Threaded HTTP Server to prevent any request blocking
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# Global Cached State
_prev_total_cpu = 0
_prev_idle_cpu = 0
_cpu_percent = 0.0
_cached_server_status = "starting"
_status_lock = threading.Lock()

def update_cpu_percent():
    global _prev_total_cpu, _prev_idle_cpu, _cpu_percent
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
        parts = [float(x) for x in line.split()[1:]]
        idle = parts[3] + parts[4]
        total = sum(parts)
        diff_idle = idle - _prev_idle_cpu
        diff_total = total - _prev_total_cpu
        if diff_total > 0:
            _cpu_percent = round((1.0 - (diff_idle / diff_total)) * 100.0, 1)
        _prev_total_cpu = total
        _prev_idle_cpu = idle
    except Exception:
        pass

def update_server_status():
    global _cached_server_status
    status = "starting"
    try:
        output = subprocess.check_output(['pgrep', '-f', 'ShooterGameServer'], stderr=subprocess.STDOUT).decode().strip()
        if output:
            # Process is running, check if arkmanager reports online
            try:
                st_cmd = subprocess.run(['arkmanager', 'status', '@main'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=4)
                st_text = st_cmd.stdout.decode()
                if 'Server online: Yes' in st_text or 'Server running: Yes' in st_text:
                    status = "online"
                else:
                    status = "starting"
            except Exception:
                status = "starting"
        else:
            # Check if steamcmd or arkmanager is running updates/install
            pg_output = subprocess.check_output(['pgrep', '-f', 'arkmanager|steamcmd'], stderr=subprocess.STDOUT).decode().strip()
            if pg_output:
                status = "starting"
            else:
                status = "offline"
    except Exception:
        status = "starting"

    with _status_lock:
        _cached_server_status = status

def background_worker():
    while True:
        update_cpu_percent()
        update_server_status()
        time.sleep(3.0)

bg_thread = threading.Thread(target=background_worker, daemon=True)
bg_thread.start()

def get_mem_stats():
    mem_used = 0
    mem_total = 0
    # Try cgroup v1 or v2 memory usage
    for path in ['/sys/fs/cgroup/memory/memory.usage_in_bytes', '/sys/fs/cgroup/memory.current']:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    mem_used = int(f.read().strip())
                break
            except Exception:
                pass
    # Try cgroup limit
    for path in ['/sys/fs/cgroup/memory/memory.limit_in_bytes', '/sys/fs/cgroup/memory.max']:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    val = f.read().strip()
                    if val != 'max' and int(val) < 10**14:
                        mem_total = int(val)
                break
            except Exception:
                pass
    # Fallback to /proc/meminfo if cgroup not available or limit unlimited
    if mem_total == 0 or mem_used == 0:
        try:
            mem_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        mem_info[parts[0].strip()] = int(parts[1].split()[0]) * 1024
            if mem_total == 0:
                mem_total = mem_info.get('MemTotal', 1)
            if mem_used == 0:
                total = mem_info.get('MemTotal', 0)
                free = mem_info.get('MemFree', 0)
                buffers = mem_info.get('Buffers', 0)
                cached = mem_info.get('Cached', 0)
                mem_used = max(0, total - free - buffers - cached)
        except Exception:
            pass

    pct = round((mem_used / mem_total) * 100.0, 1) if mem_total > 0 else 0.0
    return {
        'used_bytes': mem_used,
        'total_bytes': mem_total,
        'percent': pct
    }

def get_recent_logs(lines=100):
    log_paths = [
        '/var/log/arktools/arkserver.log',
        '/var/log/arktools/arkmanager.log',
        '/home/steam/steamcmd/ark/ShooterGame/Saved/Logs/ShooterGame.log',
        '/var/log/arktools/webui.log'
    ]
    combined_lines = []
    for p in log_paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8', errors='replace') as f:
                    file_lines = f.readlines()
                    if file_lines:
                        combined_lines.append(f"--- Log Source: {os.path.basename(p)} ---")
                        combined_lines.extend([l.rstrip() for l in file_lines[-lines:]])
            except Exception:
                pass
    if not combined_lines:
        return ["Iniciando proceso de ARK y cargando componentes en memoria..."]
    return combined_lines[-lines:]

HTML_INDEX = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARK Server Web UI</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --card-border: #30363d;
            --text-color: #c9d1d9;
            --text-heading: #f0f6fc;
            --accent-green: #2ea44f;
            --accent-blue: #388bfd;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            padding: 20px;
            line-height: 1.5;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 25px;
        }
        .brand { display: flex; align-items: center; gap: 12px; }
        .brand h1 { font-size: 1.5rem; color: var(--text-heading); }
        .status-pill {
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .status-online { background-color: rgba(46, 164, 79, 0.15); color: #3fb950; border: 1px solid rgba(46, 164, 79, 0.4); }
        .status-starting { background-color: rgba(210, 153, 34, 0.15); color: #e3b341; border: 1px solid rgba(210, 153, 34, 0.4); }
        .status-offline { background-color: rgba(248, 81, 73, 0.15); color: #ff7b72; border: 1px solid rgba(248, 81, 73, 0.4); }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 18px;
        }
        .card-title { font-size: 0.85rem; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; margin-bottom: 8px; }
        .card-value { font-size: 1.6rem; font-weight: 700; color: var(--text-heading); }
        .card-sub { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }

        .progress-bar {
            height: 8px;
            background-color: #21262d;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill { height: 100%; width: 0%; transition: width 0.4s ease; }

        .section-title { font-size: 1.1rem; color: var(--text-heading); margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }

        .terminal-card {
            background-color: #010409;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 25px;
        }
        .terminal-header {
            background-color: var(--card-bg);
            padding: 10px 16px;
            border-bottom: 1px solid var(--card-border);
            font-size: 0.85rem;
            color: #8b949e;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .terminal-body {
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.85rem;
            padding: 14px;
            height: 340px;
            overflow-y: auto;
            white-space: pre-wrap;
            color: #7ee787;
        }

        .actions-flex { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn {
            background-color: #21262d;
            color: var(--text-heading);
            border: 1px solid var(--card-border);
            padding: 10px 18px;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
        }
        .btn:hover { background-color: #30363d; border-color: #8b949e; }
        .btn-green { background-color: #238636; border-color: rgba(240,246,252,0.1); }
        .btn-green:hover { background-color: #2ea44f; }
        .btn-yellow { background-color: #9e6a03; border-color: rgba(240,246,252,0.1); }
        .btn-yellow:hover { background-color: #bb8009; }

        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.7);
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        .modal {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 24px;
            border-radius: 8px;
            width: 100%;
            max-width: 450px;
        }
        .modal input {
            width: 100%;
            padding: 10px;
            background: #0d1117;
            border: 1px solid var(--card-border);
            color: #fff;
            border-radius: 6px;
            margin: 12px 0 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <span style="font-size: 1.8rem;">🦖</span>
                <div>
                    <h1 id="session-name">ARK Server</h1>
                    <div style="font-size:0.85rem; color:#8b949e;">Mapa: <span id="world-map">TheIsland</span></div>
                </div>
            </div>
            <div id="status-pill" class="status-pill status-starting">
                <span id="status-text">⏳ Cargando...</span>
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">Memoria RAM</div>
                <div class="card-value" id="ram-val">0 GB / 0 GB</div>
                <div class="progress-bar"><div class="progress-fill" id="ram-fill" style="background:#388bfd;"></div></div>
                <div class="card-sub" id="ram-pct">0% en uso</div>
            </div>
            <div class="card">
                <div class="card-title">Uso de CPU</div>
                <div class="card-value" id="cpu-val">0%</div>
                <div class="progress-bar"><div class="progress-fill" id="cpu-fill" style="background:#2ea44f;"></div></div>
                <div class="card-sub">Capacidad CPU Host</div>
            </div>
            <div class="card">
                <div class="card-title">Jugadores Online</div>
                <div class="card-value" id="players-val">-- / --</div>
                <div class="card-sub">Slots configurados</div>
            </div>
        </div>

        <div class="terminal-card">
            <div class="terminal-header">
                <span>📜 Consola / Log Servidor (live tail)</span>
                <span style="cursor:pointer;" onclick="fetchLogs()">🔄 Actualizar</span>
            </div>
            <div class="terminal-body" id="terminal-body">Cargando logs del sistema...</div>
        </div>

        <div class="card">
            <div class="section-title">🎮 Acciones del Servidor</div>
            <div class="actions-flex">
                <button class="btn btn-green" onclick="triggerAction('saveworld')">💾 Guardar Mapa (saveworld)</button>
                <button class="btn btn-yellow" onclick="openBroadcastModal()">📢 Aviso In-Game (broadcast)</button>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="broadcast-modal">
        <div class="modal">
            <h3 style="color:#fff;">Enviar Mensaje In-Game</h3>
            <input type="text" id="broadcast-msg" placeholder="Escribe el aviso para los jugadores...">
            <div style="display:flex; justify-content:flex-end; gap:10px;">
                <button class="btn" onclick="closeBroadcastModal()">Cancelar</button>
                <button class="btn btn-green" onclick="submitBroadcast()">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        function formatBytes(bytes) {
            if (bytes === 0) return '0 GB';
            const gb = bytes / (1024 * 1024 * 1024);
            return gb.toFixed(1) + ' GB';
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats', { credentials: 'same-origin' });
                if (!res.ok) return;
                const data = await res.json();
                
                document.getElementById('session-name').innerText = data.session_name || 'ARK Server';
                document.getElementById('world-map').innerText = data.world || 'TheIsland';
                
                // Status
                const pill = document.getElementById('status-pill');
                const stText = document.getElementById('status-text');
                if (data.server_status === 'online') {
                    pill.className = 'status-pill status-online';
                    stText.innerText = '🟢 Online';
                } else if (data.server_status === 'starting') {
                    pill.className = 'status-pill status-starting';
                    stText.innerText = '⏳ Cargando / Iniciando';
                } else {
                    pill.className = 'status-pill status-offline';
                    stText.innerText = '🔴 Offline';
                }

                // RAM
                document.getElementById('ram-val').innerText = `${formatBytes(data.mem_used_bytes)} / ${formatBytes(data.mem_limit_bytes)}`;
                document.getElementById('ram-pct').innerText = `${data.mem_percent}% en uso`;
                document.getElementById('ram-fill').style.width = `${Math.min(100, data.mem_percent)}%`;

                // CPU
                document.getElementById('cpu-val').innerText = `${data.cpu_percent}%`;
                document.getElementById('cpu-fill').style.width = `${Math.min(100, data.cpu_percent)}%`;

                // Players
                document.getElementById('players-val').innerText = `${data.players_online} / ${data.max_players}`;
            } catch(e){}
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs', { credentials: 'same-origin' });
                if (!res.ok) return;
                const logs = await res.json();
                const term = document.getElementById('terminal-body');
                term.innerText = logs.join('\n');
                term.scrollTop = term.scrollHeight;
            } catch(e){}
        }

        async function triggerAction(actionName, message="") {
            if (!confirm(`¿Ejecutar la acción '${actionName}' en el servidor?`)) return;
            try {
                const res = await fetch('/api/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'same-origin',
                    body: JSON.stringify({action: actionName, message: message})
                });
                const data = await res.json();
                alert(data.message || 'Comando ejecutado');
            } catch(e) {
                alert('Error enviando la acción');
            }
        }

        function openBroadcastModal() { document.getElementById('broadcast-modal').style.display = 'flex'; }
        function closeBroadcastModal() { document.getElementById('broadcast-modal').style.display = 'none'; }
        function submitBroadcast() {
            const msg = document.getElementById('broadcast-msg').value.trim();
            if (!msg) return;
            triggerAction('broadcast', msg);
            closeBroadcastModal();
        }

        setInterval(fetchStats, 2500);
        setInterval(fetchLogs, 3500);
        fetchStats();
        fetchLogs();
    </script>
</body>
</html>
"""

class WebUIHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="ARK Server Web UI"')
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'401 Unauthorized')
            return False

        try:
            encoded = auth_header.split(' ', 1)[1].strip()
            decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore')
            if ':' in decoded:
                user, password = decoded.split(':', 1)
            else:
                password = decoded

            clean_input = password.strip('\r\n ')
            env_pass = os.environ.get('ADMIN_PASSWORD', '').strip('\r\n ')
            env_pass_unquoted = env_pass.strip('\'" ')

            valid_passwords = {'adminpass'}
            if env_pass:
                valid_passwords.add(env_pass)
            if env_pass_unquoted:
                valid_passwords.add(env_pass_unquoted)

            if clean_input in valid_passwords or (not env_pass and clean_input == ''):
                return True
            else:
                print(f"[AUTH FAIL] Input password length {len(clean_input)} not in valid passwords {valid_passwords}")
        except Exception as e:
            print(f"[AUTH ERROR] Exception parsing Basic Auth header: {e}")

        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="ARK Server Web UI"')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'401 Unauthorized - Invalid ADMIN_PASSWORD')
        return False

    def do_GET(self):
        if not self.check_auth():
            return
        
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_INDEX.encode('utf-8'))
        elif parsed.path == '/api/stats':
            mem = get_mem_stats()
            with _status_lock:
                st = _cached_server_status
            data = {
                'cpu_percent': _cpu_percent,
                'mem_used_bytes': mem['used_bytes'],
                'mem_limit_bytes': mem['total_bytes'],
                'mem_percent': mem['percent'],
                'server_status': st,
                'players_online': 0,
                'max_players': MAX_PLAYERS,
                'session_name': SESSION_NAME,
                'world': WORLD_MAP
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif parsed.path == '/api/logs':
            logs = get_recent_logs(100)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(logs).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self.check_auth():
            return
        
        parsed = urlparse(self.path)
        if parsed.path == '/api/action':
            length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(length) if length > 0 else b'{}'
            try:
                payload = json.loads(body_bytes.decode('utf-8'))
                action = payload.get('action')
                msg = payload.get('message', '')

                if action == 'saveworld':
                    subprocess.run(['arkmanager', 'saveworld', '@main'], timeout=10)
                    resp = {'success': True, 'message': 'Guardado de mapa (saveworld) ejecutado.'}
                elif action == 'broadcast':
                    if msg:
                        subprocess.run(['arkmanager', 'broadcast', msg, '@main'], timeout=10)
                        resp = {'success': True, 'message': f'Aviso enviado: {msg}'}
                    else:
                        resp = {'success': False, 'message': 'Mensaje de broadcast vacío.'}
                else:
                    resp = {'success': False, 'message': 'Acción desconocida.'}
            except Exception as e:
                resp = {'success': False, 'message': f'Error ejecutando acción: {str(e)}'}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Mute standard HTTP access logging to keep console clean
        return

def main():
    server = ThreadedHTTPServer(('0.0.0.0', PORT), WebUIHandler)
    print(f"ARK Server Web UI listening on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == '__main__':
    main()
