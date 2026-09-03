#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"
set -e

BACKUP_DIR="${BACKUP_DIR:-/home/steam/ark-backups}"
ARK_ROOT="${ARK_ROOT:-/home/steam/steamcmd/ark}"
SHOOTER_DIR="$ARK_ROOT/ShooterGame"
SAVED_DIR="$SHOOTER_DIR/Saved"
SAVED_ARKS_DIR="$SAVED_DIR/SavedArks"
CONFIG_DIR="$SAVED_DIR/Config/LinuxServer"
BACKUP_FILE="$1"

# Cargar helper de Discord si existe
if [ -f "/home/steam/scripts/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "/home/steam/scripts/discord.sh"
elif [ -f "$(dirname "$0")/discord.sh" ]; then
    # shellcheck source=/dev/null
    source "$(dirname "$0")/discord.sh"
fi

if [ -z "$BACKUP_FILE" ]; then
    echo "================================================================="
    echo "  🔄 Utilidad de Restauración de Copias de Seguridad de ARK"
    echo "================================================================="
    echo "Uso: $0 <latest | nombre_o_ruta_de_archivo.tar.bz2>"
    echo ""
    echo "Backups disponibles en $BACKUP_DIR:"
    find "$BACKUP_DIR" -name "*.tar.bz2" -type f -printf "%TY-%Tm-%Td %TH:%TM  %p\n" 2>/dev/null | sort -r || echo "  (No se encontraron archivos .tar.bz2)"
    echo "================================================================="
    exit 1
fi

if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_PATH=$(find "$BACKUP_DIR" -name "*.tar.bz2" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)
    if [ -z "$BACKUP_PATH" ]; then
        echo "[ERROR] No se encontró ningún archivo de backup en $BACKUP_DIR"
        exit 1
    fi
    echo "[restore] Usando el backup más reciente: $BACKUP_PATH"
else
    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_PATH="$BACKUP_FILE"
    elif [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"
    else
        # Buscar recursivamente por si solo se dio el nombre base
        BACKUP_PATH=$(find "$BACKUP_DIR" -type f -name "$(basename "$BACKUP_FILE")" 2>/dev/null | head -n 1)
        if [ -z "$BACKUP_PATH" ]; then
            echo "[ERROR] No se encontró el archivo de backup: $BACKUP_FILE"
            exit 1
        fi
    fi
fi

echo "[restore] Guardando el mapa actual y generando un backup de seguridad preventivo..."
arkmanager saveworld @main 2>/dev/null || true
SAFETY_NAME="pre_restore_safety_$(date +%Y%m%d_%H%M%S)"

if [ -f "/home/steam/scripts/backup.sh" ]; then
    echo "[restore] Creando respaldo preventivo estructurado: ${SAFETY_NAME}..."
    bash /home/steam/scripts/backup.sh "$SAFETY_NAME" || true
else
    echo "[restore] Creando respaldo preventivo con arkmanager..."
    arkmanager backup @main || true
fi

echo "[restore] Deteniendo el servidor de ARK..."
arkmanager stop --saveworld @main || true

echo "[restore] Analizando formato de la copia de seguridad: $BACKUP_PATH..."

# Inspeccionar estructura interna del tarball
ARCHIVE_CONTENTS=$(tar -tf "$BACKUP_PATH" 2>/dev/null || true)

if echo "$ARCHIVE_CONTENTS" | grep -qE "(^\./Saved/|^Saved/)"; then
    echo "[restore] Detectado FORMATO ORGANIZADO (conserva carpetas Saved/SavedArks y Saved/Config)..."
    mkdir -p "$SHOOTER_DIR"
    tar -xjvf "$BACKUP_PATH" -C "$SHOOTER_DIR"
    echo "[restore] Archivos estructurados extraídos directamente en $SHOOTER_DIR/Saved"
else
    echo "[restore] Detectado FORMATO LEGADO (archivos sueltos sin jerarquía)..."
    echo "[restore] Probando restauración interna con arkmanager..."
    if ! arkmanager restore "$BACKUP_PATH" @main; then
        echo "[restore] arkmanager restore no pudo extraer automáticamente."
        echo "[restore] Realizando separación inteligente de archivos sueltos..."
        
        TEMP_RESTORE=$(mktemp -d /tmp/ark_restore_legacy_XXXXXX)
        tar -xjvf "$BACKUP_PATH" -C "$TEMP_RESTORE"
        mkdir -p "$SAVED_ARKS_DIR" "$CONFIG_DIR"

        # 1. Copiar mapas, jugadores y tribus a SavedArks
        find "$TEMP_RESTORE" -type f \( -name "*.ark" -o -name "*.arkprofile" -o -name "*.arktribe" -o -name "*.profilebak" -o -name "*.tribebak" \) -exec cp -fp {} "$SAVED_ARKS_DIR/" \;
        echo "[restore] Mapa, personajes y tribus colocados en: $SAVED_ARKS_DIR"

        # 2. Copiar archivos .ini a Config/LinuxServer
        find "$TEMP_RESTORE" -type f \( -name "Game.ini" -o -name "GameUserSettings.ini" \) -exec cp -fp {} "$CONFIG_DIR/" \;
        echo "[restore] Configuraciones (.ini) colocadas en: $CONFIG_DIR"

        # 3. Copiar subcarpeta SaveGames si existe
        if [ -d "$TEMP_RESTORE/SaveGames" ]; then
            mkdir -p "$SAVED_DIR/SaveGames"
            cp -rfp "$TEMP_RESTORE/SaveGames/"* "$SAVED_DIR/SaveGames/" 2>/dev/null || true
            echo "[restore] Datos de SaveGames colocados en: $SAVED_DIR/SaveGames"
        fi

        rm -rf "$TEMP_RESTORE"
    fi
fi

# Corregir permisos en los datos restaurados
chown -R steam:steam "$SAVED_DIR" 2>/dev/null || true

echo "[restore] Restauración completada con éxito."
echo "[restore] Reiniciando el servidor de ARK..."
arkmanager start --noautoupdate @main
echo "[restore] Servidor reiniciado correctamente."

# Notificar a Discord la restauración exitosa
if command -v send_discord_embed >/dev/null 2>&1; then
    _LANG="${DISCORD_LANGUAGE:-es}"
    _FILE_NAME=$(basename "$BACKUP_PATH")
    if [ "$_LANG" = "en" ]; then
        _DISCORD_MSG="Server save successfully restored from backup: \`${_FILE_NAME}\`. ARK server restarted and online."
    else
        _DISCORD_MSG="Servidor de ARK restaurado exitosamente desde la copia: \`${_FILE_NAME}\`. Servidor reiniciado y online."
    fi
    send_discord_embed "RESTORE_OK" "$_DISCORD_MSG"
fi

exit 0
