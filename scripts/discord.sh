#!/bin/bash
# Reusable Discord Webhook Embed Helper for ARK Server Scripts

send_discord_embed() {
    local event_type="$1"
    local custom_msg="$2"

    if [ -z "${DISCORD_WEBHOOK_URL}" ]; then
        return 0
    fi

    # Ensure jq and curl are available
    if ! command -v jq >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
        return 0
    fi

    local title=""
    local color=3066993
    local status_text="🟢 Online"
    local lang="${DISCORD_LANGUAGE:-es}"

    case "$event_type" in
        "STARTING")
            color=15844367 # Yellow (#F1C40F)
            status_text="⏳ Cargando / Starting"
            title=$([ "$lang" = "en" ] && echo "⏳ Starting ARK Server" || echo "⏳ Cargando Servidor de ARK")
            ;;
        "START")
            color=3066993 # Green (#2ECC71)
            status_text="🟢 Online"
            title=$([ "$lang" = "en" ] && echo "🚀 ARK Server 100% Online" || echo "🚀 Servidor de ARK Online")
            ;;
        "SHUTDOWN_WARN")
            color=15844367 # Yellow (#F1C40F)
            status_text="⚠️ Programado / Scheduled"
            title=$([ "$lang" = "en" ] && echo "⚠️ Scheduled Shutdown Warning" || echo "⚠️ Aviso de Apagado Programado")
            ;;
        "SHUTDOWN")
            color=15158332 # Red (#E74C3C)
            status_text="🔴 Offline"
            title=$([ "$lang" = "en" ] && echo "🛑 ARK Server Offline" || echo "🛑 Servidor de ARK Apagado")
            ;;
        "BACKUP_OK")
            color=3447003 # Blue (#3498DB)
            status_text="📦 Backup OK"
            title=$([ "$lang" = "en" ] && echo "📦 Backup Created Successfully" || echo "📦 Copia de Seguridad Completada")
            ;;
        "BACKUP_MANUAL")
            color=3447003 # Blue (#3498DB)
            status_text="📦 Backup Manual"
            title=$([ "$lang" = "en" ] && echo "📦 Manual Backup Created" || echo "📦 Copia de Seguridad Manual Creada")
            ;;
        "BACKUP_FAIL")
            color=15158332 # Red (#E74C3C)
            status_text="⚠️ Backup Error"
            title=$([ "$lang" = "en" ] && echo "⚠️ Backup Creation Failed" || echo "⚠️ Fallo en Copia de Seguridad")
            ;;
        "RESTORE_OK")
            color=15105570 # Orange (#E67E22)
            status_text="🔄 Restaurado / Restored"
            title=$([ "$lang" = "en" ] && echo "🔄 Server Save Restored" || echo "🔄 Servidor de ARK Restaurado")
            ;;
        "RESTART")
            color=10181046 # Purple (#9B59B6)
            status_text="🔄 Reiniciando / Restarting"
            title=$([ "$lang" = "en" ] && echo "🔄 Server Restart Sequence" || echo "🔄 Secuencia de Reinicio Programado")
            ;;
        "WILD_DINOS_WIPED")
            color=1752220 # Teal (#1ABC9C)
            status_text="🦕 Fauna Reiniciada"
            title=$([ "$lang" = "en" ] && echo "🦕 Wild Dinos Reset" || echo "🦕 Fauna Salvaje Reiniciada")
            ;;
        *)
            color=3447003
            title="ℹ️ Notificación de ARK"
            ;;
    esac

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local session_name="${SESSION_NAME:-ARK Server}"
    local world="${WORLD:-TheIsland}"
    local payload

    payload=$(jq -n \
        --arg username "$session_name" \
        --arg avatar_url "https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/logo.png" \
        --arg title "$title" \
        --arg description "$custom_msg" \
        --argjson color "$color" \
        --arg session_field "$session_name" \
        --arg world_field "$world" \
        --arg status_field "$status_text" \
        --arg footer_text "ARK: Survival Evolved Docker" \
        --arg footer_icon "https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/logo.png" \
        --arg timestamp "$timestamp" \
        '{
            username: $username,
            avatar_url: $avatar_url,
            embeds: [{
                title: $title,
                description: $description,
                color: $color,
                fields: [
                    {name: "🎮 Servidor", value: ("`" + $session_field + "`"), inline: true},
                    {name: "🗺️ Mapa", value: ("`" + $world_field + "`"), inline: true},
                    {name: "📊 Estado", value: $status_field, inline: true}
                ],
                footer: {text: $footer_text, icon_url: $footer_icon},
                timestamp: $timestamp
            }]
        }')

    curl -s -H "Content-Type: application/json" -X POST -d "$payload" "${DISCORD_WEBHOOK_URL}" > /dev/null 2>&1 || true
}
