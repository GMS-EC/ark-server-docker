#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"
set -e

BACKUP_DIR="${BACKUP_DIR:-/home/steam/ark-backups}"
ARK_ROOT="${ARK_ROOT:-/home/steam/steamcmd/ark}"
SHOOTER_DIR="$ARK_ROOT/ShooterGame"
SAVED_DIR="$SHOOTER_DIR/Saved"
SAVED_ARKS_DIR="$SAVED_DIR/SavedArks"
CONFIG_DIR="$SAVED_DIR/Config/LinuxServer"
SAVEGAMES_DIR="$SAVED_DIR/SaveGames"
WORLD="${WORLD:-TheIsland}"
BACKUP_MAX_COUNT="${BACKUP_MAX_COUNT:-10}"
CUSTOM_PREFIX="$1"

# Cargar helper de Discord si existe
if [ -f "/home/steam/scripts/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "/home/steam/scripts/discord.sh"
elif [ -f "$(dirname "$0")/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "$(dirname "$0")/discord.sh"
fi

echo "[backup] Iniciando proceso de copia de seguridad organizada..."

# 1. Guardar el estado del mundo en memoria a disco
if command -v arkmanager >/dev/null 2>&1; then
    echo "[backup] Forzando guardado del mundo (saveworld)..."
    arkmanager saveworld @main 2>/dev/null || true
    sleep 2
fi

# 2. Verificar que existan carpetas de guardado
if [ ! -d "$SAVED_ARKS_DIR" ]; then
    echo "[backup] ADVERTENCIA: No se encontró el directorio $SAVED_ARKS_DIR. No hay datos de juego activos."
    exit 1
fi

# 3. Crear directorio temporal de empaquetado estructurado
STAGING_DIR=$(mktemp -d /tmp/ark_backup_staging_XXXXXX)
trap 'rm -rf "$STAGING_DIR"' EXIT

TARGET_SAVED="$STAGING_DIR/Saved"
TARGET_ARKS="$TARGET_SAVED/SavedArks"
TARGET_CONFIG="$TARGET_SAVED/Config/LinuxServer"
TARGET_SAVEGAMES="$TARGET_SAVED/SaveGames"

mkdir -p "$TARGET_ARKS" "$TARGET_CONFIG"

# 4. Copiar archivos del mapa y partidas activas a Saved/SavedArks/
echo "[backup] Copiando archivos de partida activa (mapa, jugadores y tribus)..."
# Copiar mapa principal si existe
if [ -f "$SAVED_ARKS_DIR/${WORLD}.ark" ]; then
    cp -p "$SAVED_ARKS_DIR/${WORLD}.ark" "$TARGET_ARKS/"
fi

# Copiar otros mapas activos si existen, omitiendo autoguardados periódicos (TheIsland_DD.MM.YYYY_...)
find "$SAVED_ARKS_DIR" -maxdepth 1 -name "*.ark" ! -name "*_*.*.*.ark" -exec cp -p {} "$TARGET_ARKS/" \; 2>/dev/null || true

# Copiar perfiles de jugador y tribus
find "$SAVED_ARKS_DIR" -maxdepth 1 -name "*.arkprofile" -exec cp -p {} "$TARGET_ARKS/" \; 2>/dev/null || true
find "$SAVED_ARKS_DIR" -maxdepth 1 -name "*.arktribe" -exec cp -p {} "$TARGET_ARKS/" \; 2>/dev/null || true

# 5. Copiar archivos de configuración a Saved/Config/LinuxServer/
echo "[backup] Copiando configuraciones (.ini)..."
if [ -f "$CONFIG_DIR/Game.ini" ]; then
    cp -p "$CONFIG_DIR/Game.ini" "$TARGET_CONFIG/"
fi
if [ -f "$CONFIG_DIR/GameUserSettings.ini" ]; then
    cp -p "$CONFIG_DIR/GameUserSettings.ini" "$TARGET_CONFIG/"
fi

# 6. Copiar datos de SaveGames o Clusters si existen
if [ -d "$SAVEGAMES_DIR" ] && [ "$(ls -A "$SAVEGAMES_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_SAVEGAMES"
    cp -rp "$SAVEGAMES_DIR/"* "$TARGET_SAVEGAMES/" 2>/dev/null || true
fi

if [ -n "$CLUSTER_DIR_OVERRIDE" ] && [ -d "$CLUSTER_DIR_OVERRIDE" ]; then
    TARGET_CLUSTER="$STAGING_DIR/clusters"
    mkdir -p "$TARGET_CLUSTER"
    cp -rp "$CLUSTER_DIR_OVERRIDE/"* "$TARGET_CLUSTER/" 2>/dev/null || true
fi

# 7. Crear guías de restauración rápida dentro del propio archivo de backup
cat << 'EOF' > "$STAGING_DIR/LEEME_RESTAURACION.txt"
================================================================================
          📦 COPIA DE SEGURIDAD ORGANIZADA DE ARK: SURVIVAL EVOLVED
================================================================================

Esta copia de seguridad conserva la estructura nativa de directorios de ARK:

ESTRUCTURA DEL BACKUP:
--------------------------------------------------------------------------------
Saved/
  ├── SavedArks/
  │   ├── <Mapa>.ark           (Estado del mundo, estructuras y dinosaurios)
  │   ├── *.arkprofile         (Perfiles de jugadores, nivel e inventario)
  │   └── *.arktribe           (Datos de tribus y propietarios)
  ├── Config/
  │   └── LinuxServer/
  │       ├── Game.ini         (Configuraciones avanzadas de juego)
  │       └── GameUserSettings.ini (Configuración principal del servidor)
  └── SaveGames/               (Datos adicionales o clusters)

--------------------------------------------------------------------------------
¿CÓMO RESTAURAR ESTA COPIA?
--------------------------------------------------------------------------------

MÉTODO 1: AUTOMATIZADO CON RESTORE.SH (RECOMENDADO)
--------------------------------------------------
1. Coloca el archivo .tar.bz2 en la carpeta ./ark-backups/ de tu servidor.
2. Ejecuta en tu terminal:
   docker exec -it ark-server /home/steam/scripts/restore.sh nombre_del_backup.tar.bz2
   (O simplemente: docker exec -it ark-server /home/steam/scripts/restore.sh latest)

MÉTODO 2: MANUAL POR SFTP (FILEZILLA / WINSCP)
--------------------------------------------------
1. ¡DETÉN EL CONTENEDOR ANTES DE TOCAR ARCHIVOS!:
   docker compose stop
2. Arrastra la carpeta "Saved" directamente a:
   .../ShooterGame/ (reemplazando la carpeta Saved existente).
   ¡Todo irá a su lugar exacto automáticamente!
3. Vuelve a iniciar el contenedor:
   docker compose start
================================================================================
EOF

cat << 'EOF' > "$STAGING_DIR/README_RESTORATION.txt"
================================================================================
          📦 ORGANIZED ARK: SURVIVAL EVOLVED BACKUP ARCHIVE
================================================================================

This backup maintains ARK's native directory structure for hassle-free restoration:

ARCHIVE STRUCTURE:
--------------------------------------------------------------------------------
Saved/
  ├── SavedArks/
  │   ├── <Map>.ark            (World state, structures, and wild/tamed dinos)
  │   ├── *.arkprofile         (Player profiles, levels, and personal inventory)
  │   └── *.arktribe           (Tribe data, ownership, and logs)
  ├── Config/
  │   └── LinuxServer/
  │       ├── Game.ini         (Advanced game and rate configurations)
  │       └── GameUserSettings.ini (Server settings and rules)
  └── SaveGames/               (Additional cluster/tribute data)

--------------------------------------------------------------------------------
HOW TO RESTORE THIS BACKUP:
--------------------------------------------------------------------------------

METHOD 1: AUTOMATED RESTORATION (RECOMMENDED)
---------------------------------------------
1. Place this .tar.bz2 file in your server's ./ark-backups/ folder.
2. Run in your terminal:
   docker exec -it ark-server /home/steam/scripts/restore.sh backup_filename.tar.bz2
   (Or simply: docker exec -it ark-server /home/steam/scripts/restore.sh latest)

METHOD 2: MANUAL SFTP (FILEZILLA / WINSCP)
------------------------------------------
1. STOP THE CONTAINER FIRST:
   docker compose stop
2. Drag the extracted "Saved" folder directly into:
   .../ShooterGame/ (overwrite existing files).
   Everything lands in its exact directory automatically!
3. Start the container:
   docker compose start
================================================================================
EOF

# 8. Comprimir archivo final
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date '+%Y-%m-%d_%H.%M.%S')

if [ -n "$CUSTOM_PREFIX" ]; then
    BACKUP_FILENAME="${CUSTOM_PREFIX}.tar.bz2"
else
    BACKUP_FILENAME="main.${TIMESTAMP}.tar.bz2"
fi

BACKUP_OUTPUT_PATH="$BACKUP_DIR/$BACKUP_FILENAME"

echo "[backup] Creando archivo comprimido: $BACKUP_OUTPUT_PATH..."
tar -cjf "$BACKUP_OUTPUT_PATH" -C "$STAGING_DIR" .

echo "[backup] Copia de seguridad generada con éxito ($(du -h "$BACKUP_OUTPUT_PATH" | cut -f1))"

# 9. Rotación de copias por conteo
if [ -n "$BACKUP_MAX_COUNT" ] && [ "$BACKUP_MAX_COUNT" -gt 0 ]; then
    COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.bz2" -type f 2>/dev/null | wc -l)
    if [ "$COUNT" -gt "$BACKUP_MAX_COUNT" ]; then
        echo "[backup] Rotando respaldos (conservando los $BACKUP_MAX_COUNT más recientes de $COUNT)..."
        find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.bz2" -type f -printf "%T@ %p\n" 2>/dev/null | \
            sort -rn | cut -d' ' -f2- | tail -n +$(( BACKUP_MAX_COUNT + 1 )) | while read -r OLD_FILE; do
                if [ -f "$OLD_FILE" ]; then
                    echo "[backup] Eliminando respaldo antiguo: $OLD_FILE"
                    rm -f "$OLD_FILE"
                fi
            done
    fi
fi

# 10. Enviar notificación a Discord si fue ejecutado manualmente (fuera del loop de start.sh)
if [ "${IS_SCHEDULED:-false}" != "true" ] && command -v send_discord_embed >/dev/null 2>&1; then
    _LANG="${DISCORD_LANGUAGE:-es}"
    _FILE_SIZE=$(du -h "$BACKUP_OUTPUT_PATH" 2>/dev/null | cut -f1)
    if [ "$_LANG" = "en" ]; then
        _DISCORD_MSG="Manual backup created successfully: \`${BACKUP_FILENAME}\` (${_FILE_SIZE})."
    else
        _DISCORD_MSG="Copia de seguridad manual creada exitosamente: \`${BACKUP_FILENAME}\` (${_FILE_SIZE})."
    fi
    send_discord_embed "BACKUP_MANUAL" "$_DISCORD_MSG"
fi

echo "[backup] Proceso finalizado exitosamente."
exit 0
