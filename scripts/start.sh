#!/bin/bash

validate_integer() {
    local var_name="$1"
    local var_value="$2"
    if [ -n "$var_value" ] && ! [[ "$var_value" =~ ^[0-9]+$ ]]; then
        echo "ERROR: $var_name debe ser un número entero, recibido: '$var_value'"
        exit 1
    fi
}

validate_time_format() {
    local var_name="$1"
    local var_value="$2"
    if [ -n "$var_value" ] && ! [[ "$var_value" =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]]; then
        echo "ERROR: $var_name debe tener formato HH:MM (24 horas), recibido: '$var_value'"
        exit 1
    fi
}

validate_integer "MAX_PLAYERS" "$MAX_PLAYERS"
validate_integer "SERVER_PORT" "$SERVER_PORT"
validate_integer "QUERY_PORT" "$QUERY_PORT"
validate_integer "RCON_PORT" "$RCON_PORT"
validate_integer "BACKUP_INTERVAL_HOURS" "$BACKUP_INTERVAL_HOURS"
validate_integer "BACKUP_MAX_COUNT" "$BACKUP_MAX_COUNT"
validate_integer "AUTO_RESTART_HOURS" "$AUTO_RESTART_HOURS"
validate_integer "SCHEDULE_WARN_MINUTES" "${SCHEDULE_WARN_MINUTES:-10}"

if [ "${SCHEDULE_ENABLED:-false}" = "true" ]; then
    if [ -z "$SCHEDULE_START" ] || [ -z "$SCHEDULE_STOP" ]; then
        echo "ERROR: SCHEDULE_ENABLED está activo pero SCHEDULE_START o SCHEDULE_STOP no están definidos o están vacíos."
        exit 1
    fi
    validate_time_format "SCHEDULE_START" "$SCHEDULE_START"
    validate_time_format "SCHEDULE_STOP" "$SCHEDULE_STOP"
fi

if [ "${ADMIN_PASSWORD:-adminpass}" = "adminpass" ]; then
    echo "⚠️  ADVERTENCIA: Estás usando la contraseña de administrador por defecto (adminpass)."
    echo "⚠️  Cámbiala en tu .env con ADMIN_PASSWORD=tu_contraseña_segura antes de exponer este servidor."
fi

echo "Starting ARK server with arkmanager..."

# Create arkmanager configuration
tee /etc/arkmanager/arkmanager.cfg > /dev/null << EOF
# ARK Server Manager Configuration
arkserverroot="/home/steam/steamcmd/ark"
arkserverexec="ShooterGame/Binaries/Linux/ShooterGameServer"
arkbackupdir="${BACKUP_DIR:-/home/steam/ark-backups}"
arkwarnminutes="15"
arkAutoUpdateOnStart="${UPDATE_ON_START:-true}"
arkprecisewarn="false"

# SteamCMD Configuration
steamcmdroot="/home/steam/steamcmd"
steamcmdexec="steamcmd.sh"
steamcmd_user="steam"
appid="376030"

logdir="/var/log/arktools"

# Server Configuration
serverMap="${WORLD:-TheIsland}"
ark_ServerPassword="${SERVER_PASSWORD:-}"
ark_ServerAdminPassword="${ADMIN_PASSWORD:-adminpass}"
ark_RCONEnabled="${RCON_ENABLED:-True}"
ark_RCONPort="${RCON_PORT:-27020}"
ark_Port="${SERVER_PORT:-7777}"
ark_QueryPort="${QUERY_PORT:-27015}"
ark_MaxPlayers="${MAX_PLAYERS:-10}"
ark_SessionName="${SESSION_NAME:-ARK Server}"
arkNoPortDecrement="true"
EOF


# Add Discord Webhook URL if configured
if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
    echo "discordWebhookURL=\"${DISCORD_WEBHOOK_URL}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Discord Webhook notifications enabled"
fi

# Add Rate Multipliers if configured
if [ -n "${XP_MULTIPLIER}" ]; then
    echo "ark_XPMultiplier=\"${XP_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "XP Multiplier configured: ${XP_MULTIPLIER}x"
fi
if [ -n "${TAME_SPEED_MULTIPLIER}" ]; then
    echo "ark_TamingSpeedMultiplier=\"${TAME_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Taming Speed Multiplier configured: ${TAME_SPEED_MULTIPLIER}x"
fi
if [ -n "${HARVEST_AMOUNT_MULTIPLIER}" ]; then
    echo "ark_HarvestAmountMultiplier=\"${HARVEST_AMOUNT_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Harvest Amount Multiplier configured: ${HARVEST_AMOUNT_MULTIPLIER}x"
fi
if [ -n "${HATCH_SPEED_MULTIPLIER}" ]; then
    echo "ark_EggHatchSpeedMultiplier=\"${HATCH_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Egg Hatch Speed Multiplier configured: ${HATCH_SPEED_MULTIPLIER}x"
fi
if [ -n "${MATURATION_SPEED_MULTIPLIER}" ]; then
    echo "ark_BabyMatureSpeedMultiplier=\"${MATURATION_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Baby Maturation Speed Multiplier configured: ${MATURATION_SPEED_MULTIPLIER}x"
fi
if [ -n "${MATING_INTERVAL_MULTIPLIER}" ]; then
    echo "ark_MatingIntervalMultiplier=\"${MATING_INTERVAL_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Mating Interval Multiplier configured: ${MATING_INTERVAL_MULTIPLIER}x"
fi
if [ -n "${CRAFT_SPEED_MULTIPLIER}" ]; then
    echo "ark_CraftingSpeedMultiplier=\"${CRAFT_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Crafting Speed Multiplier configured: ${CRAFT_SPEED_MULTIPLIER}x"
fi

# Add PvE flag if enabled
if [ "${SERVER_PVE}" = "true" ]; then
    echo "ark_ServerPVE=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Add BattlEye configuration
if [ "${BATTLEEYE}" = "true" ]; then
    echo "arkflag_UseBattlEye=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
else
    echo "arkflag_NoBattlEye=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Add cluster configuration if set
if [ ! -z "${CLUSTER_ID}" ] && [ "${CLUSTER_ID}" != "" ]; then
    echo "arkopt_clusterid=\"${CLUSTER_ID}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Cluster ID configured: ${CLUSTER_ID}"
fi

if [ ! -z "${CLUSTER_DIR_OVERRIDE}" ] && [ "${CLUSTER_DIR_OVERRIDE}" != "" ]; then
    echo "arkopt_ClusterDirOverride=\"${CLUSTER_DIR_OVERRIDE}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Add mods if specified
if [ ! -z "${MOD_IDS}" ] && [ "${MOD_IDS}" != "" ]; then
    echo "ark_GameModIds=\"${MOD_IDS}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "Mods configured: ${MOD_IDS}"
fi

# Add additional arguments if set
if [ ! -z "${ADDITIONAL_ARGS}" ] && [ "${ADDITIONAL_ARGS}" != "" ]; then
    echo "" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "# Additional custom arguments" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    for arg in ${ADDITIONAL_ARGS}; do
        if [[ $arg == -* ]]; then
            flag="${arg#-}"
            echo "arkflag_${flag}=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
        fi
    done
    echo "Additional arguments configured: ${ADDITIONAL_ARGS}"
fi

# Add raw arkmanager.cfg options if specified
if [ ! -z "${ARKMANAGER_OPTS}" ] && [ "${ARKMANAGER_OPTS}" != "" ]; then
    echo "" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "# Custom arkmanager options" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    while IFS= read -r line; do
        echo "${line}" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    done <<< "${ARKMANAGER_OPTS}"
    echo "Custom arkmanager options configured"
fi

# Always enable logging
echo "arkflag_log=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null

# Create instance configuration
mkdir -p /etc/arkmanager/instances
tee /etc/arkmanager/instances/main.cfg > /dev/null << EOF
# Instance Configuration
arkserverroot="/home/steam/steamcmd/ark"
arkserverexec="ShooterGame/Binaries/Linux/ShooterGameServer"
EOF

# Install ARK server if it doesn't exist
if [ ! -f "/home/steam/steamcmd/ark/ShooterGame/Binaries/Linux/ShooterGameServer" ]; then
    echo "Installing ARK server (this may take a while)..."
    echo "Server will be installed to: /home/steam/steamcmd/ark"
    echo "Beta branch: ${BETA:-public}"
    
    # Run install with beta flag
    if [ "${BETA}" = "public" ] || [ -z "${BETA}" ]; then
        arkmanager install @main 2>&1
    else
        echo "Updating ARK server (this may take a while)..."
        arkmanager install --beta="${BETA}" @main 2>&1
    fi
    
    if [ -f "/home/steam/steamcmd/ark/ShooterGame/Binaries/Linux/ShooterGameServer" ]; then
        echo "ARK server installation completed successfully!"
    else
        echo "ERROR: ARK server installation failed - binary not found"
        echo "Checking directory contents:"
        ls -la /home/steam/steamcmd/ark/ || echo "Directory does not exist"
        exit 1
    fi
fi

# Install mods if specified
if [ ! -z "$MOD_IDS" ] && [ "$MOD_IDS" != "" ]; then
    echo "Installing mods: $MOD_IDS"
    IFS=',' read -ra MODS <<< "$MOD_IDS"
    _FAILED_MODS=()
    for mod in "${MODS[@]}"; do
        mod=$(echo "$mod" | tr -d ' ')
        [ -z "$mod" ] && continue
        echo "Installing mod: $mod"
        if ! arkmanager installmod "$mod" @main; then
            echo "ERROR: Failed to install mod $mod (check that the Workshop ID is correct and the mod is public)"
            _FAILED_MODS+=("$mod")
        fi
    done
    if [ ${#_FAILED_MODS[@]} -gt 0 ]; then
        echo "WARNING: ${#_FAILED_MODS[@]} mod(s) failed to install: ${_FAILED_MODS[*]}"
        echo "The server will still start, but these mods will not be active."
    fi
fi

# Update server if UPDATE_ON_START is set
if [ "${UPDATE_ON_START}" = "true" ]; then
    echo "Updating ARK server..."
    if [ "${BETA}" = "public" ] || [ -z "${BETA}" ]; then
        arkmanager update --update-mods @main
    else
        arkmanager update --beta="${BETA}" --update-mods @main
    fi
fi

_SCHEDULE_WARN_SENT=false

# Discord webhook message localization
if [ "${DISCORD_LANGUAGE:-es}" = "en" ]; then
    _DISCORD_MSG_BACKUP_OK="📦 **[ARK Backup]** Scheduled backup completed successfully on server **${SESSION_NAME:-ARK Server}**."
    _DISCORD_MSG_BACKUP_FAIL="⚠️ **[ARK Backup Warning]** Scheduled backup creation failed on server **${SESSION_NAME:-ARK Server}**."
    _DISCORD_MSG_RESTART="🔄 **[ARK Server Restart]** Initiating scheduled restart sequence (interval: ${AUTO_RESTART_HOURS}h) with in-game warnings."
    _DISCORD_MSG_SCHEDULE_START="⏰ **[ARK Power Schedule]** Server started according to schedule (${SCHEDULE_START:-20:00} - ${SCHEDULE_STOP:-00:00})."
    _DISCORD_MSG_SCHEDULE_WARN="⏰ **[ARK Power Schedule]** Server will shut down in ${SCHEDULE_WARN_MINUTES:-10} minute(s) according to schedule."
    _DISCORD_MSG_SCHEDULE_STOP="⏰ **[ARK Power Schedule]** Server shut down according to schedule (${SCHEDULE_START:-20:00} - ${SCHEDULE_STOP:-00:00})."
else
    _DISCORD_MSG_BACKUP_OK="📦 **[ARK Backup]** Backup programado completado exitosamente en el servidor **${SESSION_NAME:-ARK Server}**."
    _DISCORD_MSG_BACKUP_FAIL="⚠️ **[ARK Backup Warning]** Falló la creación del backup programado en el servidor **${SESSION_NAME:-ARK Server}**."
    _DISCORD_MSG_RESTART="🔄 **[ARK Server Restart]** Iniciando secuencia de reinicio programado (intervalo: ${AUTO_RESTART_HOURS}h) con avisos in-game."
    _DISCORD_MSG_SCHEDULE_START="⏰ **[ARK Power Schedule]** Servidor encendido según el horario programado (${SCHEDULE_START:-20:00} - ${SCHEDULE_STOP:-00:00})."
    _DISCORD_MSG_SCHEDULE_WARN="⏰ **[ARK Power Schedule]** El servidor se apagará en ${SCHEDULE_WARN_MINUTES:-10} minuto(s) según el horario programado."
    _DISCORD_MSG_SCHEDULE_STOP="⏰ **[ARK Power Schedule]** Servidor apagado según el horario programado (${SCHEDULE_START:-20:00} - ${SCHEDULE_STOP:-00:00})."
fi

# Initial check for power schedule before starting server
_INITIAL_IN_WINDOW=true
if [ "${SCHEDULE_ENABLED:-false}" = "true" ]; then
    _NOW_H=$(date +%H)
    _NOW_M=$(date +%M)
    _NOW_MINUTES=$(( 10#$_NOW_H * 60 + 10#$_NOW_M ))
    _START_H="${SCHEDULE_START%%:*}"
    _START_M="${SCHEDULE_START#*:}"
    _START_MINUTES=$(( 10#$_START_H * 60 + 10#$_START_M ))
    _STOP_H="${SCHEDULE_STOP%%:*}"
    _STOP_M="${SCHEDULE_STOP#*:}"
    _STOP_MINUTES=$(( 10#$_STOP_H * 60 + 10#$_STOP_M ))

    if [ "$_START_MINUTES" -le "$_STOP_MINUTES" ]; then
        _INITIAL_IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] && [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
    else
        _INITIAL_IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] || [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
    fi
fi

if [ "$_INITIAL_IN_WINDOW" = "true" ]; then
    echo "Starting ARK server..."
    arkmanager start --noautoupdate @main
else
    echo "[schedule] Server schedule enabled and outside active window (${SCHEDULE_START} - ${SCHEDULE_STOP}). Process start deferred."
fi

# Monitor the server's status
_BACKUP_LAST_RUN=$(date +%s)
_BACKUP_INTERVAL_SECS=$(( ${BACKUP_INTERVAL_HOURS:-6} * 3600 ))

_RESTART_LAST_RUN=$(date +%s)
_RESTART_INTERVAL_SECS=$(( ${AUTO_RESTART_HOURS:-0} * 3600 ))

while true; do
    _STATUS_OUTPUT=$(arkmanager status @main 2>&1 || true)
    echo "$_STATUS_OUTPUT"
    _NOW=$(date +%s)

    # --- Power Schedule Monitoring ---
    _IN_WINDOW=true
    if [ "${SCHEDULE_ENABLED:-false}" = "true" ]; then
        _NOW_H=$(date +%H)
        _NOW_M=$(date +%M)
        _NOW_MINUTES=$(( 10#$_NOW_H * 60 + 10#$_NOW_M ))
        _START_H="${SCHEDULE_START%%:*}"
        _START_M="${SCHEDULE_START#*:}"
        _START_MINUTES=$(( 10#$_START_H * 60 + 10#$_START_M ))
        _STOP_H="${SCHEDULE_STOP%%:*}"
        _STOP_M="${SCHEDULE_STOP#*:}"
        _STOP_MINUTES=$(( 10#$_STOP_H * 60 + 10#$_STOP_M ))

        if [ "$_START_MINUTES" -le "$_STOP_MINUTES" ]; then
            # Ventana normal, no cruza medianoche (ej. 08:00 a 18:00)
            _IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] && [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
            _MINUTES_UNTIL_STOP=$(( _STOP_MINUTES - _NOW_MINUTES ))
        else
            # Ventana cruza medianoche (ej. 20:00 a 00:00)
            _IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] || [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
            if [ "$_NOW_MINUTES" -ge "$_START_MINUTES" ]; then
                _MINUTES_UNTIL_STOP=$(( 1440 - _NOW_MINUTES + _STOP_MINUTES ))
            else
                _MINUTES_UNTIL_STOP=$(( _STOP_MINUTES - _NOW_MINUTES ))
            fi
        fi

        _IS_RUNNING=$(pgrep "ShooterGameServer" > /dev/null 2>&1 && echo true || echo false)

        if [ "$_IN_WINDOW" = "true" ]; then
            if [ "$_IS_RUNNING" = "false" ]; then
                echo "[schedule] Inside scheduled window (${SCHEDULE_START} - ${SCHEDULE_STOP}). Starting ARK server..."
                _SCHEDULE_WARN_SENT=false
                if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                    curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_SCHEDULE_START}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                fi
                arkmanager start --noautoupdate @main
            else
                _WARN_MINS=${SCHEDULE_WARN_MINUTES:-10}
                if [ "$_SCHEDULE_WARN_SENT" = "false" ] && [ "$_WARN_MINS" -gt 0 ] && [ "$_MINUTES_UNTIL_STOP" -le "$_WARN_MINS" ] && [ "$_MINUTES_UNTIL_STOP" -gt 0 ]; then
                    echo "[schedule] Sending shutdown warning (${_MINUTES_UNTIL_STOP} min remaining until ${SCHEDULE_STOP})..."
                    if [ "${DISCORD_LANGUAGE:-es}" = "en" ]; then
                        _WARN_MSG="[SCHEDULE] Server will shut down in ${_MINUTES_UNTIL_STOP} minute(s) according to schedule (${SCHEDULE_STOP})."
                    else
                        _WARN_MSG="[HORARIO] El servidor se apagara en ${_MINUTES_UNTIL_STOP} minuto(s) segun el horario programado (${SCHEDULE_STOP})."
                    fi
                    arkmanager broadcast "${_WARN_MSG}" @main || true
                    if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                        curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_SCHEDULE_WARN}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                    fi
                    _SCHEDULE_WARN_SENT=true
                fi
            fi
        else
            if [ "$_IS_RUNNING" = "true" ]; then
                _ACTIVE_PLAYERS=$(echo "$_STATUS_OUTPUT" | grep -i "Active.*Players:" | grep -o '[0-9]\+' | head -n 1)
                _ACTIVE_PLAYERS=${_ACTIVE_PLAYERS:-0}

                if [ "$_ACTIVE_PLAYERS" -gt 0 ]; then
                    echo "[schedule] Fuera de horario (${SCHEDULE_START} - ${SCHEDULE_STOP}) pero hay ${_ACTIVE_PLAYERS} jugador(es) conectado(s), posponiendo apagado..."
                else
                    echo "[schedule] Outside scheduled window (${SCHEDULE_START} - ${SCHEDULE_STOP}) and 0 active players. Stopping ARK server..."
                    if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                        curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_SCHEDULE_STOP}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                    fi
                    arkmanager stop --saveworld @main
                    _SCHEDULE_WARN_SENT=false
                fi
            else
                _SCHEDULE_WARN_SENT=false
            fi
        fi
    fi
    # --- End Power Schedule Monitoring ---

    # --- Automatic backup ---
    if [ "${BACKUP_ENABLED:-true}" = "true" ]; then
        _ELAPSED=$(( _NOW - _BACKUP_LAST_RUN ))
        if [ "${_ELAPSED}" -ge "${_BACKUP_INTERVAL_SECS}" ]; then
            echo "[backup] Saving world state prior to scheduled backup..."
            arkmanager saveworld @main || true
            echo "[backup] Running scheduled backup (interval: ${BACKUP_INTERVAL_HOURS:-6}h)..."
            mkdir -p "${BACKUP_DIR:-/home/steam/ark-backups}"
            if arkmanager backup @main; then
                echo "[backup] Backup completed at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                
                # Backup rotation by count
                if [ -n "${BACKUP_MAX_COUNT}" ] && [ "${BACKUP_MAX_COUNT:-0}" -gt 0 ]; then
                    _MAX_KEEP="${BACKUP_MAX_COUNT}"
                    _BDIR="${BACKUP_DIR:-/home/steam/ark-backups}"
                    _COUNT=$(find "${_BDIR}" -name "*.tar.bz2" -type f 2>/dev/null | wc -l)
                    if [ "${_COUNT}" -gt "${_MAX_KEEP}" ]; then
                        echo "[backup] Rotating backups (keeping latest ${_MAX_KEEP} of ${_COUNT})..."
                        find "${_BDIR}" -name "*.tar.bz2" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | cut -d' ' -f2- | tail -n +$(( _MAX_KEEP + 1 )) | while read -r _OLD_FILE; do
                            if [ -f "${_OLD_FILE}" ]; then
                                echo "[backup] Removing old backup: ${_OLD_FILE}"
                                rm -f "${_OLD_FILE}"
                                rmdir "$(dirname "${_OLD_FILE}")" 2>/dev/null || true
                            fi
                        done
                    fi
                fi

                if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                    curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_BACKUP_OK}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                fi
            else
                echo "[backup] WARNING: Backup failed at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
                if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                    curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_BACKUP_FAIL}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                fi
            fi
            _BACKUP_LAST_RUN=$_NOW
        fi
    fi
    # --- End backup ---

    # --- Scheduled Restart ---
    if [ "${AUTO_RESTART_HOURS:-0}" -gt 0 ]; then
        _SKIP_RESTART=false
        if [ "${SCHEDULE_ENABLED:-false}" = "true" ] && [ "${_IN_WINDOW}" = "false" ] && ! pgrep "ShooterGameServer" > /dev/null 2>&1; then
            _SKIP_RESTART=true
        fi

        if [ "$_SKIP_RESTART" = "true" ]; then
            _RESTART_LAST_RUN=$_NOW
        else
            _RESTART_ELAPSED=$(( _NOW - _RESTART_LAST_RUN ))
            if [ "${_RESTART_ELAPSED}" -ge "${_RESTART_INTERVAL_SECS}" ]; then
                echo "[restart] Triggering scheduled server restart (interval: ${AUTO_RESTART_HOURS}h)..."
                if [ -n "${DISCORD_WEBHOOK_URL}" ]; then
                    curl -s -H "Content-Type: application/json" -X POST -d "{\"content\": \"${_DISCORD_MSG_RESTART}\"}" "${DISCORD_WEBHOOK_URL}" > /dev/null || true
                fi
                arkmanager restart --warn @main
                _RESTART_LAST_RUN=$(date +%s)
            fi
        fi
    fi
    # --- End Scheduled Restart ---

    # --- Periodic Log Cleanup ---
    # Purge log files older than 7 days from /var/log/arktools
    find /var/log/arktools -type f -mtime +7 -delete 2>/dev/null || true

    sleep 60
done
