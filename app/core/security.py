import hmac
import hashlib
import base64
import time
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings

SESSION_COOKIE_NAME = "ark_session"
SESSION_DURATION_SECONDS = 60 * 60  # 60 minutos de caducidad de sesión
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 10 * 60  # 10 minutos de bloqueo
ATTEMPT_WINDOW_SECONDS = 15 * 60    # Ventana de 15 minutos para contabilizar intentos

# In-memory tracking: { ip: { "attempts": [float, ...], "locked_until": float } }
_ip_security_tracker: Dict[str, Dict[str, Any]] = {}
_MAX_TRACKED_IPS = 1000

def _purge_stale_ip_records():
    """Elimina registros de IPs sin bloqueo activo y sin intentos recientes."""
    now = time.time()
    stale = [
        ip for ip, rec in _ip_security_tracker.items()
        if now >= rec.get("locked_until", 0.0)
        and not [t for t in rec.get("attempts", []) if now - t < ATTEMPT_WINDOW_SECONDS]
    ]
    for ip in stale:
        _ip_security_tracker.pop(ip, None)

    # Acotar tamaño máximo del diccionario (orden aproximado por antigüedad de inserción)
    overflow = len(_ip_security_tracker) - _MAX_TRACKED_IPS
    if overflow > 0:
        for ip in list(_ip_security_tracker.keys())[:overflow]:
            _ip_security_tracker.pop(ip, None)

def create_session_token(username: str) -> str:
    """Genera un token de sesión criptográficamente firmado."""
    issued_at = int(time.time())
    payload = f"{username}:{issued_at}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

def verify_session_token(token: str) -> Optional[str]:
    """Verifica la validez y firma de un token de sesión, respetando caducidad de 60 min."""
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.split(":")
        if len(parts) != 3:
            return None
        username, issued_at_str, signature = parts
        issued_at = int(issued_at_str)

        if time.time() - issued_at > SESSION_DURATION_SECONDS:
            return None

        expected_sig = hmac.new(settings.secret_key.encode(), f"{username}:{issued_at_str}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_sig, signature):
            return username
    except Exception:
        return None
    return None

def verify_admin_credentials(username: str, password: str) -> bool:
    """Comprueba las credenciales del panel de control."""
    if not settings.admin_password:
        return True  # Sin contraseña requerida
    valid_user = hmac.compare_digest(username.strip(), settings.admin_user.strip())
    valid_pass = hmac.compare_digest(password.strip(), settings.admin_password.strip())
    return valid_user and valid_pass

def is_authenticated(request: Request) -> bool:
    """Verifica si la petición actual está autenticada con token válido."""
    if not settings.admin_password:
        return True
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        return False
    return verify_session_token(token) is not None

def require_auth(request: Request):
    """Dependencia de FastAPI para proteger endpoints."""
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Inicie sesión en el panel."
        )

def check_login_rate_limit(ip: str) -> Tuple[bool, int]:
    """
    Verifica si la IP tiene permitido intentar iniciar sesión.
    Retorna (is_allowed, remaining_lockout_seconds).
    """
    now = time.time()
    _purge_stale_ip_records()
    record = _ip_security_tracker.get(ip)
    if not record:
        return True, 0

    locked_until = record.get("locked_until", 0.0)
    if now < locked_until:
        remaining = int(locked_until - now)
        return False, max(remaining, 1)

    # Filtrar intentos en la ventana activa
    recent_attempts = [t for t in record.get("attempts", []) if now - t < ATTEMPT_WINDOW_SECONDS]
    record["attempts"] = recent_attempts
    return True, 0

def record_failed_login(ip: str) -> int:
    """
    Registra un intento fallido. Tras 5 intentos en la ventana, activa bloqueo de 10 minutos.
    Retorna los segundos de bloqueo si se activó, o 0 si todavía quedan intentos.
    """
    now = time.time()
    if ip not in _ip_security_tracker:
        _ip_security_tracker[ip] = {"attempts": [], "locked_until": 0.0}

    record = _ip_security_tracker[ip]
    recent = [t for t in record.get("attempts", []) if now - t < ATTEMPT_WINDOW_SECONDS]
    recent.append(now)
    record["attempts"] = recent

    if len(recent) >= MAX_LOGIN_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_DURATION_SECONDS
        record["attempts"] = []
        return LOCKOUT_DURATION_SECONDS
    return 0

def reset_failed_login(ip: str) -> None:
    """Limpia el registro de intentos fallidos de una IP tras un login exitoso."""
    _ip_security_tracker.pop(ip, None)
