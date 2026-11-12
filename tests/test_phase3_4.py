"""Tests de verificación para Fase 3 (Frontend/UI) y Fase 4 (Paridad con Dockraft v1.4.0)."""
import re
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_phase3_files_js_filter_and_quick_configs():
    """Verifica que files.js asigne data-name, persista currentPath y resuelva rutas LinuxServer."""
    files_js = (REPO_ROOT / "web" / "static" / "js" / "files.js").read_text(encoding="utf-8")

    # 3.1: data-name presente en renderFileList
    assert "row.setAttribute('data-name'" in files_js or 'row.setAttribute("data-name"' in files_js
    # 3.2: rutas LinuxServer y fallback CleanConfig en openDirectConfig
    assert "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini" in files_js
    assert "ShooterGame/Saved/Config/LinuxServer/Game.ini" in files_js
    assert "ShooterGame/Saved/Logs/ShooterGame.log" in files_js
    # 3.8: reutiliza window.escapeHtml y window.attrJsStr
    assert "window.escapeHtml" in files_js
    assert "window.attrJsStr" in files_js
    # 4.1: soporte de subida múltiple y drag & drop
    assert "uploadFiles(" in files_js
    assert "enqueueUploads(" in files_js
    assert "XMLHttpRequest" in files_js


def test_phase3_app_js_fixes():
    """Verifica correcciones en app.js: único sendQuickRcon, server_port, max_players y ?instance=."""
    app_js = (REPO_ROOT / "web" / "static" / "js" / "app.js").read_text(encoding="utf-8")

    # 3.3: una sola definición de sendQuickRcon y es consciente del clúster
    matches = re.findall(r"function\s+sendQuickRcon\s*\(", app_js)
    assert len(matches) == 1
    assert "/api/cluster/instances/${currentInstanceId}/command" in app_js

    # 3.4: server_port en onSwitchClusterServer
    assert "targetInst.server_port || targetInst.game_port" in app_js

    # 3.5: contador de jugadores conserva denominador / maxP
    assert "${playersCache.online.length} / ${maxP}" in app_js

    # 4.3: settings usa ?instance=
    assert "/api/settings?instance=${instParam}" in app_js

    # 4.4: gráfico incluye dataset Disco (%) y alerta de disco
    assert 'label: "Disco (%)"' in app_js
    assert "disk-alert-banner" in app_js
    assert "escapeHtml(nodeTitle)" in app_js


def test_phase3_templates_and_css_cleanup():
    """Verifica limpieza de redundancias en players.html y style.css y mejoras en files.html/metrics.html."""
    base_html = (REPO_ROOT / "web" / "templates" / "base.html").read_text(encoding="utf-8")
    players_html = (REPO_ROOT / "web" / "templates" / "tabs" / "players.html").read_text(encoding="utf-8")
    style_css = (REPO_ROOT / "web" / "static" / "css" / "style.css").read_text(encoding="utf-8")
    files_html = (REPO_ROOT / "web" / "templates" / "tabs" / "files.html").read_text(encoding="utf-8")
    metrics_html = (REPO_ROOT / "web" / "templates" / "tabs" / "metrics.html").read_text(encoding="utf-8")

    # SRI en CDN de Chart.js
    assert 'integrity="sha384-e6cc9LaIG7xZ3XD5B+jtr1NhTWPQGQdRCh6xiZ+ZFUtWCpg4ycv3Sh+SkZoopvUY"' in base_html
    assert 'crossorigin="anonymous"' in base_html

    # 3.6: players.html no duplica bloque <style>
    assert "<style>" not in players_html
    # 3.7: clases residuales de Minecraft removidas de style.css
    assert ".prop-cat-btn" not in style_css
    assert ".plugin-item-card" not in style_css

    # 4.1: files.html tiene drag & drop overlay, multiple upload y widget flotante
    assert 'id="files-drop-overlay"' in files_html
    assert 'id="upload-manager-widget"' in files_html
    assert "multiple" in files_html

    # 4.4: metrics.html tiene banner de alerta de disco y barra de disco
    assert 'id="disk-alert-banner"' in metrics_html
    assert 'id="val-disk-bar"' in metrics_html


@pytest.mark.asyncio
async def test_phase4_mods_workshop_enrichment(tmp_path, monkeypatch):
    """Verifica el enriquecimiento de metadatos de Steam Workshop y detección de actualizaciones."""
    from unittest.mock import AsyncMock, MagicMock
    from app.routers import mods as mods_router

    mods_dir = tmp_path / "ShooterGame" / "Content" / "Mods" / "731604991"
    mods_dir.mkdir(parents=True)
    mod_file = mods_dir / "mod.info"
    mod_file.write_bytes(b"x" * (2 * 1024 * 1024))
    folder_mtime = int(mods_dir.stat().st_mtime)

    steam_response_payload = {
        "response": {
            "publishedfiledetails": [
                {
                    "publishedfileid": "731604991",
                    "title": "Structures Plus (S+)",
                    "preview_url": "https://steamuserimages-a.akamaihd.net/splus.jpg",
                    "file_size": int(45.2 * 1024 * 1024),
                    "time_updated": folder_mtime + 3600,  # Más reciente en Steam -> update_available
                    "subscriptions": 1500000,
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = steam_response_payload

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post.return_value = mock_resp

    mods_router._WORKSHOP_CACHE.clear()
    monkeypatch.setattr(mods_router.settings, "ark_data_dir", tmp_path)
    monkeypatch.setattr(mods_router.settings, "runtime_config", {"mod_ids": "731604991"})

    with patch.object(mods_router.httpx, "AsyncClient", return_value=mock_client):
        resp = await mods_router.api_get_mods(enrich=True, refresh=True)
        assert resp["mods"] == ["731604991"]
        assert resp["count"] == 1
        assert resp["updates_available"] == 1
        assert "731604991" in resp["details"]
        detail = resp["details"]["731604991"]
        assert detail["title"] == "Structures Plus (S+)"
        assert detail["installed_locally"] is True
        assert detail["update_available"] is True


def test_app_version_synced_from_changelog_and_footer_only(tmp_path, monkeypatch):
    """La versión se lee automáticamente de CHANGELOG.md y solo se renderiza en el footer."""
    from fastapi.testclient import TestClient
    from app.config import get_app_version, settings
    from app.core.security import create_session_token
    from app.main import app

    assert settings.app_version == get_app_version(REPO_ROOT / "CHANGELOG.md")
    sidebar_html = (REPO_ROOT / "web" / "templates" / "components" / "sidebar.html").read_text(encoding="utf-8")
    assert "sidebar-version" not in sidebar_html
    assert "get_app_version" not in sidebar_html

    fake_changelog = tmp_path / "CHANGELOG.md"
    fake_changelog.write_text("# Changelog\n\n## [Unreleased]\n\n## [2.9.4] - 2026-12-01\n", encoding="utf-8")
    assert get_app_version(fake_changelog) == "2.9.4"

    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(settings, "admin_password", "PlainSecret123")
    client = TestClient(app)
    client.cookies.set("ark_session", create_session_token("admin"))
    res = client.get("/")
    assert res.status_code == 200
    assert '<span class="footer-ver">v2.9.4</span>' in res.text
    assert "/static/css/style.css?v=2.9.4" in res.text
    assert "/static/sw.js?v=2.9.4" in res.text
    assert "/static/js/app.js?v=2.9.4" in res.text
    assert "sidebar-version" not in res.text
