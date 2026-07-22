#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-/home/steam/ark-backups}"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <latest | ruta_o_nombre_de_archivo.tar.bz2>"
    echo ""
    echo "Backups disponibles en $BACKUP_DIR:"
    find "$BACKUP_DIR" -name "*.tar.bz2" -type f -printf "%TY-%Tm-%Td %TH:%TM  %p\n" 2>/dev/null | sort -r || echo "  (No se encontraron archivos .tar.bz2)"
    exit 1
fi

if [ "$BACKUP_FILE" = "latest" ]; then
    BACKUP_PATH=$(find "$BACKUP_DIR" -name "*.tar.bz2" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)
    if [ -z "$BACKUP_PATH" ]; then
        echo "[ERROR] No se encontró ningún backup en $BACKUP_DIR"
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
        # (los backups viven en subcarpetas por fecha)
        BACKUP_PATH=$(find "$BACKUP_DIR" -type f -name "$(basename "$BACKUP_FILE")" 2>/dev/null | head -n 1)
        if [ -z "$BACKUP_PATH" ]; then
            echo "[ERROR] No se encontró el archivo de backup: $BACKUP_FILE"
            exit 1
        fi
    fi
fi

echo "[restore] Guardando el mapa actual y generando un backup de seguridad preventivo..."
arkmanager saveworld @main || true
SAFETY_BACKUP_NAME="pre_restore_safety_$(date +%Y%m%d_%H%M%S)"
echo "[restore] Creando respaldo preventivo: ${SAFETY_BACKUP_NAME}..."
arkmanager backup @main || true

echo "[restore] Deteniendo el servidor de ARK..."
arkmanager stop --saveworld @main || true

echo "[restore] Restaurando backup desde: $BACKUP_PATH..."
arkmanager restore "$BACKUP_PATH" @main || {
    echo "[restore] arkmanager restore no pudo extraer automáticamente. Intentando descompresión directa..."
    SAVED_DIR="/home/steam/steamcmd/ark/ShooterGame/Saved/SavedArks"
    mkdir -p "$SAVED_DIR"
    tar -xjvf "$BACKUP_PATH" -C "$SAVED_DIR"
}

echo "[restore] Restauración completada con éxito."
echo "[restore] Reiniciando el servidor de ARK..."
arkmanager start --noautoupdate @main
echo "[restore] Servidor reiniciado."
