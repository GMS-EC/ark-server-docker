"""Suite ampliada (Fase 5): cobertura de lógica crítica, seguridad, rendimiento y routers FastAPI."""

import json
import sys
import time
import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.core import process_utils
from app.core.activity_manager import ActivityManager
from app.core.ark_settings_manager import ark_settings_manager
from app.core.backup_manager import BackupManager
from app.core.cluster_manager import ClusterManager, cluster_manager, _sanitize_cli_param
from app.core.metrics_manager import MetricsManager
from app.core.process_manager import ProcessManager, process_manager
from app.core.rcon_client import ArkRconClient
from app.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    reset_api_rate_limits,
    revoke_session_token,
    verify_session_token,
)
from app.core.task_scheduler import TaskScheduler


def _fake_proc(pid: int, name: str, cmdline):
    return SimpleNamespace(info={"pid": pid, "name": name, "cmdline": cmdline})


def _auth_client() -> TestClient:
    client = TestClient(app)
    token = create_session_token(settings.admin_user)
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def test_find_ark_processes_ttl_cache_filtering_and_invalidation(monkeypatch):
    """Valida filtrado de shells, caché TTL único por ventana, filtro de puerto e invalidación."""
    scans = 0
    fake_list = [
        _fake_proc(100, "bash", ["/bin/bash", "-c", "ShooterGameServer"]),
        _fake_proc(101, "python3", ["python3", "ShooterGameServer"]),
        _fake_proc(201, "ShooterGameServ", ["./ShooterGameServer", "TheIsland?Port=7777?QueryPort=27015"]),
        _fake_proc(202, "ShooterGameServer", ["./ShooterGameServer", "ScorchedEarth_P?Port=7779"]),
    ]

    def fake_iter(attrs=None):
        nonlocal scans
        scans += 1
        return list(fake_list)

    monkeypatch.setattr(process_utils.psutil, "process_iter", fake_iter)
    process_utils.invalidate_ark_process_cache()

    all_procs = process_utils.find_ark_processes(ttl=10.0)
    assert scans == 1
    assert [p.pid for p in all_procs] == [201, 202]

    # Llamadas posteriores dentro del TTL reutilizan la caché sin volver a iterar procesos
    main_procs = process_utils.find_ark_processes(port=7777, ttl=10.0)
    cluster_procs = process_utils.find_ark_processes(port=7779, ttl=10.0)
    assert scans == 1
    assert [p.pid for p in main_procs] == [201]
    assert [p.pid for p in cluster_procs] == [202]

    process_utils.invalidate_ark_process_cache()
    process_utils.find_ark_processes(ttl=10.0)
    assert scans == 2


@pytest.mark.asyncio
async def test_process_manager_status_pid_logs_and_simulation(tmp_path, monkeypatch):
    """Cubre detección de estado/PID, buffer de logs con límite y arranque/parada en simulación."""
    pm = ProcessManager()
    monkeypatch.setattr(settings, "server_port", 7777)

    # Sin procesos ni binarios
    monkeypatch.setattr(process_utils.psutil, "process_iter", lambda attrs=None: [])
    process_utils.invalidate_ark_process_cache()
    assert pm.get_status() == "OFFLINE"
    assert pm.get_server_pid() is None

    # Proceso externo detectado en el puerto principal
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs=None: [_fake_proc(4321, "ShooterGameServer", ["./ShooterGameServer", "TheIsland?Port=7777"])],
    )
    process_utils.invalidate_ark_process_cache()
    assert pm.get_server_pid() == 4321
    assert pm.get_status() == "RUNNING"

    # Buffer acotado (maxlen=1000)
    for i in range(1050):
        await pm.broadcast_log(f"line-{i}")
    assert len(pm.log_buffer) == 1000
    assert pm.log_buffer[-1] == "line-1049"

    # Arranque y parada en modo simulación (mocking subprocess_exec para no dormir 600s)
    pm2 = ProcessManager()
    fake_subproc = MagicMock()
    fake_subproc.pid = 9999
    fake_subproc.returncode = None
    fake_subproc.stdout = None
    fake_subproc.terminate = MagicMock()
    fake_subproc.kill = MagicMock()
    fake_subproc.wait = AsyncMock(return_value=0)

    monkeypatch.setattr("app.core.process_manager.shutil.which", lambda _: None)
    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(pm2, "_cancel_log_file_task", lambda: None)
    monkeypatch.setattr(pm2, "_stream_output", AsyncMock())
    monkeypatch.setattr(pm2, "_watch_server_readiness", AsyncMock())
    monkeypatch.setattr(pm2.rcon, "save_world", AsyncMock(return_value="Saved"))
    monkeypatch.setattr(pm2.rcon, "disconnect", AsyncMock())
    monkeypatch.setattr(process_utils.psutil, "process_iter", lambda attrs=None: [])
    process_utils.invalidate_ark_process_cache()

    with patch("app.core.process_manager.asyncio.create_subprocess_exec", AsyncMock(return_value=fake_subproc)) as mock_exec:
        started = await pm2.start_server()
        assert started is True
        assert pm2._is_simulation is True
        assert pm2.status == "STARTING"
        # Simulación usa sys.executable
        assert mock_exec.call_args[0][0] == sys.executable

        fake_subproc.returncode = 0
        stopped = await pm2.stop_server(grace_seconds=1)
        assert stopped is True
        assert pm2.status == "OFFLINE"


def test_cluster_manager_crud_ports_sanitization_and_sync_rates(tmp_path, monkeypatch):
    """Valida ciclo CRUD, sugerencia y conflicto de puertos, cache PS y sync_rates sin ciclos."""
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(settings, "backups_dir", tmp_path / "backups")

    cm = ClusterManager()
    assert "main" in cm.list_instance_ids()

    suggested = cm.suggest_next_ports()
    assert suggested["server_port"] >= 7777
    assert suggested["query_port"] >= 27015
    assert suggested["rcon_port"] >= 27020

    res = cm.create_instance({
        "name": "Scorched Node!",
        "map": "ScorchedEarth_P;rm",
        "server_port": 7779,
        "query_port": 27016,
        "rcon_port": 27021,
        "max_players": 16,
    })
    assert res["success"] is True
    inst = res["instance"]
    inst_id = inst["id"]
    assert ";" not in inst["map"]
    sanitized_cmd = _sanitize_cli_param("Map;rm -rf /")
    assert ";" not in sanitized_cmd and "-" not in sanitized_cmd
    assert sanitized_cmd == "Maprm rf /"

    # Conflicto de puerto rechazado
    dup = cm.create_instance({
        "name": "Otra",
        "map": "Ragnarok",
        "server_port": 7779,
        "query_port": 27029,
        "rcon_port": 27039,
    })
    assert dup["success"] is False

    # Actualización de instancia
    upd = cm.update_instance(inst_id, {"max_players": 32})
    assert upd["success"] is True
    assert upd["instance"]["max_players"] == 32

    # _refresh_ps_cache usa find_ark_processes
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs=None: [_fake_proc(5555, "ShooterGameServer", ["./ShooterGameServer", "ScorchedEarth_P?Port=7779"])],
    )
    process_utils.invalidate_ark_process_cache()
    ports_map = cm._refresh_ps_cache(ttl=0)
    assert ports_map[7779] == 5555

    # sync_rates_to_all vive en ark_settings_manager (sin import circular con cluster_manager)
    monkeypatch.setattr(cluster_manager, "_instances", cm._instances)
    monkeypatch.setattr(ark_settings_manager, "config_dir", tmp_path / "ShooterGame" / "Saved" / "Config" / "LinuxServer")
    monkeypatch.setattr(ark_settings_manager, "gus_file", ark_settings_manager.config_dir / "GameUserSettings.ini")
    monkeypatch.setattr(ark_settings_manager, "game_file", ark_settings_manager.config_dir / "Game.ini")
    sync_res = ark_settings_manager.sync_rates_to_all({"xp": "3.0", "taming": "4.0"})
    assert sync_res["success"] is True
    assert sync_res["synced_nodes"] == 2
    assert "3.0" in ark_settings_manager.gus_file.read_text(encoding="utf-8")

    # Protección al borrar principal vs borrado de secundaria
    assert cm.delete_instance("main")["success"] is False
    monkeypatch.setattr(process_utils.psutil, "process_iter", lambda attrs=None: [])
    process_utils.invalidate_ark_process_cache()
    assert cm.delete_instance(inst_id)["success"] is True
    assert inst_id not in cm.list_instance_ids()


@pytest.mark.asyncio
async def test_task_scheduler_power_window_and_player_postponement(monkeypatch):
    """Verifica ventana nocturna de horarios, autoencendido y posposición si hay jugadores."""
    ts = TaskScheduler()
    monkeypatch.setattr(settings, "runtime_config", {
        "schedule_enabled": True,
        "schedule_start": "22:00",
        "schedule_stop": "02:00",
        "schedule_warn_mins": 10,
    })

    start_calls = 0
    stop_calls = 0

    async def fake_start():
        nonlocal start_calls
        start_calls += 1
        return True

    async def fake_stop():
        nonlocal stop_calls
        stop_calls += 1
        return True

    monkeypatch.setattr("app.core.task_scheduler.process_manager.is_installed", lambda: True)
    monkeypatch.setattr("app.core.task_scheduler.process_manager.start_server", fake_start)
    monkeypatch.setattr("app.core.task_scheduler.process_manager.stop_server", fake_stop)
    monkeypatch.setattr("app.core.task_scheduler.process_manager.broadcast_log", AsyncMock())
    monkeypatch.setattr("app.core.task_scheduler.webhook_manager.notify_starting", AsyncMock())
    monkeypatch.setattr("app.core.task_scheduler.webhook_manager.send_discord_embed", AsyncMock())

    # 1. Dentro de horario nocturno (23:30) con servidor apagado -> autoencendido
    monkeypatch.setattr("app.core.task_scheduler.process_manager.get_status", lambda: "OFFLINE")
    await ts._check_power_schedule(now_dt=datetime(2026, 11, 12, 23, 30))
    assert start_calls == 1
    assert ts.last_power_event == "autoencendido (22:00)"

    # 2. Fuera de horario (02:05) con servidor encendido y 1 jugador -> pospone apagado
    monkeypatch.setattr("app.core.task_scheduler.process_manager.get_status", lambda: "RUNNING")
    monkeypatch.setattr("app.core.task_scheduler.process_manager.rcon.list_players", AsyncMock(return_value=[{"name": "Bob"}]))
    await ts._check_power_schedule(now_dt=datetime(2026, 11, 13, 2, 5))
    assert stop_calls == 0
    assert ts.last_power_event == "pospuesto (1 online)"

    # 3. 0 jugadores -> ejecuta apagado
    monkeypatch.setattr("app.core.task_scheduler.process_manager.rcon.list_players", AsyncMock(return_value=[]))
    await ts._check_power_schedule(now_dt=datetime(2026, 11, 13, 2, 6))
    assert stop_calls == 1


@pytest.mark.asyncio
async def test_backup_manager_create_rotate_and_restore_cycle(tmp_path, monkeypatch):
    """Prueba ciclo completo de creación, rotación máxima y restauración con copia de seguridad previa."""
    ark_dir = tmp_path / "ark"
    backups_dir = tmp_path / "backups"
    saved_arks = ark_dir / "ShooterGame" / "Saved" / "SavedArks"
    saved_cfg = ark_dir / "ShooterGame" / "Saved" / "Config" / "LinuxServer"
    saved_arks.mkdir(parents=True)
    saved_cfg.mkdir(parents=True)

    map_file = saved_arks / "TheIsland.ark"
    gus_file = saved_cfg / "GameUserSettings.ini"
    map_file.write_bytes(b"ORIGINAL_WORLD_DATA")
    gus_file.write_text("[ServerSettings]\nSessionName=Original\n", encoding="utf-8")

    monkeypatch.setattr(settings, "ark_data_dir", ark_dir)
    monkeypatch.setattr(settings, "backups_dir", backups_dir)
    monkeypatch.setattr(settings, "world", "TheIsland")
    monkeypatch.setattr(settings, "runtime_config", {"backup_max_count": 2})
    monkeypatch.setattr("app.core.backup_manager.process_manager.get_status", lambda: "OFFLINE")
    monkeypatch.setattr("app.core.backup_manager.process_manager.broadcast_log", AsyncMock())
    monkeypatch.setattr("app.core.backup_manager.webhook_manager.notify_backup", AsyncMock())
    monkeypatch.setattr("app.core.backup_manager.webhook_manager.notify_restore", AsyncMock())

    bm = BackupManager()
    res1 = await bm.create_backup("manual_v1", notify=False)
    assert res1["success"] is True
    assert (backups_dir / res1["filename"]).exists()

    # Crear 2 backups adicionales y verificar rotación a 2 archivos
    await asyncio.sleep(0.02)
    await bm.create_backup("manual_v2", notify=False)
    await asyncio.sleep(0.02)
    await bm.create_backup("manual_v3", notify=False)
    listed = bm.list_backups()
    assert len(listed) == 2

    target_backup = listed[-1]["filename"]  # el más antiguo de los 2 conservados

    # Mutar el archivo antes de restaurar
    map_file.write_bytes(b"CORRUPTED_WORLD_DATA")

    # Ampliar retención para observar pre_restore + backups conservados
    monkeypatch.setattr(settings, "runtime_config", {"backup_max_count": 5})
    restored = await bm.restore_backup(target_backup, create_safety_backup=True)
    assert restored["success"] is True
    assert map_file.read_bytes() == b"ORIGINAL_WORLD_DATA"
    assert any("pre_restore_" in b["filename"] for b in bm.list_backups())


def test_activity_manager_debounced_save_and_flush(tmp_path, monkeypatch):
    """Comprueba que log() agrupa escrituras en RAM y las consolida al ejecutar flush()."""
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    am = ActivityManager(debounce_seconds=5.0)
    try:
        for idx in range(5):
            am.log("Consola", f"Comando #{idx}")
        # Aún dentro de la ventana de debounce, el archivo no ha sido reescrito 5 veces
        assert not (tmp_path / "activity_logs.json").exists()

        am.flush()
        assert (tmp_path / "activity_logs.json").exists()
        saved = json.loads((tmp_path / "activity_logs.json").read_text(encoding="utf-8"))
        assert len(saved) == 5
        assert saved[0]["message"] == "Comando #4"
    finally:
        am.flush()


def test_metrics_manager_primes_cpu_and_reuses_process_cache(monkeypatch):
    """Verifica pre-inicialización de psutil.cpu_percent(interval=None) en MetricsManager."""
    cpu_calls = []

    def fake_cpu_percent(interval=None):
        cpu_calls.append(interval)
        return 12.5

    monkeypatch.setattr("app.core.metrics_manager.psutil.cpu_percent", fake_cpu_percent)
    mm = MetricsManager(max_history=10)
    assert cpu_calls == [None]

    monkeypatch.setattr(process_utils.psutil, "process_iter", lambda attrs=None: [])
    process_utils.invalidate_ark_process_cache()
    metrics = mm._collect_metrics()
    assert metrics["host_cpu_percent"] == 12.5


@pytest.mark.asyncio
async def test_rcon_client_strips_control_chars_preserving_chat():
    """Filtra NUL y saltos de línea en RCON sin romper caracteres válidos de chat o parámetros."""
    client = ArkRconClient("127.0.0.1", 27020, "secret")
    sent_payloads = []

    fake_writer = MagicMock()
    fake_writer.is_closing.return_value = False
    fake_writer.write = lambda data: sent_payloads.append(data)
    fake_writer.drain = AsyncMock()

    client.writer = fake_writer
    client.reader = MagicMock()
    client._authenticated = True

    monkeypatch_packet_args = []
    orig_build = client._build_packet

    def spy_build(req_id: int, ptype: int, body: str) -> bytes:
        monkeypatch_packet_args.append(body)
        return orig_build(req_id, ptype, body)

    client._build_packet = spy_build
    client._read_packet = AsyncMock(return_value=(1, 0, "OK"))

    resp = await client.send_command("ServerChat Hola; 1 & 2 | test\x00\r\nQuit")
    assert resp == "OK"
    assert len(monkeypatch_packet_args) == 1
    cleaned = monkeypatch_packet_args[0]
    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert "; 1 & 2 |" in cleaned


@pytest.mark.asyncio
async def test_rcon_error_log_redacts_command_arguments(caplog):
    """Verifica que un fallo RCON no exponga contraseñas ni argumentos sensibles en los logs."""
    client = ArkRconClient("127.0.0.1", 27020, "secret")
    fake_writer = MagicMock()
    fake_writer.is_closing.return_value = False
    fake_writer.write.side_effect = OSError("socket reset")
    client.writer = fake_writer
    client.reader = MagicMock()
    client._authenticated = True

    with caplog.at_level("ERROR", logger="arkserver.rcon"):
        res = await client.send_command("EnableCheats SuperSecretPass123")

    assert "Error ejecutando comando" in res
    assert "SuperSecretPass123" not in caplog.text
    assert "EnableCheats ***" in caplog.text


def test_session_tokens_unique_nonce_and_api_rate_limiting(monkeypatch):
    """Garantiza unicidad de tokens por login dentro del mismo segundo y límite 429 en RCON."""
    t1 = create_session_token("admin")
    t2 = create_session_token("admin")
    assert t1 != t2
    revoke_session_token(t1)
    assert verify_session_token(t1) is None
    assert verify_session_token(t2) == "admin"

    reset_api_rate_limits()
    monkeypatch.setattr(process_manager, "send_command", AsyncMock(return_value="Executed"))
    client = _auth_client()

    # Límite de /api/server/command es 30 peticiones / 60s
    for _ in range(30):
        res = client.post("/api/server/command", json={"command": "ListPlayers"})
        assert res.status_code == 200

    blocked = client.post("/api/server/command", json={"command": "ListPlayers"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_routers_integration_endpoints(tmp_path, monkeypatch):
    """Pruebas de integración TestClient contra settings, mods, cluster, tasks, webhooks, backups y server."""
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(settings, "backups_dir", tmp_path / "backups")
    monkeypatch.setattr(settings, "cluster_dir", tmp_path / "clusters")
    monkeypatch.setattr(ark_settings_manager, "config_dir", tmp_path / "ShooterGame" / "Saved" / "Config" / "LinuxServer")
    monkeypatch.setattr(ark_settings_manager, "gus_file", ark_settings_manager.config_dir / "GameUserSettings.ini")
    monkeypatch.setattr(ark_settings_manager, "game_file", ark_settings_manager.config_dir / "Game.ini")
    monkeypatch.setattr(cluster_manager, "_config_file", tmp_path / "ark_cluster_instances.json")
    monkeypatch.setattr(cluster_manager, "_instances", {
        "main": {
            "id": "main",
            "name": "Principal (The Island)",
            "map": "TheIsland",
            "session_name": "ARK Server",
            "server_port": 7777,
            "query_port": 27015,
            "rcon_port": 27020,
            "alt_save_dir": "TheIsland",
            "is_primary": True,
            "enabled": True,
        }
    })

    # Sin autenticación -> 401
    unauth = TestClient(app)
    assert unauth.get("/api/settings?instance=main").status_code == 401

    client = _auth_client()

    # Settings GET & POST
    assert client.post("/api/settings?instance=main", json={"multipliers": {"xp": "2.5"}}).status_code == 200
    s_data = client.get("/api/settings?instance=main").json()
    assert str(s_data["multipliers"]["xp"]) == "2.5"

    # Mods GET & POST
    assert client.post("/api/mods", json={"mod_ids": "731604991"}).status_code == 200
    m_data = client.get("/api/mods?enrich=false").json()
    assert m_data["mods"] == ["731604991"]

    # Cluster CRUD & sync_rates
    c_create = client.post("/api/cluster/instances", json={"name": "RagnarokTest", "map": "Ragnarok"})
    assert c_create.status_code == 200
    created_id = c_create.json()["instance"]["id"]
    c_sync = client.post("/api/cluster/sync_rates", json={"rates": {"xp": "4.0"}})
    assert c_sync.status_code == 200
    assert c_sync.json()["synced_nodes"] >= 2
    assert client.delete(f"/api/cluster/instances/{created_id}").json()["success"] is True

    # Tasks GET & POST
    assert client.post("/api/tasks/config", json={"auto_backup_enabled": True}).status_code == 200
    assert client.get("/api/tasks/status").status_code == 200

    # Webhooks GET & POST (rechaza localhost por SSRF con HTTP 400, acepta URL pública Discord)
    bad_wh = client.post("/api/webhooks", json={"url": "http://127.0.0.1:8080/hook"})
    assert bad_wh.status_code == 400
    ok_wh = client.post("/api/webhooks", json={"url": "https://discord.com/api/webhooks/123/abc", "language": "es"})
    assert ok_wh.json()["success"] is True
    assert client.get("/api/webhooks").json()["has_url"] is True

    # Backups GET & POST (con backup_manager dirigido a tmp_path)
    from app.routers import backups as backups_router
    monkeypatch.setattr(backups_router.backup_manager, "backup_dir", tmp_path / "backups")
    monkeypatch.setattr(backups_router.backup_manager, "saved_dir", tmp_path / "ShooterGame" / "Saved")
    (tmp_path / "ShooterGame" / "Saved" / "SavedArks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ShooterGame" / "Saved" / "SavedArks" / "TheIsland.ark").write_bytes(b"ARK_SAVE")
    monkeypatch.setattr("app.core.backup_manager.process_manager.get_status", lambda: "OFFLINE")
    b_create = client.post("/api/backups/create", json={"name": "router_test"})
    assert b_create.status_code == 200
    assert b_create.json()["success"] is True
    assert len(client.get("/api/backups").json()["backups"]) >= 1

    # Server command & broadcast
    monkeypatch.setattr(process_manager, "send_command", AsyncMock(return_value="Command OK"))
    monkeypatch.setattr(process_manager.rcon, "broadcast", AsyncMock(return_value="Broadcast OK"))
    assert client.post("/api/server/command", json={"command": "SaveWorld"}).json()["response"] == "Command OK"
    assert client.post("/api/server/broadcast", json={"message": "Reiniciando en 5m"}).json()["success"] is True
