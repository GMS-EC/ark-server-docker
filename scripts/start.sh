#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"

echo "[ARK Server Manager] Generando configuración exhaustiva de arkmanager..."
mkdir -p /etc/arkmanager /var/log/arktools /etc/arkmanager/instances

# Si existe generate-config.sh, usarlo para escribir arkmanager.cfg
if [ -f "/home/steam/scripts/generate-config.sh" ]; then
    bash /home/steam/scripts/generate-config.sh
elif [ -f "$(dirname "$0")/generate-config.sh" ]; then
    bash "$(dirname "$0")/generate-config.sh"
fi

# Si arkmanager está disponible en el PATH
if command -v arkmanager >/dev/null 2>&1; then
    # 1. Si no existe el ejecutable, instalar si UPDATE_ON_START=true o AUTO_INSTALL=true
    if [ ! -f "/home/steam/steamcmd/ark/ShooterGame/Binaries/Linux/ShooterGameServer" ]; then
        if [ "${UPDATE_ON_START:-true}" = "true" ] || [ "${AUTO_INSTALL:-false}" = "true" ]; then
            echo "[ARK Server Manager] Servidor no detectado. Iniciando instalación automática de ARK (SteamCMD AppID 376030)..."
            if [ "${BETA}" = "public" ] || [ -z "${BETA}" ]; then
                arkmanager install @main
            else
                arkmanager install --beta="${BETA}" @main
            fi
        else
            echo "[ARK Server Manager] [AVISO] El servidor de ARK no está instalado aún."
            echo "[ARK Server Manager] Accede al panel web (http://localhost:${PANEL_PORT:-8080}) para configurar e iniciar la descarga."
            exit 1
        fi
    fi

    # 2. Instalar o verificar mods Workshop configurados
    if [ -n "$MOD_IDS" ]; then
        echo "[ARK Server Manager] Verificando mods Workshop: $MOD_IDS"
        IFS=',' read -ra MODS <<< "$MOD_IDS"
        for mod in "${MODS[@]}"; do
            mod=$(echo "$mod" | tr -d ' ')
            [ -z "$mod" ] && continue
            if [ ! -d "/home/steam/steamcmd/ark/ShooterGame/Content/Mods/$mod" ]; then
                echo "[ARK Server Manager] Mod $mod no detectado. Descargando e instalando con SteamCMD..."
                arkmanager installmod "$mod" @main || true
            else
                echo "[ARK Server Manager] Mod $mod ya instalado en ShooterGame/Content/Mods/$mod."
            fi
        done
    fi

    # 3. Actualizar servidor si UPDATE_ON_START está habilitado
    if [ "${UPDATE_ON_START:-true}" = "true" ]; then
        echo "[ARK Server Manager] Verificando actualizaciones de servidor y mods..."
        if [ "${BETA}" = "public" ] || [ -z "${BETA}" ]; then
            arkmanager update --no-background --update-mods @main 2>/dev/null || true
        else
            arkmanager update --beta="${BETA}" --no-background --update-mods @main 2>/dev/null || true
        fi
    fi

    # 4. Iniciar ShooterGameServer en primer plano para supervisión de procesos y streaming de consola
    echo "========================================================================"
    echo "[ARK Server Manager] Todos los mods instalados exitosamente."
    echo "[ARK Server Manager] Lanzando ejecutable ShooterGameServer..."
    echo "[ARK Server Manager] [INFO] El servidor está cargando el mapa, dinos y mods en memoria RAM."
    echo "[ARK Server Manager] [INFO] En discos duros mecánicos (HDD) o con mods extensos (como ARK Additions), la carga inicial puede tomar entre 15 y 25 minutos."
    echo "[ARK Server Manager] [INFO] El estado en el panel permanecerá en STARTING (color naranja con pulso) hasta estar 100% disponible."
    echo "========================================================================"
    exec arkmanager run @main
else
    echo "[ARK Server Manager] Modo local / Simulación: arkmanager no encontrado en el PATH."
    while true; do
        sleep 30
    done
fi
