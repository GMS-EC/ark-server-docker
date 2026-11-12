import os
import hmac
import hashlib
import base64
import secrets
import time
from typing import Optional, Dict, Any, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings

try:
    import bcrypt as _bcrypt  # type: ignore
except ImportError:
    _bcrypt = None

SESSION_COOKIE_NAME = "ark_session"
SESSION_DURATION_SECONDS = 60 * 60  # 60 minutos de caducidad de sesión
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 10 * 60  # 10 minutos de bloqueo
ATTEMPT_WINDOW_SECONDS = 15 * 60    # Ventana de 15 minutos para contabilizar intentos

# In-memory tracking: { ip: { "attempts": [float, ...], "locked_until": float } }
_ip_security_tracker: Dict[str, Dict[str, Any]] = {}
_MAX_TRACKED_IPS = 10000

# Revoked tokens cache: { token_sha256: expires_at_timestamp }
_revoked_tokens: Dict[str, float] = {}

_DUMMY_PBKDF2_SALT = b"ark-panel-constant-time-salt"


def _purge_stale_ip_records() -> None:
    """Elimina registros de IPs sin bloqueo activo y sin intentos recientes."""
    now = time.time()
    stale = [
        ip for ip, rec in _ip_security_tracker.items()
        if now >= rec.get("locked_until", 0.0)
        and not [t for t in rec.get("attempts", []) if now - t < ATTEMPT_WINDOW_SECONDS]
    ]
    for ip in stale:
        _ip_security_tracker.pop(ip, None)

    overflow = len(_ip_security_tracker) - _MAX_TRACKED_IPS
    if overflow > 0:
        for ip in list(_ip_security_tracker.keys())[:overflow]:
            _ip_security_tracker.pop(ip, None)


def _purge_revoked_tokens() -> None:
    now = time.time()
    expired = [th for th, exp in _revoked_tokens.items() if now >= exp]
    for th in expired:
        _revoked_tokens.pop(th, None)


def create_session_token(username: str) -> str:
    """Genera un token de sesión criptográficamente firmado con nonce único."""
    issued_at = int(time.time())
    nonce = secrets.token_hex(8)
    payload = f"{username}:{issued_at}:{nonce}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def revoke_session_token(token: Optional[str]) -> None:
    """Revoca un token de sesión activo antes de su expiración natural."""
    if not token:
        return
    _purge_revoked_tokens()
    token_hash = hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()
    _revoked_tokens[token_hash] = time.time() + SESSION_DURATION_SECONDS + 60


def verify_session_token(token: str) -> Optional[str]:
    """Verifica la validez y firma de un token de sesión, respetando caducidad y revocación."""
    if not token:
        return None
    _purge_revoked_tokens()
    token_hash = hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()
    if token_hash in _revoked_tokens:
        return None

    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.split(":")
        if len(parts) == 3:
            username, issued_at_str, signature = parts
            signed_payload = f"{username}:{issued_at_str}"
        elif len(parts) == 4:
            username, issued_at_str, nonce, signature = parts
            signed_payload = f"{username}:{issued_at_str}:{nonce}"
        else:
            return None
        issued_at = int(issued_at_str)

        if time.time() - issued_at > SESSION_DURATION_SECONDS:
            return None

        expected_sig = hmac.new(settings.secret_key.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_sig, signature):
            return username
    except Exception:
        return None
    return None


def is_auth_bypassed() -> bool:
    """Solo permite acceso sin autenticación si PANEL_PASSWORD está vacío y ALLOW_EMPTY_PASSWORD=true."""
    if (settings.admin_password or "").strip():
        return False
    return os.getenv("ALLOW_EMPTY_PASSWORD", "").strip().lower() in ("1", "true", "yes")


def verify_admin_credentials(username: str, password: str) -> bool:
    """Comprueba las credenciales del panel en tiempo constante sin cortocircuito por usuario inválido."""
    if not (settings.admin_password or "").strip():
        return is_auth_bypassed()

    valid_user = hmac.compare_digest((username or "").strip().encode("utf-8"), settings.admin_user.strip().encode("utf-8"))
    configured_pw = settings.admin_password.strip()
    candidate_pw = (password or "").strip()

    if _bcrypt is not None and configured_pw.startswith(("$2b$", "$2a$", "$2y$")):
        try:
            valid_pass = _bcrypt.checkpw(candidate_pw.encode("utf-8"), configured_pw.encode("utf-8"))
        except Exception:
            valid_pass = False
        return bool(valid_user and valid_pass)

    # Derivar digest PBKDF2-HMAC-SHA256 en ambos lados para mantener tiempo constante
    cand_digest = hashlib.pbkdf2_hmac("sha256", candidate_pw.encode("utf-8"), _DUMMY_PBKDF2_SALT, 100_000)
    conf_digest = hashlib.pbkdf2_hmac("sha256", configured_pw.encode("utf-8"), _DUMMY_PBKDF2_SALT, 100_000)
    valid_pass = hmac.compare_digest(cand_digest, conf_digest)
    return bool(valid_user and valid_pass)


def is_request_secure(request: Request) -> bool:
    """Determina si la cookie debe llevar el atributo Secure según configuración o cabeceras de proxy."""
    env_flag = os.getenv("COOKIE_SECURE", "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return True
    if env_flag in ("0", "false", "no"):
        return False
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return "https" in forwarded_proto.lower()


def is_authenticated(request: Request) -> bool:
    """Verifica si la petición actual está autenticada con token válido."""
    if not (settings.admin_password or "").strip():
        return is_auth_bypassed()
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

    recent_attempts = [t for t in record.get("attempts", []) if now - t < ATTEMPT_WINDOW_SECONDS]
    record["attempts"] = recent_attempts
    return True, 0


def record_failed_login(ip: str) -> int:
    """
    Registra un intento fallido. Tras 5 intentos en la ventana, activa bloqueo de 10 minutos.
    Retorna los segundos de bloqueo si se activó, o 0 si todavía quedan intentos.
    """
    now = time.time()
    _purge_stale_ip_records()
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


# In-memory API rate limiter por endpoint/cliente: { key: [float_timestamp, ...] }
_api_rate_tracker: Dict[str, list[float]] = {}
_MAX_API_BUCKETS = 10000


def _purge_stale_api_records(window_seconds: int) -> None:
    now = time.time()
    stale = [
        key for key, timestamps in _api_rate_tracker.items()
        if not timestamps or (now - timestamps[-1]) >= window_seconds
    ]
    for key in stale:
        _api_rate_tracker.pop(key, None)

    overflow = len(_api_rate_tracker) - _MAX_API_BUCKETS
    if overflow > 0:
        for key in list(_api_rate_tracker.keys())[:overflow]:
            _api_rate_tracker.pop(key, None)


def check_api_rate_limit(
    key: str,
    max_requests: int = 30,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """Evalúa y registra una petición bajo ventana deslizante en memoria."""
    now = time.time()
    _purge_stale_api_records(window_seconds)
    recent = [t for t in _api_rate_tracker.get(key, []) if now - t < window_seconds]
    if len(recent) >= max_requests:
        _api_rate_tracker[key] = recent
        retry_after = max(1, int(window_seconds - (now - recent[0])) + 1)
        return False, retry_after
    recent.append(now)
    _api_rate_tracker[key] = recent
    return True, 0


def reset_api_rate_limits() -> None:
    """Limpia todos los contadores de rate-limit de la API."""
    _api_rate_tracker.clear()


def require_api_rate_limit(
    bucket: str,
    max_requests: int = 30,
    window_seconds: int = 60,
):
    """Dependencia FastAPI para limitar abuso en endpoints sensibles."""
    def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        session_token = request.cookies.get(SESSION_COOKIE_NAME) or ""
        subject = hashlib.sha256(session_token.encode("utf-8", errors="ignore")).hexdigest()[:12] if session_token else client_ip
        key = f"{bucket}:{client_ip}:{subject}"
        allowed, retry_after = check_api_rate_limit(
            key, max_requests=max_requests, window_seconds=window_seconds
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Límite de frecuencia excedido para '{bucket}'. Reintente en {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency
