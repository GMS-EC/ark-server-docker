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

#### ⏰ 5. Reinicios Programados vs. Horario Automático de Encendido/Apagado

Es importante entender la diferencia entre ambas funciones y cuándo utilizar cada una:

| Función | Variable | Propósito | Comportamiento | Casos de Uso Recomendados |
|---------|----------|-----------|----------------|---------------------------|
| **Reinicios Programados** | `AUTO_RESTART_HOURS` | Liberar memoria RAM, prevenir lag por uso prolongado y aplicar parches de mods. | Reinicia periódicamente el proceso del servidor activo (ej. cada 24h u 48h) enviando avisos in-game previamente. | Servidores activos 24/7 o abiertos muchas horas al día. |
| **Horario de Encendido/Apagado** | `SCHEDULE_ENABLED` | Ahorrar procesamiento (CPU) y memoria (RAM) en el equipo host. | Apaga el proceso del servidor (`ShooterGameServer`) fuera del horario y lo enciende automáticamente al entrar en el horario. | Servidores privados, de amigos o clanes con horas de juego definidas (ej. 20:00 a 02:00). |

##### 💡 ¿Qué ocurre si coinciden ambas funciones?
Si tienes ambas opciones activas (ej. `AUTO_RESTART_HOURS=48` y `SCHEDULE_ENABLED=true`) y la hora de reinicio cae **fuera del horario de juego** (cuando el servidor está apagado):
- **Omisión Inteligente:** El sistema detecta automáticamente que el servidor se encuentra apagado por horario y **omite el reinicio**, reiniciando el contador del temporizador.
- **Sin falsos encendidos:** Esto evita que el servidor se encienda accidentalmente en la madrugada solo para cumplir con un ciclo de reinicio.

---

#### ⏰ 6. Configuración del Horario Automático (`SCHEDULE_ENABLED`)

Permite apagar y encender automáticamente el **proceso** del servidor de ARK (mientras el contenedor Docker sigue corriendo en segundo plano) para ahorrar CPU y memoria RAM cuando nadie está jugando.

Configuración en `.env`:
```bash
SCHEDULE_ENABLED=true       # Valor por defecto: false (requiere establecerse en true)
SCHEDULE_START=20:00        # Valor por defecto: "20:00"
SCHEDULE_STOP=02:00         # Valor por defecto: "00:00"
TZ=America/Guayaquil        # Valor por defecto: UTC
SCHEDULE_WARN_MINUTES=10    # Valor por defecto: 10
```

##### Características del Horario Automático:
1. **Ahorro de Recursos**: Ejecuta `arkmanager stop @main` fuera del horario y `arkmanager start @main` dentro del horario.
2. **Soporte para Ventanas Nocturnas**: Soporta horarios que cruzan la medianoche (ej. de 20:00 a 00:00 o 02:00).
3. **Protección de Jugadores Activos**: Si llega la hora de apagado pero hay 1 o más jugadores conectados, el servidor **no se apaga** y pospone la verificación hasta que todos se desconecten.
4. **Advertencias Previas**: Envía una alerta in-game y notificación a Discord `SCHEDULE_WARN_MINUTES` minutos antes de apagar.
5. **Zona Horaria (`TZ`)**: Respeta la zona horaria del usuario configurada en `TZ` (ej. `America/Guayaquil`, `Europe/Madrid`).

---

#### 🩺 7. Diagnóstico y Ajuste de Salud (`HEALTHCHECK`)

El comprobador de salud integrado verifica periódicamente que el proceso de ARK y los puertos de red estén respondiendo.

##### ⚠️ Servidores en Disco Duro Mecánico (HDD) o con Mods Pesados:
Si tu servidor se ejecuta desde un disco HDD mecánico o tiene varios mods de Steam instalados, la carga inicial puede tardar entre **15 y 25 minutos**.
- Durante la carga, Docker puede mostrar temporalmente el estado en **rojo (unhealthy)** si el período de inicio (`start_period`) es inferior a lo que tarda el disco en leer los archivos.
- **Solución:** Agrega o ajusta la sección `healthcheck` en tu `docker-compose.yml` (o en CasaOS / Portainer) para otorgar un período de inicio más holgado:

```yaml
    healthcheck:
      test: ["CMD", "/home/steam/scripts/healthcheck.sh"]
      interval: 1m
      timeout: 30s
      retries: 5
      start_period: 25m
```

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

#### ⏰ 5. Scheduled Restarts vs. Automatic Power Schedule

It is important to understand the difference between both features and when to use each:

| Feature | Variable | Purpose | Behavior | Recommended Use Cases |
|---------|----------|---------|----------|-----------------------|
| **Scheduled Restarts** | `AUTO_RESTART_HOURS` | Free RAM memory, prevent long-term lag, and apply mod patches. | Periodically restarts the running server process (e.g. every 24h or 48h) with in-game advance warnings. | Servers running 24/7 or active for many hours a day. |
| **Power Schedule** | `SCHEDULE_ENABLED` | Save host CPU and RAM resources during off-peak hours. | Stops the game process (`ShooterGameServer`) outside schedule and automatically starts it during schedule. | Private servers, friend groups, or small clans with defined playing hours (e.g., 20:00 to 02:00). |

##### 💡 What happens if both features overlap?
If both options are active (e.g. `AUTO_RESTART_HOURS=48` and `SCHEDULE_ENABLED=true`) and the restart interval triggers **outside scheduled playing hours** (when the server process is stopped):
- **Smart Skip:** The system automatically detects that the server is off due to schedule and **skips the restart**, resetting the timer count.
- **No Unintended Power-Ons:** This prevents the server from accidentally waking up in the middle of the night just to perform a restart cycle.

---

#### ⏰ 6. Power Schedule Setup (`SCHEDULE_ENABLED`)

Allows automatically starting and stopping the ARK server **process** (while the Docker container continues running in background) to save CPU and RAM resources during off-peak hours.

`.env` Configuration:
```bash
SCHEDULE_ENABLED=true       # Default: false (must be set to true to enable)
SCHEDULE_START=20:00        # Default: "20:00"
SCHEDULE_STOP=02:00         # Default: "00:00"
TZ=America/Guayaquil        # Default: UTC
SCHEDULE_WARN_MINUTES=10    # Default: 10
```

##### Key Power Schedule Features:
1. **Resource Saving**: Runs `arkmanager stop @main` during off-hours and `arkmanager start @main` during active hours.
2. **Midnight-Crossing Windows**: Fully supports schedules spanning across midnight (e.g., 20:00 to 00:00 or 02:00).
3. **Active Player Protection**: If shutdown time arrives while 1 or more players are online, the server **postpones shutdown** until all players disconnect.
4. **Advance Warning**: Sends in-game chat broadcasts and Discord alerts `SCHEDULE_WARN_MINUTES` minutes before shutting down.
5. **Timezone Aware (`TZ`)**: Evaluates schedule times based on the container's configured `TZ` variable (e.g., `America/Guayaquil`, `Europe/Madrid`).

---

#### 🩺 7. Healthcheck Diagnostics & Tuning (`HEALTHCHECK`)

The built-in health check periodically verifies that the ARK process and network query ports are responding.

##### ⚠️ Mechanical Hard Drives (HDD) or Heavy Mod Packs:
If your server runs on a mechanical HDD or loads multiple Steam Workshop mods, initial startup can take **15 to 25 minutes**.
- During startup, Docker might temporarily mark the container status as **unhealthy** if the `start_period` is shorter than the disk read time.
- **Solution:** Add or customize the `healthcheck` section in your `docker-compose.yml` (or in CasaOS / Portainer settings) to grant a generous start period:

```yaml
    healthcheck:
      test: ["CMD", "/home/steam/scripts/healthcheck.sh"]
      interval: 1m
      timeout: 30s
      retries: 5
      start_period: 25m
```

</details>
