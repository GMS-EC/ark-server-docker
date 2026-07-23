<div align="center">
  <h1>🛠️ Guía de Administración del Servidor / Server Management Guide</h1>
  <p>
    <b>Select Language / Selecciona Idioma:</b><br>
    <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
  </p>
</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### 🛠️ Guía de Administración del Servidor

Esta guía cubre las operaciones diarias de mantenimiento, gestión de respaldos, restauración en un clic, alertas a Discord y reinicios automáticos.

---

#### 💻 1. Comandos Frecuentes con `arkmanager`

El contenedor incluye [ARK Server Tools (`arkmanager`)](https://github.com/arkmanager/ark-server-tools) preinstalado. Puedes consultar la [documentación completa de comandos de arkmanager](https://github.com/arkmanager/ark-server-tools#usage) o ejecutar cualquiera de los comandos administrativos más frecuentes directamente con `docker exec`:

##### Comandos de Consola Útiles:

* **Ver el estado detallado del servidor (Jugadores conectados, versión, memoria):**
  ```bash
  docker exec -u steam ark-server arkmanager status @main
  ```

* **Enviar un mensaje global al chat del juego (Broadcast):**
  ```bash
  docker exec -u steam ark-server arkmanager broadcast "El servidor entrará en mantenimiento en 10 minutos" @main
  ```

* **Forzar un guardado inmediato del mundo:**
  ```bash
  docker exec -u steam ark-server arkmanager saveworld @main
  ```

* **Forzar una copia de seguridad manual:**
  ```bash
  docker exec -u steam ark-server arkmanager backup @main
  ```

* **Actualizar el servidor de ARK y sus Mods instalados:**
  ```bash
  docker exec -u steam ark-server arkmanager update --update-mods @main
  ```

* **Reiniciar el servidor de forma segura con aviso de 15 minutos:**
  ```bash
  docker exec -u steam ark-server arkmanager restart --warn @main
  ```

---

#### 📦 2. Sistema de Respaldos (Backups Automáticos)

Configuración en `.env`:
```bash
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=6
BACKUP_DIR=/home/steam/ark-backups
BACKUP_MAX_COUNT=10
```

##### Características del Sistema de Backup:
1. **Guardado Preventivo (`saveworld`)**: El contenedor fuerza la grabación del mapa a disco antes de crear cada comprimido `.tar.bz2`.
2. **Rotación Inteligente por Cantidad (`BACKUP_MAX_COUNT`)**: Conserva únicamente los `N` respaldos más recientes y borra los más antiguos automáticamente.
3. **Persistencia en el Host**: Las copias se guardan en `./ark-backups/` en tu PC.

> [!TIP]
> **Recomendación sobre `BACKUP_MAX_COUNT`:** Dejar `BACKUP_MAX_COUNT` vacío o en `0` conserva todos los respaldos indefinidamente, lo cual en un servidor de larga duración puede llenar el disco con el tiempo. Con `BACKUP_INTERVAL_HOURS=6` (4 backups/día), un valor de `BACKUP_MAX_COUNT=20` conserva aproximadamente 5 días de historial de respaldos sin acumular espacio indefinidamente.

---

#### 🔄 3. Guía de Restauración con `restore.sh`

Para restaurar un mapa desde un backup:

##### Paso 1: Abrir la terminal dentro del contenedor
```bash
docker exec -it ark-server bash
```

##### Paso 2: Ejecutar el script de restauración
- **Para restaurar el respaldo más reciente:**
  ```bash
  /home/steam/scripts/restore.sh latest
  ```
- **Para restaurar un respaldo específico:**
  ```bash
  /home/steam/scripts/restore.sh main.2026-07-22_15.30.00.tar.bz2
  ```

> [!TIP]
> **Salvaguarda Automática:** `restore.sh` genera automáticamente una copia preventivo llamada `pre_restore_safety_...` antes de descompprimir, por lo que nunca perderás el progreso actual.

---

#### 🔔 4. Notificaciones Webhook a Discord

Agrega tu URL de Webhook y el idioma deseado a `.env`:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/TU_WEBHOOK_ID/TU_WEBHOOK_TOKEN
DISCORD_LANGUAGE=es # Opciones: "es" (Español, por defecto) o "en" (Inglés)
```

Recibirás notificaciones automáticas para:
- Inicio y apagado del servidor.
- Éxito o falla en los backups.
- Procesos de reinicio programados.

---

#### ⏰ 5. Reinicios Programados (`AUTO_RESTART_HOURS`)

Configura `AUTO_RESTART_HOURS=24` en tu `.env` para reiniciar el servidor cada 24 horas con advertencias in-game (15m, 10m, 5m, 1m) y guardado automático previo.

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to expand / collapse)</h2></summary>

### 🛠️ Server Management Guide

This guide covers daily maintenance, backup management, one-click restoration, Discord notifications, and scheduled server restarts.

---

#### 💻 1. Common `arkmanager` Commands

The container includes [ARK Server Tools (`arkmanager`)](https://github.com/arkmanager/ark-server-tools) pre-installed. You can consult the [full arkmanager command usage documentation](https://github.com/arkmanager/ark-server-tools#usage) or execute common admin commands directly using `docker exec`:

* **Check detailed server status (connected players, version, RAM usage):**
  ```bash
  docker exec -u steam ark-server arkmanager status @main
  ```

* **Broadcast an in-game global chat message:**
  ```bash
  docker exec -u steam ark-server arkmanager broadcast "Server maintenance in 10 minutes" @main
  ```

* **Force an immediate world save:**
  ```bash
  docker exec -u steam ark-server arkmanager saveworld @main
  ```

* **Force a manual backup:**
  ```bash
  docker exec -u steam ark-server arkmanager backup @main
  ```

* **Update ARK server files and installed Mods:**
  ```bash
  docker exec -u steam ark-server arkmanager update --update-mods @main
  ```

* **Restart server gracefully with a 15-minute warning:**
  ```bash
  docker exec -u steam ark-server arkmanager restart --warn @main
  ```

---

#### 📦 2. Automated Backup System

`.env` Settings:
```bash
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=6
BACKUP_DIR=/home/steam/ark-backups
BACKUP_MAX_COUNT=10
```

##### Key Backup Features:
1. **Pre-Backup Saveworld**: Forces in-memory world save prior to creating `.tar.bz2` archives.
2. **Count-Based Rotation (`BACKUP_MAX_COUNT`)**: Retains only the `N` most recent backups.
3. **Host Persistence**: Stored in `./ark-backups/` on your host PC.

> [!TIP]
> **Recommendation for `BACKUP_MAX_COUNT`:** Leaving `BACKUP_MAX_COUNT` empty or set to `0` retains all backups indefinitely, which on long-running servers can fill up disk space over time. With `BACKUP_INTERVAL_HOURS=6` (4 backups/day), setting `BACKUP_MAX_COUNT=20` retains approximately 5 days of backup history without accumulating unlimited disk usage.

---

#### 🔄 3. Restoration Guide using `restore.sh`

##### Step 1: Open a terminal inside the container
```bash
docker exec -it ark-server bash
```

##### Step 2: Run the restoration script
- **To restore the latest backup:**
  ```bash
  /home/steam/scripts/restore.sh latest
  ```
- **To restore a specific backup:**
  ```bash
  /home/steam/scripts/restore.sh main.2026-07-22_15.30.00.tar.bz2
  ```

> [!TIP]
> **Safety Safeguard:** `restore.sh` automatically creates a safety backup named `pre_restore_safety_...` prior to restoring.

---

#### 🔔 4. Discord Webhook Notifications

Set `DISCORD_WEBHOOK_URL` and `DISCORD_LANGUAGE` in `.env`:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
DISCORD_LANGUAGE=es # Options: "es" (Spanish, default) or "en" (English)
```

---

#### ⏰ 5. Scheduled Restarts (`AUTO_RESTART_HOURS`)

Set `AUTO_RESTART_HOURS=24` in `.env` for periodic restarts with 15m, 10m, 5m, 1m in-game warnings and pre-save.

</details>
