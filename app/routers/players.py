from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.core.security import require_auth
from app.core.player_manager import player_manager
from app.core.rcon_client import escape_rcon_quoted_text, sanitize_steam_id
from app.core.activity_manager import activity_manager

router = APIRouter(tags=["players"], dependencies=[Depends(require_auth)])


class KickBanRequest(BaseModel):
    steam_id: str

    @field_validator("steam_id")
    @classmethod
    def validate_steam_id(cls, value: str) -> str:
        return sanitize_steam_id(value)


class PlayerMessageRequest(BaseModel):
    steam_id: str
    message: str

    @field_validator("steam_id")
    @classmethod
    def validate_steam_id(cls, value: str) -> str:
        return sanitize_steam_id(value)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not escape_rcon_quoted_text(value):
            raise ValueError("El mensaje no puede estar vacío.")
        return value


@router.get("/api/players")
async def api_players():
    online = await player_manager.get_online_players()
    history = player_manager.get_all_history()
    return {
        "online": online,
        "online_count": len(online),
        "history": history
    }


@router.post("/api/players/message")
async def api_player_message(req: PlayerMessageRequest):
    try:
        resp = await player_manager.message_player(req.steam_id, req.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    activity_manager.log("Jugadores", f"Mensaje privado a {req.steam_id}: {req.message}")
    return {"success": True, "response": resp}


@router.post("/api/players/kick")
async def api_player_kick(req: KickBanRequest):
    try:
        resp = await player_manager.kick(req.steam_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    activity_manager.log("Jugadores", f"Superviviente expulsado: {req.steam_id}")
    return {"success": True, "response": resp}


@router.post("/api/players/ban")
async def api_player_ban(req: KickBanRequest):
    try:
        resp = await player_manager.ban(req.steam_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    activity_manager.log("Jugadores", f"Superviviente baneado: {req.steam_id}")
    return {"success": True, "response": resp}


@router.post("/api/players/unban")
async def api_player_unban(req: KickBanRequest):
    try:
        resp = await player_manager.unban(req.steam_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    activity_manager.log("Jugadores", f"Superviviente desbaneado: {req.steam_id}")
    return {"success": True, "response": resp}
