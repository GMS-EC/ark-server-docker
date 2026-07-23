<div align="center">

<table border="0">
  <tr>
    <td align="center" width="170" valign="middle">
      <img src="https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png" width="150" alt="ARK Server Docker Logo">
    </td>
    <td align="left" valign="middle">
      <h2 align="left">🦖 ARK: Survival Evolved — Dedicated Server in Docker</h2>
      <p align="left"><b>Contenedor optimizado y automatizado para servidores dedicados de ARK utilizando <code>arkmanager</code></b></p>
      <p align="left">
        <a href="https://hub.docker.com/r/marcusm99/ark-server-docker"><img src="https://img.shields.io/docker/v/marcusm99/ark-server-docker/latest?style=for-the-badge&color=2496ED&logo=docker&logoColor=white&label=Docker%20Hub" alt="Docker Hub"></a>
        <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL_v3-blue.svg?style=for-the-badge&logo=gnu" alt="License GPLv3"></a>
        <a href="https://github.com/arkmanager/ark-server-tools"><img src="https://img.shields.io/badge/ARK_Tools-arkmanager-green.svg?style=for-the-badge" alt="arkmanager"></a>
        <img src="https://img.shields.io/badge/Platform-Linux_amd64-black.svg?style=for-the-badge&logo=linux" alt="Linux amd64">
      </p>
    </td>
  </tr>
</table>

<p>
  <b>🌐 Select Language / Selecciona Idioma:</b> &nbsp;
  <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
</p>

</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### Servidor Dedicado de ARK: Survival Evolved en Docker

Contenedor Docker para ejecutar un servidor dedicado de ARK: Survival Evolved utilizando [ARK Server Tools (arkmanager)](https://github.com/arkmanager/ark-server-tools), con respaldos automáticos integrados, notificaciones a Discord, reinicios programados y configuración completa mediante variables de entorno.

### 📖 Acerca del Proyecto

Contenedor Docker todo-en-uno diseñado para desplegar y administrar servidores dedicados de ARK: Survival Evolved de forma robusta, automatizada y sin complicaciones. Desarrollado sobre la base de [ARK Server Tools (arkmanager)](https://github.com/arkmanager/ark-server-tools) e inspirado originalmente en [indifferentbroccoli/ark-server-docker](https://github.com/indifferentbroccoli/ark-server-docker), este proyecto ha evolucionado para ofrecer una solución completa lista para producción con copias de seguridad inteligentes, notificaciones multi-idioma a Discord, reinicios programados y restauración en un solo comando.

### 📚 Centro de Documentación
Para guías detalladas paso a paso, consulta la carpeta [**`Documents/`**](Documents/README.md):
- 🌐 [**Guía de Conexión (Steam, LAN y ZeroTier sin abrir puertos)**](Documents/connect-guide.md#-español)
- ⚙️ [**Guía de Configuración Avanzada y Edición `.ini`**](Documents/configuration-guide.md#-español)
- 🛠️ [**Guía de Administración y Restauración**](Documents/management-guide.md#-español)

### Características

#### 🌟 Principales Capacidades
- **Copias de Seguridad Automáticas**: Backups periódicos con intervalo configurable y rotación por cantidad máxima de archivos (`BACKUP_MAX_COUNT`).
- **Restauración Fácil en 1 Comando**: Script ejecutable `restore.sh` para restaurar el último backup o uno específico.
- **Notificaciones a Discord**: Alertas en tiempo real en tu canal de Discord para estado del servidor, respaldos, actualizaciones y reinicios.
- **Reinicios Programados**: Reinicios automáticos periódicos (`AUTO_RESTART_HOURS`) con advertencias in-game (15m, 10m, 5m, 1m) y guardado previo del mapa.
- **Multiplicadores de Rates por Entorno**: Variables `.env` para XP, Doma (Taming), Recolección (Harvesting), Incubación (Hatching) y Crianza (Maturation).

#### ⚡ Características Base del Contenedor
- **Integración con ARK Server Tools**: Gestión completa del servidor potenciada por `arkmanager`.
- **Soporte para Mods**: Instalación y gestión sencilla de mods de la Workshop de Steam (`MOD_IDS`).
- **Soporte para Clústeres**: Configuración de viaje entre mapas (`CLUSTER_ID`).
- **Actualizaciones Automáticas**: Actualización opcional del servidor y mods al arrancar el contenedor (`UPDATE_ON_START`).
- **Configuración por Variables**: Control completo del mapa, contraseñas, RCON, PvE/PvP y BattlEye.
- **Apagado Elegante (Graceful Shutdown)**: Guardado automático del mundo (`saveworld`) al detener el contenedor (`SIGTERM` / `SIGINT`).

### Requisitos del Servidor

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU     | 2 núcleos | 4+ núcleos  |
| RAM     | 6GB    | 8GB+        |
| Almacenamiento | 30GB | 50GB+    |

### Modo de Uso

#### Docker Compose

Copia `.env.example` a `.env` y ajusta tus configuraciones:

```bash
cp .env.example .env
```

Inicia el servidor con Docker Compose:

```bash
docker compose up -d
```

Detén el servidor de forma segura:

```bash
docker compose down
```

Ver logs del servidor en tiempo real:

```bash
docker compose logs -f
```

#### Ejemplo de `docker-compose.yml`

```yaml
name: ark-server
services:
  ark-server:
    image: marcusm99/ark-server-docker:latest
    platform: linux/amd64
    restart: unless-stopped
    container_name: ark-server
    stop_grace_period: 30s
    ports:
      - "7777:7777/udp"
      - "27015:27015/udp"
      - "27020:27020/tcp"
    environment:
      - SESSION_NAME=ARK Server
      - SERVER_PASSWORD=
      - ADMIN_PASSWORD=adminpass
      - MAX_PLAYERS=10
      - WORLD=TheIsland
      - SERVER_PVE=false
      - BATTLEEYE=false
      - RCON_ENABLED=true
      - MOD_IDS=
      - BACKUP_ENABLED=true
      - BACKUP_INTERVAL_HOURS=6
      - BACKUP_MAX_COUNT=10
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### Variables de Entorno

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `PUID` | `1000` | ID de usuario para permisos de archivos |
| `PGID` | `1000` | ID de grupo para permisos de archivos |
| `SESSION_NAME` | `ARK Server` | Nombre del servidor visible en la lista de servidores |
| `SERVER_PASSWORD` | (vacío) | Contraseña para unirse (dejar vacío para servidor público) |
| `ADMIN_PASSWORD` | `adminpass` | Contraseña de administración y RCON |
| `MAX_PLAYERS` | `10` | Número máximo de jugadores permitidos |
| `WORLD` | `TheIsland` | Nombre del mapa (`TheIsland`, `ScorchedEarth_P`, `TheCenter`, `Ragnarok`, etc.) |
| `SERVER_PORT` | `7777` | Puerto UDP del juego |
| `QUERY_PORT` | `27015` | Puerto UDP de consultas de Steam |
| `RCON_PORT` | `27020` | Puerto TCP de RCON |
| `RCON_ENABLED` | `true` | Establecer en `true` para activar la consola remota RCON (`true` / `false`) |
| `SERVER_PVE` | `false` | Establecer en `true` para activar modo PvE |
| `BATTLEEYE` | `false` | Establecer en `true` para activar anti-cheat BattlEye |
| `MOD_IDS` | (vacío) | IDs de mods de Steam Workshop separados por coma (ej. `731604991,893735676`) |
| `CLUSTER_ID` | (vacío) | ID de clúster para clústeres de servidores |
| `CLUSTER_DIR_OVERRIDE` | (vacío) | Ruta del directorio compartido del clúster |
| `ADDITIONAL_ARGS` | (vacío) | Argumentos adicionales del servidor tipo `-flag` |
| `ARKMANAGER_OPTS` | (vacío) | Entradas crudas separadas por línea para `arkmanager.cfg` |
| `BETA` | `public` | Rama de Steam del servidor (`public`, `preaquatica`, etc.) |
| `UPDATE_ON_START` | `true` | Actualizar servidor y mods al arrancar el contenedor |
| `BACKUP_ENABLED` | `true` | Activar o desactivar las copias de seguridad automáticas |
| `BACKUP_INTERVAL_HOURS` | `6` | Intervalo en horas entre cada backup automático |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Directorio dentro del contenedor donde se guardan los backups |
| `BACKUP_MAX_COUNT` | (vacío) | Cantidad máxima de respaldos a conservar antes de borrar los más antiguos |
| `DISCORD_WEBHOOK_URL` | (vacío) | URL del Webhook de Discord para notificaciones del servidor |
| `DISCORD_LANGUAGE` | `es` | Idioma de los mensajes enviados a Discord (`es` / `en`) |
| `AUTO_RESTART_HOURS` | `0` | Intervalo en horas para reinicios automáticos con avisos in-game (0 = desactivado) |
| `XP_MULTIPLIER` | (vacío) | Multiplicador de experiencia (ej. `2.0`) |
| `TAME_SPEED_MULTIPLIER` | (vacío) | Multiplicador de velocidad de doma (ej. `3.0`) |
| `HARVEST_AMOUNT_MULTIPLIER` | (vacío) | Multiplicador de recolección de recursos (ej. `2.0`) |
| `HATCH_SPEED_MULTIPLIER` | (vacío) | Multiplicador de eclosión de huevos (ej. `5.0`) |
| `MATURATION_SPEED_MULTIPLIER` | (vacío) | Multiplicador de maduración de crías (ej. `5.0`) |
| `MATING_INTERVAL_MULTIPLIER` | (vacío) | Multiplicador de intervalo de apareamiento (ej. `0.5` para menor tiempo) |
| `CRAFT_SPEED_MULTIPLIER` | (vacío) | Multiplicador de velocidad de fabricación/crafteo (ej. `2.0`) |

### Notificaciones a Discord

Configura `DISCORD_WEBHOOK_URL` en tu `.env` para recibir alertas en tiempo real en tu canal de Discord para:
- Inicio y apagado del servidor
- Actualizaciones del servidor y mods
- Finalización o fallos de respaldos automáticos
- Reinicios programados

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/TU_WEBHOOK_ID/TU_WEBHOOK_TOKEN
```

### Reinicios Programados

Evita fugas de memoria y mantén el rendimiento óptimo del servidor configurando reinicios periódicos. Configurar `AUTO_RESTART_HOURS` (ej. `48`) activa `arkmanager restart --warn @main`.

- Envía **advertencias automáticas al chat del juego** (15m, 10m, 5m, 1m).
- Ejecuta `saveworld` antes de reiniciar para evitar pérdida de progreso.
- Notifica a Discord si está configurado.

```bash
# Reiniciar el servidor automáticamente cada 48 horas
AUTO_RESTART_HOURS=48
```

### Copias de Seguridad Automáticas y Restauración

Los backups automáticos funcionan de forma nativa con `arkmanager backup` dentro del bucle de monitoreo del contenedor. No se requieren paquetes adicionales ni demonios cron.

#### Configuración y Persistencia

- **`BACKUP_ENABLED`** (`true` / `false`): Activa o desactiva las copias programadas.
- **`BACKUP_INTERVAL_HOURS`** (por defecto: `6`): Controla la frecuencia de creación de respaldos.
- **`BACKUP_DIR`** (por defecto: `/home/steam/ark-backups`): Especifica la ruta interna de backups.
  > **Importante**: Mapea siempre `BACKUP_DIR` a un volumen del host en `docker-compose.yml` (ej. `./ark-backups:/home/steam/ark-backups`) para que los archivos persistan si el contenedor se elimina o actualiza.

#### Rotación de Backups por Cantidad Máxima

Configurar **`BACKUP_MAX_COUNT`** (ej. `10`) mantendrá únicamente las 10 copias de seguridad más recientes. Cada vez que se genere un nuevo backup, el contenedor eliminará automáticamente el archivo `.tar.bz2` más antiguo que supere esta cantidad. Dejar vacío o en `0` para conservar todos los backups indefinidamente.

```bash
# Conservar únicamente los últimos 10 backups
BACKUP_MAX_COUNT=10
```

#### Backup Manual y Restauración Fácil

Crear una copia de seguridad manual:

```bash
docker exec -u steam ark-server arkmanager backup @main
```

Restaurar la **última copia de seguridad** disponible en un comando:

```bash
docker exec -u steam ark-server /home/steam/scripts/restore.sh latest
```

Restaurar un **archivo de backup específico**:

```bash
docker exec -u steam ark-server /home/steam/scripts/restore.sh main.2026-07-22_14.00.00.tar.bz2
```

### Puertos

Asegúrate de que los siguientes puertos estén abiertos y redirigidos en tu enrutador/firewall:

- `7777/udp` — Puerto del juego
- `27015/udp` — Puerto de consultas de Steam (Query)
- `27020/tcp` — Puerto RCON

### ⚠️ Limitaciones Conocidas

- **Arquitectura**: Solo soporta la arquitectura `linux/amd64`. No es compatible con procesadores ARM (como Raspberry Pi o Mac Apple Silicon de forma nativa sin emulación), debido a limitaciones del binario oficial de SteamCMD y del servidor de ARK.
- **Versión del Juego**: Este contenedor está diseñado exclusivamente para **ARK: Survival Evolved** (el juego original). NO es compatible con **ARK: Survival Ascended**, el cual utiliza un motor y ejecutables de servidor completamente diferentes.

### Estructura de Archivos

```
.
├── steamcmd/               (se crea en el primer arranque)
│   └── ark/
│       └── ShooterGame/
│           ├── Binaries/
│           ├── Content/
│           │   └── Mods/   # Mods instalados
│           └── Saved/
│               └── SavedArks/ # Archivos del mapa y partida
├── ark-backups/            (se crea al ejecutar copias de seguridad)
│   └── 2026-07-22/         # una subcarpeta por día
│       └── main.2026-07-22_15.30.00.tar.bz2
└── scripts/
    ├── init.sh
    ├── start.sh
    ├── healthcheck.sh
    └── restore.sh
```

### 👨‍💻 Autor y Mantenedor

Proyecto mantenido activamente por **[GMS-EC](https://gmsec.cc/)**.

- 🌐 **Sitio Web Oficial**: [gmsec.cc](https://gmsec.cc/)
- 🐳 **Docker Hub Repository**: [marcusm99/ark-server-docker](https://hub.docker.com/r/marcusm99/ark-server-docker)
- 🐙 **GitHub Repository**: [@GMS-EC/ark-server-docker](https://github.com/GMS-EC/ark-server-docker)

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to expand / collapse)</h2></summary>

### ARK: Survival Evolved Dedicated Server in Docker

A Docker container for running an ARK: Survival Evolved dedicated server using [ARK Server Tools (arkmanager)](https://github.com/arkmanager/ark-server-tools), featuring built-in automated backups, Discord notifications, scheduled restarts, and full configuration via environment variables.

### 📖 About the Project

An all-in-one Docker container designed to deploy and manage ARK: Survival Evolved dedicated servers in a robust, automated, and hassle-free manner. Built on top of [ARK Server Tools (arkmanager)](https://github.com/arkmanager/ark-server-tools) and originally inspired by [indifferentbroccoli/ark-server-docker](https://github.com/indifferentbroccoli/ark-server-docker), this project has evolved into a complete production-ready solution featuring intelligent automated backups, multi-language Discord notifications, scheduled server restarts, and single-command restoration.

### 📚 Documentation Center
For detailed step-by-step guides, check out the [**`Documents/`**](Documents/README.md) folder:
- 🌐 [**Connection Guide (Steam, LAN & ZeroTier without Port Forwarding)**](Documents/connect-guide.md#-english)
- ⚙️ [**Advanced Configuration Guide & `.ini` Customization**](Documents/configuration-guide.md#-english)
- 🛠️ [**Server Management & Restoration Guide**](Documents/management-guide.md#-english)

### Features

#### 🌟 Core Capabilities
- **Automated Scheduled Backups**: Built-in periodic backups with configurable interval and count-based rotation (`BACKUP_MAX_COUNT`).
- **One-Command Restoration**: Simple `restore.sh` script to restore the latest or a specific backup instantly.
- **Discord Webhook Notifications**: Real-time channel alerts for server status, backups, updates, and restarts.
- **Scheduled Restarts**: Periodic automated restarts (`AUTO_RESTART_HOURS`) with in-game warnings (15m, 10m, 5m, 1m) and auto-save.
- **Server Rate Multipliers**: Environment variables for XP, Taming, Harvesting, Hatching, and Maturation rates.

#### ⚡ Core Container Features
- **ARK Server Tools Integration**: Full-featured server management powered by `arkmanager`.
- **Mod Support**: Easy installation and management of Steam Workshop mods (`MOD_IDS`).
- **Cluster Support**: Cross-travel server cluster configuration (`CLUSTER_ID`).
- **Automatic Updates**: Optional server and mod updates on container startup (`UPDATE_ON_START`).
- **Environment Configuration**: Complete control over map, passwords, RCON, PvE/PvP, and BattlEye.
- **Graceful Shutdown**: Proper world saving (`saveworld`) on container stop (`SIGTERM` / `SIGINT`).

### Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 2 cores | 4+ cores    |
| RAM      | 6GB     | 8GB+        |
| Storage  | 30GB    | 50GB+       |

### How to Use

#### Docker Compose

Copy `.env.example` to `.env` and adjust your settings:

```bash
cp .env.example .env
```

Start the server using Docker Compose:

```bash
docker compose up -d
```

Stop the server gracefully:

```bash
docker compose down
```

View live server logs:

```bash
docker compose logs -f
```

#### Quick `docker-compose.yml` Example

```yaml
name: ark-server
services:
  ark-server:
    image: marcusm99/ark-server-docker:latest
    platform: linux/amd64
    restart: unless-stopped
    container_name: ark-server
    stop_grace_period: 30s
    ports:
      - "7777:7777/udp"
      - "27015:27015/udp"
      - "27020:27020/tcp"
    environment:
      - SESSION_NAME=ARK Server
      - SERVER_PASSWORD=
      - ADMIN_PASSWORD=adminpass
      - MAX_PLAYERS=10
      - WORLD=TheIsland
      - SERVER_PVE=false
      - BATTLEEYE=false
      - RCON_ENABLED=true
      - MOD_IDS=
      - BACKUP_ENABLED=true
      - BACKUP_INTERVAL_HOURS=6
      - BACKUP_MAX_COUNT=10
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | User ID for file permissions |
| `PGID` | `1000` | Group ID for file permissions |
| `SESSION_NAME` | `ARK Server` | Server name displayed in the server browser |
| `SERVER_PASSWORD` | (empty) | Password required to join (leave empty for public) |
| `ADMIN_PASSWORD` | `adminpass` | Admin and RCON password |
| `MAX_PLAYERS` | `10` | Maximum number of players allowed |
| `WORLD` | `TheIsland` | Map name (`TheIsland`, `ScorchedEarth_P`, `TheCenter`, `Ragnarok`, etc.) |
| `SERVER_PORT` | `7777` | Game UDP port |
| `QUERY_PORT` | `27015` | Steam query UDP port |
| `RCON_PORT` | `27020` | RCON TCP port |
| `RCON_ENABLED` | `true` | Set to `true` to enable RCON remote administration (`true` / `false`) |
| `SERVER_PVE` | `false` | Set to `true` to enable PvE mode |
| `BATTLEEYE` | `false` | Set to `true` to enable BattlEye anti-cheat |
| `MOD_IDS` | (empty) | Comma-separated Steam Workshop mod IDs (e.g. `731604991,893735676`) |
| `CLUSTER_ID` | (empty) | Cluster ID for server clusters |
| `CLUSTER_DIR_OVERRIDE` | (empty) | Custom shared cluster directory path |
| `ADDITIONAL_ARGS` | (empty) | Additional `-flag` style command line arguments |
| `ARKMANAGER_OPTS` | (empty) | Raw newline-separated `arkmanager.cfg` entries for custom configuration |
| `BETA` | `public` | Server Steam branch (`public`, `preaquatica`, etc.) |
| `UPDATE_ON_START` | `true` | Update server and mods on container start |
| `BACKUP_ENABLED` | `true` | Enable or disable automatic scheduled backups |
| `BACKUP_INTERVAL_HOURS` | `6` | Interval in hours between automatic backups |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Directory inside the container where backups are stored |
| `BACKUP_MAX_COUNT` | (empty) | Max number of recent backup files to retain before purging older ones |
| `DISCORD_WEBHOOK_URL` | (empty) | Discord Webhook URL for server status, update, and backup notifications |
| `DISCORD_LANGUAGE` | `es` | Language for Discord notification messages (`es` / `en`) |
| `AUTO_RESTART_HOURS` | `0` | Interval in hours for automatic server restarts with in-game warnings (0 = disabled) |
| `XP_MULTIPLIER` | (empty) | Server XP multiplier (e.g. `2.0`) |
| `TAME_SPEED_MULTIPLIER` | (empty) | Taming speed multiplier (e.g. `3.0`) |
| `HARVEST_AMOUNT_MULTIPLIER` | (empty) | Resource harvesting multiplier (e.g. `2.0`) |
| `HATCH_SPEED_MULTIPLIER` | (empty) | Egg hatch speed multiplier (e.g. `5.0`) |
| `MATURATION_SPEED_MULTIPLIER` | (empty) | Baby dino maturation speed multiplier (e.g. `5.0`) |
| `MATING_INTERVAL_MULTIPLIER` | (empty) | Mating interval multiplier (e.g. `0.5` for shorter cooldown) |
| `CRAFT_SPEED_MULTIPLIER` | (empty) | Crafting speed multiplier (e.g. `2.0`) |

### Discord Webhook Notifications

Set `DISCORD_WEBHOOK_URL` in your `.env` to receive real-time notifications in your Discord channel for:
- Server startup and shutdown
- Server and mod updates
- Automatic backup completions or failures
- Scheduled server restarts

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### Scheduled Restarts

Prevent memory leaks and maintain optimal server performance by configuring periodic restarts. Setting `AUTO_RESTART_HOURS` (e.g., `48`) triggers `arkmanager restart --warn @main`.

- Sends automatic **in-game chat warnings** (15m, 10m, 5m, 1m).
- Executes `saveworld` to prevent rollbacks.
- Sends a notification to Discord if configured.

```bash
# Restart server automatically every 48 hours
AUTO_RESTART_HOURS=48
```

### Automatic Backups & Restoration

Automatic backups are driven natively by `arkmanager backup` inside the container's main monitoring loop. No external cron daemon or extra packages are required.

#### Configuration & Persistence

- **`BACKUP_ENABLED`** (`true` / `false`): Toggles scheduled backups.
- **`BACKUP_INTERVAL_HOURS`** (default: `6`): Controls how frequently a backup is created.
- **`BACKUP_DIR`** (default: `/home/steam/ark-backups`): Specifies the internal backup directory path.
  > **Important**: Always map `BACKUP_DIR` to a host volume in `docker-compose.yml` (e.g. `./ark-backups:/home/steam/ark-backups`) so your backup files persist even if the container is destroyed or updated.

#### Backup Retention & Rotation

Setting **`BACKUP_MAX_COUNT`** (e.g., `10`) retains only the 10 most recent backup files. Whenever a new backup is created, the container automatically purges the oldest `.tar.bz2` archive exceeding this count. Leave empty or set to `0` to keep all backups indefinitely.

```bash
# Retain only the 10 most recent backups
BACKUP_MAX_COUNT=10
```

#### Manual Backup & Easy Restoration

Trigger a manual backup:

```bash
docker exec -u steam ark-server arkmanager backup @main
```

Restore the **latest backup** in one command:

```bash
docker exec -u steam ark-server /home/steam/scripts/restore.sh latest
```

Restore a **specific backup file**:

```bash
docker exec -u steam ark-server /home/steam/scripts/restore.sh main.2026-07-22_14.00.00.tar.bz2
```

### Ports

Ensure the following ports are open and forwarded:

- `7777/udp` — Game port
- `27015/udp` — Query port
- `27020/tcp` — RCON port

### ⚠️ Known Limitations

- **Architecture**: Only supports `linux/amd64`. It is not compatible with ARM architecture (such as Raspberry Pi or Apple Silicon natively without emulation), due to limitations of the official SteamCMD binary and ARK server executable.
- **Game Version**: This container is built exclusively for **ARK: Survival Evolved** (the original game). It is NOT compatible with **ARK: Survival Ascended**, which is a separate game with different server requirements.

### File Structure

```
.
├── steamcmd/               (created on first run)
│   └── ark/
│       └── ShooterGame/
│           ├── Binaries/
│           ├── Content/
│           │   └── Mods/   # Installed mods
│           └── Saved/
│               └── SavedArks/ # World saves
├── ark-backups/            (created when backups run)
│   └── 2026-07-22/         # one subfolder per day
│       └── main.2026-07-22_15.30.00.tar.bz2
└── scripts/
    ├── init.sh
    ├── start.sh
    ├── healthcheck.sh
    └── restore.sh
```

### 👨‍💻 Author & Maintainer

Actively maintained by **[GMS-EC](https://gmsec.cc/)**.

- 🌐 **Official Website**: [gmsec.cc](https://gmsec.cc/)
- 🐳 **Docker Hub Repository**: [marcusm99/ark-server-docker](https://hub.docker.com/r/marcusm99/ark-server-docker)
- 🐙 **GitHub Repository**: [@GMS-EC/ark-server-docker](https://github.com/GMS-EC/ark-server-docker)

</details>
