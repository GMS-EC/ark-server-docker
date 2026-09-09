#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"

echo "[ARK Server Manager] Generando configuración de arkmanager desde variables de entorno..."
mkdir -p /etc/arkmanager /var/log/arktools /etc/arkmanager/instances

tee /etc/arkmanager/arkmanager.cfg > /dev/null << EOF
# ARK Server Manager Configuration
arkserverroot="${ARK_DATA_DIR:-/home/steam/steamcmd/ark}"
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

# Server Identity & Ports
serverMap="${WORLD:-TheIsland}"
ark_SessionName="${SESSION_NAME:-ARK Server}"
ark_ServerPassword="${SERVER_PASSWORD:-}"
ark_ServerAdminPassword="${ADMIN_PASSWORD:-adminpass}"
rconpassword="${ADMIN_PASSWORD:-adminpass}"
ark_RCONEnabled="${RCON_ENABLED:-True}"
ark_RCONPort="${RCON_PORT:-27020}"
rconport="${RCON_PORT:-27020}"
ark_Port="${SERVER_PORT:-7777}"
ark_QueryPort="${QUERY_PORT:-27015}"
ark_MaxPlayers="${MAX_PLAYERS:-10}"
arkNoPortDecrement="true"
EOF

# Multiplicadores de Jugabilidad
if [ -n "${XP_MULTIPLIER}" ]; then
    echo "ark_XPMultiplier=\"${XP_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${TAME_SPEED_MULTIPLIER}" ]; then
    echo "ark_TamingSpeedMultiplier=\"${TAME_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${HARVEST_AMOUNT_MULTIPLIER}" ]; then
    echo "ark_HarvestAmountMultiplier=\"${HARVEST_AMOUNT_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${HATCH_SPEED_MULTIPLIER}" ]; then
    echo "ark_EggHatchSpeedMultiplier=\"${HATCH_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${MATURATION_SPEED_MULTIPLIER}" ]; then
    echo "ark_BabyMatureSpeedMultiplier=\"${MATURATION_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${MATING_INTERVAL_MULTIPLIER}" ]; then
    echo "ark_MatingIntervalMultiplier=\"${MATING_INTERVAL_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi
if [ -n "${CRAFT_SPEED_MULTIPLIER}" ]; then
    echo "ark_CraftingSpeedMultiplier=\"${CRAFT_SPEED_MULTIPLIER}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Modo PvE
if [ "${SERVER_PVE}" = "true" ]; then
    echo "ark_ServerPVE=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# BattlEye
if [ "${BATTLEEYE}" = "true" ]; then
    echo "arkflag_UseBattlEye=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
else
    echo "arkflag_NoBattlEye=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Clúster
if [ -n "${CLUSTER_ID}" ]; then
    echo "arkopt_clusterid=\"${CLUSTER_ID}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    cluster_dir="${CLUSTER_DIR_OVERRIDE:-/home/steam/clusters}"
    echo "arkopt_ClusterDirOverride=\"${cluster_dir}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
elif [ -n "${CLUSTER_DIR_OVERRIDE}" ]; then
    echo "arkopt_ClusterDirOverride=\"${CLUSTER_DIR_OVERRIDE}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Mods
if [ -n "${MOD_IDS}" ]; then
    echo "ark_GameModIds=\"${MOD_IDS}\"" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
fi

# Argumentos Adicionales
if [ -n "${ADDITIONAL_ARGS}" ]; then
    echo "" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "# Argumentos adicionales" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    for arg in ${ADDITIONAL_ARGS}; do
        if [[ $arg == -* ]]; then
            flag="${arg#-}"
            echo "arkflag_${flag}=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
        fi
    done
fi

# Opciones en crudo de ARKMANAGER_OPTS
if [ -n "${ARKMANAGER_OPTS}" ]; then
    echo "" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    echo "# Opciones personalizadas de arkmanager" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    while IFS= read -r line; do
        [ -n "$line" ] && echo "${line}" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
    done <<< "${ARKMANAGER_OPTS}"
fi

# Optimizaciones de rendimiento del motor Unreal Engine en Linux
echo "arkflag_USEALLAVAILABLECORES=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null
echo "arkflag_nostallstartup=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null

# Habilitar logging siempre
echo "arkflag_log=true" | tee -a /etc/arkmanager/arkmanager.cfg > /dev/null

# Configuración de instancia principal
tee /etc/arkmanager/instances/main.cfg > /dev/null << EOF
# Configuración de instancia principal @main
arkserverroot="${ARK_DATA_DIR:-/home/steam/steamcmd/ark}"
arkserverexec="ShooterGame/Binaries/Linux/ShooterGameServer"
EOF

chown -R steam:steam /etc/arkmanager /var/log/arktools 2>/dev/null || true
echo "[ARK Server Manager] Configuración de arkmanager generada correctamente."
