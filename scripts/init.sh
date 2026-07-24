#!/bin/bash
set -e

# Show branding
cat /branding

# Set PUID/PGID
if [ -n "${PUID}" ] && [ -n "${PGID}" ]; then
    echo "Setting steam user to UID:${PUID} GID:${PGID}"
    usermod -o -u "${PUID}" steam
    groupmod -o -g "${PGID}" steam
fi

# Fix permissions
chown -R steam:steam /home/steam /var/log/arktools
chown -R steam:steam /etc/arkmanager

# Trap signals for graceful shutdown
trap 'su - steam -c "arkmanager stop --saveworld @main" && exit 0' SIGTERM SIGINT

# Export and pass environment variables to steam user
su - steam -c "
    export PUID='${PUID}'
    export PGID='${PGID}'
    export SESSION_NAME='${SESSION_NAME}'
    export SERVER_PASSWORD='${SERVER_PASSWORD}'
    export ADMIN_PASSWORD='${ADMIN_PASSWORD}'
    export MAX_PLAYERS='${MAX_PLAYERS}'
    export WORLD='${WORLD}'
    export SERVER_PORT='${SERVER_PORT}'
    export QUERY_PORT='${QUERY_PORT}'
    export RCON_PORT='${RCON_PORT}'
    export RCON_ENABLED='${RCON_ENABLED}'
    export SERVER_PVE='${SERVER_PVE}'
    export BATTLEEYE='${BATTLEEYE}'
    export CLUSTER_ID='${CLUSTER_ID}'
    export CLUSTER_DIR_OVERRIDE='${CLUSTER_DIR_OVERRIDE}'
    export MOD_IDS='${MOD_IDS}'
    export ADDITIONAL_ARGS='${ADDITIONAL_ARGS}'
    export ARKMANAGER_OPTS='${ARKMANAGER_OPTS}'
    export BETA='${BETA}'
    export UPDATE_ON_START='${UPDATE_ON_START}'
    export BACKUP_ENABLED='${BACKUP_ENABLED}'
    export BACKUP_INTERVAL_HOURS='${BACKUP_INTERVAL_HOURS}'
    export BACKUP_DIR='${BACKUP_DIR}'
    export BACKUP_MAX_COUNT='${BACKUP_MAX_COUNT}'
    export DISCORD_WEBHOOK_URL='${DISCORD_WEBHOOK_URL}'
    export DISCORD_LANGUAGE='${DISCORD_LANGUAGE}'
    export AUTO_RESTART_HOURS='${AUTO_RESTART_HOURS}'
    export SCHEDULE_ENABLED='${SCHEDULE_ENABLED}'
    export SCHEDULE_START='${SCHEDULE_START}'
    export SCHEDULE_STOP='${SCHEDULE_STOP}'
    export TZ='${TZ}'
    export SCHEDULE_WARN_MINUTES='${SCHEDULE_WARN_MINUTES}'
    export XP_MULTIPLIER='${XP_MULTIPLIER}'
    export TAME_SPEED_MULTIPLIER='${TAME_SPEED_MULTIPLIER}'
    export HARVEST_AMOUNT_MULTIPLIER='${HARVEST_AMOUNT_MULTIPLIER}'
    export HATCH_SPEED_MULTIPLIER='${HATCH_SPEED_MULTIPLIER}'
    export MATURATION_SPEED_MULTIPLIER='${MATURATION_SPEED_MULTIPLIER}'
    export MATING_INTERVAL_MULTIPLIER='${MATING_INTERVAL_MULTIPLIER}'
    export CRAFT_SPEED_MULTIPLIER='${CRAFT_SPEED_MULTIPLIER}'
    bash /home/steam/scripts/start.sh
"
