#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"
set -e

# Cargar helper de Discord si existe
if [ -f "/home/steam/scripts/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "/home/steam/scripts/discord.sh"
elif [ -f "$(dirname "$0")/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "$(dirname "$0")/discord.sh"
fi

echo "================================================================="
echo "  🦕 ARK: Survival Evolved - Repoblación de Dinos Salvajes"
echo "================================================================="

# Verificar que arkmanager esté disponible
if ! command -v arkmanager >/dev/null 2>&1; then
    echo "[ERROR] arkmanager no se encuentra en el sistema."
    exit 1
fi

LANG="${DISCORD_LANGUAGE:-es}"

# 1. Enviar aviso in-game a los jugadores conectados
if [ "$LANG" = "en" ]; then
    WARN_MSG="[ADMIN] Resetting wild dinosaur population (DestroyWildDinos). Your tamed dinos are safe."
    DISCORD_DESC="Wild dino population was wiped across ${WORLD:-TheIsland} for fresh repopulation. Tamed dinos and structures were not affected."
else
    WARN_MSG="[ADMIN] Reiniciando fauna salvaje (DestroyWildDinos). Tus dinos domesticados estan a salvo."
    DISCORD_DESC="Se reinicio la fauna salvaje en ${WORLD:-TheIsland} para repoblacion limpia. Los dinos domesticados y estructuras no fueron afectados."
fi

echo "[wipe-dinos] Enviando aviso in-game por broadcast..."
arkmanager broadcast "$WARN_MSG" @main 2>/dev/null || true
sleep 3

# 2. Ejecutar DestroyWildDinos por RCON
echo "[wipe-dinos] Ejecutando comando RCON: DestroyWildDinos..."
if arkmanager rconcmd "DestroyWildDinos" @main; then
    echo "[wipe-dinos] Comando ejecutado con éxito. Los nuevos dinos salvajes comenzarán a aparecer en los próximos minutos."
    
    # 3. Notificar a Discord
    if command -v send_discord_embed >/dev/null 2>&1; then
        send_discord_embed "WILD_DINOS_WIPED" "$DISCORD_DESC"
    fi
else
    echo "[ERROR] No se pudo ejecutar el comando RCON. Verifica que el servidor de ARK esté encendido y RCON activo."
    exit 1
fi

echo "================================================================="
echo "  ✅ Limpieza y repoblación de dinosaurios completada."
echo "================================================================="
exit 0
