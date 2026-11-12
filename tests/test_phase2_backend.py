from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.security import create_session_token, SESSION_COOKIE_NAME
from app.core.fs_utils import atomic_write_json, get_dir_size_cached, invalidate_dir_size_cache
from app.core.ark_settings_manager import ark_settings_manager
from app.core.task_scheduler import task_scheduler


def _auth_client() -> TestClient:
    client = TestClient(app)
    token = create_session_token(settings.admin_user)
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def test_modular_routers_mounted_and_responding(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(settings, "_config_file", tmp_path / "ark_panel_config.json")
    monkeypatch.setattr(settings, "runtime_config", dict(settings.runtime_config))
    monkeypatch.setattr(ark_settings_manager, "config_dir", tmp_path / "ShooterGame" / "Saved" / "Config" / "LinuxServer")
    monkeypatch.setattr(ark_settings_manager, "gus_file", ark_settings_manager.config_dir / "GameUserSettings.ini")
    monkeypatch.setattr(ark_settings_manager, "game_file", ark_settings_manager.config_dir / "Game.ini")

    client = _auth_client()

    # Healthcheck
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # Settings router (with instance parameter support)
    res_settings = client.get("/api/settings?instance=main")
    assert res_settings.status_code == 200
    assert "server" in res_settings.json()
    assert res_settings.json()["instance_id"] == "main"

    # Tasks router (check auto_dino_wipe_enabled key fixed)
    res_tasks = client.get("/api/tasks/status")
    assert res_tasks.status_code == 200
    t_cfg = res_tasks.json()["config"]
    assert "auto_dino_wipe_enabled" in t_cfg
    assert "dino_wipe_Enabled" not in t_cfg

    # Webhooks router
    res_wh = client.get("/api/webhooks")
    assert res_wh.status_code == 200
    assert "events" in res_wh.json()

    # Metrics endpoint (check disk_history & disk_alert_level included)
    res_metrics = client.get("/api/metrics")
    assert res_metrics.status_code == 200
    m_json = res_metrics.json()
    assert "current" in m_json
    assert "disk_alert_level" in m_json["current"]
    assert "disk_history" in m_json


def test_dir_size_ttl_cache_and_invalidation(tmp_path):
    f1 = tmp_path / "world.ark"
    f1.write_bytes(b"x" * 2048)

    invalidate_dir_size_cache(tmp_path)
    size1 = get_dir_size_cached(tmp_path, ttl_seconds=60.0)
    assert size1 == 2048

    # Atomic write invalidates cache automatically
    atomic_write_json(tmp_path / "extra.json", {"hello": "world"})
    size2 = get_dir_size_cached(tmp_path, ttl_seconds=60.0)
    assert size2 > 2048


def test_ark_settings_manager_precompiled_regex_read_write(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(settings, "_config_file", tmp_path / "ark_panel_config.json")
    monkeypatch.setattr(settings, "runtime_config", dict(settings.runtime_config))
    monkeypatch.setattr(ark_settings_manager, "config_dir", tmp_path / "ShooterGame" / "Saved" / "Config" / "LinuxServer")
    monkeypatch.setattr(ark_settings_manager, "gus_file", ark_settings_manager.config_dir / "GameUserSettings.ini")
    monkeypatch.setattr(ark_settings_manager, "game_file", ark_settings_manager.config_dir / "Game.ini")

    ok = ark_settings_manager.save_settings({
        "server": {"session_name": "TestServerARK", "max_players": 42},
        "multipliers": {"xp": "3.5", "taming": "5.0"},
        "rules": {"pve_mode": True}
    })
    assert ok is True

    loaded = ark_settings_manager.get_all_settings()
    assert loaded["server"]["session_name"] == "TestServerARK"
    assert str(loaded["server"]["max_players"]) == "42"
    assert loaded["multipliers"]["xp"] == "3.5"
    assert loaded["multipliers"]["taming"] == "5.0"
    assert loaded["rules"]["pve_mode"] is True
