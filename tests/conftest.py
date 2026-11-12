"""Fixtures compartidas para aislar cachés, rate-limiters y archivos temporales en pruebas."""

import pytest

from app.config import settings
from app.core.activity_manager import activity_manager
from app.core.process_utils import invalidate_ark_process_cache
from app.core.security import reset_api_rate_limits


@pytest.fixture(autouse=True)
def _isolate_runtime_state(tmp_path, monkeypatch):
    """Evita que las pruebas muten archivos reales de steamcmd/ark o arrastren cachés globales."""
    invalidate_ark_process_cache()
    reset_api_rate_limits()

    # Cancelar temporizador pendiente de activity_manager y aislar su archivo JSON
    with activity_manager._lock:
        if activity_manager._flush_timer is not None:
            activity_manager._flush_timer.cancel()
            activity_manager._flush_timer = None
        activity_manager._dirty = False
        monkeypatch.setattr(activity_manager, "_file", tmp_path / "activity_logs.json")
        monkeypatch.setattr(activity_manager, "_logs", [])

    monkeypatch.setattr(settings, "_config_file", tmp_path / "ark_panel_config.json")
    monkeypatch.setattr(settings, "runtime_config", dict(settings.runtime_config))

    yield

    with activity_manager._lock:
        if activity_manager._flush_timer is not None:
            activity_manager._flush_timer.cancel()
            activity_manager._flush_timer = None
        activity_manager._dirty = False
    invalidate_ark_process_cache()
    reset_api_rate_limits()

