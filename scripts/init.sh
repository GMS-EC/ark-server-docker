#!/bin/bash
set -e

# Mostrar branding si existe
[ -f /branding ] && cat /branding 2>/dev/null || true

echo "================================================="
echo "       Iniciando ARK Server Manager - Panel & Servidor      "
echo "================================================="

# Configurar PUID y PGID si se especifican
if [ -n "${PUID}" ] && [ -n "${PGID}" ]; then
    echo "[ARK Server Manager] Configurando usuario steam con UID:${PUID} y GID:${PGID}"
    usermod -o -u "${PUID}" steam 2>/dev/null || true
    groupmod -o -g "${PGID}" steam 2>/dev/null || true
fi

# Crear directorios necesarios y ajustar permisos de forma inmediata sin recorrer recursivamente decenas de GBs
mkdir -p /etc/arkmanager /var/log/arktools /home/steam/steamcmd/ark /home/steam/ark-backups /home/steam/clusters /app/data
chown steam:steam /home/steam /home/steam/steamcmd 2>/dev/null || true
chown -R steam:steam /var/log/arktools /etc/arkmanager /app /home/steam/ark-backups /home/steam/clusters /app/data 2>/dev/null || true

# Solo si la raíz del juego no pertenece al usuario steam (o PUID), sincronizar permisos
if [ -d "/home/steam/steamcmd/ark" ] && [ "$(stat -c '%u' /home/steam/steamcmd/ark 2>/dev/null)" != "${PUID:-1000}" ]; then
    echo "[ARK Server Manager] Sincronizando permisos en datos de juego..."
    chown -R steam:steam /home/steam/steamcmd/ark 2>/dev/null || true
fi

# Configurar Timezone del sistema desde la variable TZ
if [ -n "${TZ}" ] && [ -f "/usr/share/zoneinfo/${TZ}" ]; then
    echo "[ARK Server Manager] Configurando zona horaria del contenedor: ${TZ}"
    ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime
    echo "${TZ}" > /etc/timezone
fi

# Generar configuración de arkmanager desde variables de entorno
if [ -f "/home/steam/scripts/generate-config.sh" ]; then
    bash /home/steam/scripts/generate-config.sh
fi

# Capturar señales SIGTERM y SIGINT para apagado seguro de servidores
trap 'su - steam -c "arkmanager stop --saveworld @all" 2>/dev/null || true; exit 0' SIGTERM SIGINT

export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"

# Arrancar el panel web de ARK Server Manager (FastAPI + Uvicorn) como usuario steam
echo "[ARK Server Manager] Lanzando panel web en puerto ${PANEL_PORT:-8080}..."
cd /app
exec su -s /bin/bash steam -c "export PATH=\"/usr/local/bin:/usr/bin:/bin:/home/steam/bin:\$PATH\"; exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port \"${PANEL_PORT:-8080}\""
