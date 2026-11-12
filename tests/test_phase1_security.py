import io
import tarfile
import zipfile
import pytest
from pathlib import Path
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.core.security import (
    create_session_token,
    verify_session_token,
    revoke_session_token,
    verify_admin_credentials,
    is_auth_bypassed,
    check_login_rate_limit,
    record_failed_login,
    reset_failed_login,
)
from app.core.file_manager import FileManager, PROTECTED_FILES
from app.core.backup_manager import BackupManager
from app.core.player_manager import PlayerManager
from app.core.process_manager import process_manager
from app.core.rcon_client import sanitize_steam_id
from app.core.webhook_manager import is_safe_webhook_url, mask_webhook_url, SECRET_MASK
from app.core.cluster_manager import _sanitize_cli_param


def test_session_token_creation_and_revocation():
    token = create_session_token("admin")
    assert verify_session_token(token) == "admin"
    revoke_session_token(token)
    assert verify_session_token(token) is None


def test_verify_admin_credentials_constant_time(monkeypatch):
    monkeypatch.setattr(settings, "admin_user", "arkadmin")
    monkeypatch.setattr(settings, "admin_password", "PlainSecret123")
    assert verify_admin_credentials("arkadmin", "PlainSecret123") is True
    assert verify_admin_credentials("arkadmin", "WrongPass") is False
    assert verify_admin_credentials("wronguser", "PlainSecret123") is False
    assert verify_admin_credentials("wronguser", "WrongPass") is False


def test_login_rate_limiter():
    ip = "198.51.100.42"
    reset_failed_login(ip)
    allowed, rem = check_login_rate_limit(ip)
    assert allowed is True and rem == 0

    for _ in range(4):
        assert record_failed_login(ip) == 0
    lockout = record_failed_login(ip)
    assert lockout > 0
    allowed, rem = check_login_rate_limit(ip)
    assert allowed is False and rem > 0
    reset_failed_login(ip)


def test_protected_files_blocked_across_all_file_operations(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    fm = FileManager()
    fm.base_dir = tmp_path

    for pname in PROTECTED_FILES:
        (tmp_path / pname).write_text("{}", encoding="utf-8")

        with pytest.raises(HTTPException) as exc:
            fm.read_file(pname)
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            fm.write_file(pname, "hacked")
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            fm.delete_item(pname)
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            fm.rename_item(pname, "exposed.txt")
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            fm.duplicate_item(pname)
        assert exc.value.status_code == 403

        with pytest.raises(HTTPException) as exc:
            fm.compress_item(pname)
        assert exc.value.status_code == 403

    # Listing root directory must hide protected files
    listing = fm.list_directory("")
    listed_names = {item["name"] for item in listing["items"]}
    assert listed_names.isdisjoint(PROTECTED_FILES)


def test_zip_slip_and_symlink_blocked_in_file_manager(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    fm = FileManager()
    fm.base_dir = tmp_path

    # 1. ZipSlip
    zip_slip = tmp_path / "slip.zip"
    with zipfile.ZipFile(zip_slip, "w") as zf:
        zf.writestr("../../outside.txt", "evil")

    with pytest.raises(HTTPException) as exc:
        fm.extract_zip("slip.zip", "")
    assert exc.value.status_code == 400

    # 2. Protected file overwrite inside zip
    zip_prot = tmp_path / "prot.zip"
    with zipfile.ZipFile(zip_prot, "w") as zf:
        zf.writestr("ark_panel_config.json", '{"hacked": true}')

    with pytest.raises(HTTPException) as exc:
        fm.extract_zip("prot.zip", "")
    assert exc.value.status_code == 403


def test_tar_slip_and_symlink_blocked_in_backup_manager(tmp_path):
    # 1. TarSlip
    tar_slip = tmp_path / "slip.tar.gz"
    with tarfile.open(tar_slip, "w:gz") as tar:
        info = tarfile.TarInfo(name="../../evil.txt")
        data = b"evil"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    dest = tmp_path / "dest"
    dest.mkdir()
    with tarfile.open(tar_slip, "r:gz") as tar:
        with pytest.raises(ValueError, match="TarSlip"):
            BackupManager._safe_extract_tar(tar, dest)

    # 2. Symlink in tar
    tar_sym = tmp_path / "sym.tar.gz"
    with tarfile.open(tar_sym, "w:gz") as tar:
        info = tarfile.TarInfo(name="Saved/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)

    with tarfile.open(tar_sym, "r:gz") as tar:
        with pytest.raises(ValueError, match="enlaces"):
            BackupManager._safe_extract_tar(tar, dest)


def test_webhook_ssrf_and_masking():
    assert is_safe_webhook_url("http://127.0.0.1:8080/api") is False
    assert is_safe_webhook_url("http://localhost/admin") is False
    assert is_safe_webhook_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_webhook_url("ftp://discord.com/api/webhooks/123/abc") is False

    masked = mask_webhook_url("https://discord.com/api/webhooks/123456789/secretTokenXYZ")
    assert SECRET_MASK in masked
    assert "secretTokenXYZ" not in masked


def test_cluster_parameter_sanitization():
    raw = "TheIsland?ServerAdminPassword=hacked\n-customflag"
    cleaned = _sanitize_cli_param(raw, allow_dash=False)
    assert "?" not in cleaned
    assert "\n" not in cleaned
    assert not cleaned.startswith("-")


def test_empty_panel_password_is_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")
    monkeypatch.delenv("ALLOW_EMPTY_PASSWORD", raising=False)

    assert is_auth_bypassed() is False
    assert verify_admin_credentials("admin", "") is False

    client = TestClient(app)
    assert client.get("/api/status").status_code == 401
    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert "PANEL_PASSWORD" in login_page.text
    assert "Content-Security-Policy" in login_page.headers
    assert "object-src 'none'" in login_page.headers["Content-Security-Policy"]

    with pytest.raises(Exception):
        with client.websocket_connect("/ws/console"):
            pass

    monkeypatch.setenv("ALLOW_EMPTY_PASSWORD", "true")
    assert is_auth_bypassed() is True
    assert verify_admin_credentials("admin", "") is True


@pytest.mark.asyncio
async def test_player_rcon_sanitization_and_router_validation(monkeypatch):
    assert sanitize_steam_id("76561198000000001") == "76561198000000001"
    for bad_id in ('76561198000" Broadcast "hack', "abc123", "", "123"):
        with pytest.raises(ValueError):
            sanitize_steam_id(bad_id)

    sent = []

    async def fake_send(cmd: str) -> str:
        sent.append(cmd)
        return "OK"

    monkeypatch.setattr(process_manager.rcon, "send_command", fake_send)
    pm = PlayerManager()
    await pm.message_player("76561198000000001", 'Hola "amigo"\r\n')
    assert sent == ['ServerChatToPlayer "76561198000000001" Hola \\"amigo\\"']

    monkeypatch.setattr(settings, "admin_password", "PlainSecret123")
    token = create_session_token("admin")
    client = TestClient(app)
    client.cookies.set("ark_session", token)
    bad_kick = client.post("/api/players/kick", json={"steam_id": '123" SaveWorld'})
    assert bad_kick.status_code == 422


def test_file_manager_does_not_leak_internal_exception_details(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ark_data_dir", tmp_path)
    fm = FileManager()
    fm.base_dir = tmp_path
    sample = tmp_path / "secret_test.ini"
    sample.write_text("key=val", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("/internal/sensitive/path PermissionError")

    monkeypatch.setattr("builtins.open", boom)
    with pytest.raises(HTTPException) as exc:
        fm.read_file("secret_test.ini")
    assert exc.value.status_code == 500
    assert "/internal/sensitive/path" not in exc.value.detail
    assert exc.value.detail == "Error interno al leer el archivo."
