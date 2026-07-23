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

### 📖 Acerca del Proyecto

Contenedor Docker todo-en-uno diseñado para desplegar y administrar servidores dedicados de ARK: Survival Evolved de forma robusta, automatizada y sin complicaciones mediante `arkmanager`. Inspirado originalmente en el proyecto de [indifferentbroccoli](https://github.com/indifferentbroccoli/ark-server-docker), este contenedor ofrece una solución completa lista para producción con copias de seguridad inteligentes, notificaciones multi-idioma a Discord, reinicios programados y restauración rápida.

### 📚 Centro de Documentación

Para guías detalladas paso a paso sobre conexión, configuración y administración, consulta la carpeta [**`Documents/`**](Documents/README.md):

- 🌐 [**Guía de Conexión (Steam, LAN y ZeroTier sin abrir puertos)**](Documents/connect-guide.md#-español) — Cómo conectarte tu y tus amigos paso a paso.
- ⚙️ [**Guía de Configuración Avanzada y Edición `.ini`**](Documents/configuration-guide.md#-español) — Personalización de `.env`, rates, `GameUserSettings.ini` y `Game.ini`.
- 🛠️ [**Guía de Administración y Restauración**](Documents/management-guide.md#-español) — Uso de `arkmanager`, notificaciones de Discord, reinicios y restauración con `restore.sh`.

### 🌟 Principales Capacidades

- **Copias de Seguridad Automáticas**: Backups periódicos integrados con rotación inteligente por cantidad (`BACKUP_MAX_COUNT`).
- **Restauración en 1 Comando**: Script ejecutable `restore.sh` para restaurar el último backup o uno específico con salvaguarda preventiva.
- **Notificaciones a Discord Multi-idioma**: Alertas en tiempo real (`DISCORD_LANGUAGE=es/en`) para estado, backups, actualizaciones y reinicios.
- **Reinicios Programados**: Reinicios automáticos periódicos (`AUTO_RESTART_HOURS`) con advertencias in-game (15m, 10m, 5m, 1m) y auto-guardado.
- **Multiplicadores de Rates por Entorno**: Control directo en `.env` para XP, Doma, Recolección, Incubación y Crianza.
- **Soporte para Mods y Clústeres**: Instalación automática de mods de la Workshop (`MOD_IDS`) y viajes entre servidores (`CLUSTER_ID`).
- **Healthcheck Inteligente**: Detecta cuando el servidor está online o cargando mapas/mods pesados.

### 🖥️ Requisitos del Servidor

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU     | 2 núcleos | 4+ núcleos  |
| RAM     | 6GB    | 8GB+        |
| Almacenamiento | 30GB | 50GB+    |

### 🚀 Modo de Uso Rápido

Copia `.env.example` a `.env` y personaliza tus contraseñas:

```bash
cp .env.example .env
docker compose up -d
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
      # --- Essential Server Settings ---
      - SESSION_NAME=ARK Server
      - SERVER_PASSWORD=
      - ADMIN_PASSWORD=adminpass
      - MAX_PLAYERS=10
      - WORLD=TheIsland
      - SERVER_PVE=false
      - BATTLEEYE=false
      - RCON_ENABLED=true
      - MOD_IDS=
      # --- Backup Settings ---
      - BACKUP_ENABLED=true
      - BACKUP_INTERVAL_HOURS=6
      - BACKUP_MAX_COUNT=10
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### ⚙️ Referencia Rápida de Variables de Entorno

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `PUID` | `1000` | ID de usuario para permisos en Linux |
| `PGID` | `1000` | ID de grupo para permisos en Linux |
| `SESSION_NAME` | `ARK Server` | Nombre del servidor visible en el buscador |
| `SERVER_PASSWORD` | (vacío) | Contraseña para unirse al servidor |
| `ADMIN_PASSWORD` | `adminpass` | Contraseña de administración (`enablecheats`) y RCON |
| `MAX_PLAYERS` | `10` | Slots máximos de jugadores |
| `WORLD` | `TheIsland` | Nombre oficial del mapa (`TheIsland`, `Ragnarok`, etc.) |
| `SERVER_PORT` | `7777` | Puerto UDP del juego |
| `QUERY_PORT` | `27015` | Puerto UDP de consultas de Steam |
| `RCON_PORT` | `27020` | Puerto TCP de RCON |
| `RCON_ENABLED` | `true` | Activa consola remota RCON |
| `SERVER_PVE` | `false` | Activa modo PvE |
| `BATTLEEYE` | `false` | Activa protección BattlEye |
| `MOD_IDS` | (vacío) | IDs de mods de Steam Workshop separados por coma |
| `CLUSTER_ID` | (vacío) | ID de clúster para viajar entre servidores |
| `CLUSTER_DIR_OVERRIDE` | (vacío) | Ruta del directorio compartido del clúster |
| `ADDITIONAL_ARGS` | (vacío) | Argumentos adicionales tipo `-flag` para el servidor |
| `ARKMANAGER_OPTS` | (vacío) | Entradas crudas inyectadas en `arkmanager.cfg` |
| `BETA` | `public` | Rama de actualización en Steam (`public`, `preaquatica`, etc.) |
| `UPDATE_ON_START` | `true` | Actualizar servidor y mods al arrancar el contenedor |
| `BACKUP_ENABLED` | `true` | Activa las copias de seguridad automáticas |
| `BACKUP_INTERVAL_HOURS` | `6` | Intervalo en horas entre cada backup |
| `BACKUP_MAX_COUNT` | `10` | Máximo de backups a conservar |
| `DISCORD_WEBHOOK_URL` | (vacío) | URL del Webhook de Discord |
| `DISCORD_LANGUAGE` | `es` | Idioma de las alertas de Discord (`es` / `en`) |
| `AUTO_RESTART_HOURS` | `0` | Intervalo de reinicios programados en horas (0 = desactivado) |

> 📌 *Consulta la [Guía de Configuración Avanzada](Documents/configuration-guide.md#-español) para ver la lista completa de variables de rates y opciones avanzadas.*

### ⚠️ Limitaciones Conocidas

- **Arquitectura**: Solo soporta `linux/amd64`. No es compatible con procesadores ARM (como Raspberry Pi o Mac Apple Silicon de forma nativa), debido a limitaciones del binario oficial de SteamCMD y del servidor de ARK.
- **Versión del Juego**: Este contenedor es exclusivo para **ARK: Survival Evolved** (el juego original). NO es compatible con **ARK: Survival Ascended**.

### 📂 Estructura de Archivos

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

### 📖 About the Project

An all-in-one Docker container designed to deploy and manage ARK: Survival Evolved dedicated servers in a robust, automated, and hassle-free manner using `arkmanager`. Originally inspired by the project by [indifferentbroccoli](https://github.com/indifferentbroccoli/ark-server-docker), this container offers a complete production-ready solution featuring intelligent automated backups, multi-language Discord notifications, scheduled server restarts, and one-command restoration.

### 📚 Documentation Center

For detailed step-by-step guides on connecting, configuring, and managing your server, check the [**`Documents/`**](Documents/README.md) folder:

- 🌐 [**Connection Guide (Steam, LAN & ZeroTier without Port Forwarding)**](Documents/connect-guide.md#-english) — Step-by-step connection guide for you and friends.
- ⚙️ [**Advanced Configuration Guide & `.ini` Customization**](Documents/configuration-guide.md#-english) — Environment variables, server rates, `GameUserSettings.ini` & `Game.ini`.
- 🛠️ [**Server Management & Restoration Guide**](Documents/management-guide.md#-english) — `arkmanager` CLI, Discord alerts, scheduled restarts, and `restore.sh`.

### 🌟 Core Capabilities

- **Automated Scheduled Backups**: Built-in periodic backups with configurable interval and count-based rotation (`BACKUP_MAX_COUNT`).
- **One-Command Restoration**: Simple `restore.sh` script to restore the latest or a specific backup instantly with pre-safety backups.
- **Multi-language Discord Webhooks**: Real-time alerts (`DISCORD_LANGUAGE=es/en`) for server status, backups, updates, and restarts.
- **Scheduled Restarts**: Periodic automated restarts (`AUTO_RESTART_HOURS`) with in-game warnings (15m, 10m, 5m, 1m) and auto-save.
- **Server Rate Multipliers**: Direct `.env` configuration for XP, Taming, Harvesting, Hatching, and Maturation rates.
- **Mod & Cluster Support**: Automatic Steam Workshop mod installation (`MOD_IDS`) and cross-server transfer configuration (`CLUSTER_ID`).
- **Smart Healthcheck**: Accurately detects when the server is online or stuck loading heavy mods/maps.

### 🖥️ Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 2 cores | 4+ cores    |
| RAM      | 6GB     | 8GB+        |
| Storage  | 30GB    | 50GB+       |

### 🚀 Quick Start

Copy `.env.example` to `.env` and customize your settings:

```bash
cp .env.example .env
docker compose up -d
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
      # --- Essential Server Settings ---
      - SESSION_NAME=ARK Server
      - SERVER_PASSWORD=
      - ADMIN_PASSWORD=adminpass
      - MAX_PLAYERS=10
      - WORLD=TheIsland
      - SERVER_PVE=false
      - BATTLEEYE=false
      - RCON_ENABLED=true
      - MOD_IDS=
      # --- Backup Settings ---
      - BACKUP_ENABLED=true
      - BACKUP_INTERVAL_HOURS=6
      - BACKUP_MAX_COUNT=10
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### ⚙️ Quick Reference Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | User ID for Linux file permissions |
| `PGID` | `1000` | Group ID for Linux file permissions |
| `SESSION_NAME` | `ARK Server` | Server name displayed in the server browser |
| `SERVER_PASSWORD` | (empty) | Password required to join |
| `ADMIN_PASSWORD` | `adminpass` | Admin (`enablecheats`) and RCON password |
| `MAX_PLAYERS` | `10` | Maximum player slots |
| `WORLD` | `TheIsland` | Official map name (`TheIsland`, `Ragnarok`, etc.) |
| `SERVER_PORT` | `7777` | Game UDP port |
| `QUERY_PORT` | `27015` | Steam query UDP port |
| `RCON_PORT` | `27020` | RCON TCP port |
| `RCON_ENABLED` | `true` | Enable RCON remote administration |
| `SERVER_PVE` | `false` | Enable PvE mode |
| `BATTLEEYE` | `false` | Enable BattlEye anti-cheat |
| `MOD_IDS` | (empty) | Comma-separated Steam Workshop mod IDs |
| `CLUSTER_ID` | (empty) | Cluster ID for server clusters |
| `CLUSTER_DIR_OVERRIDE` | (empty) | Custom cluster directory path |
| `ADDITIONAL_ARGS` | (empty) | Additional `-flag` command line arguments |
| `ARKMANAGER_OPTS` | (empty) | Raw newline-separated `arkmanager.cfg` entries |
| `BETA` | `public` | Steam update branch (`public`, `preaquatica`, etc.) |
| `UPDATE_ON_START` | `true` | Update server and mods on container start |
| `BACKUP_ENABLED` | `true` | Enable automatic scheduled backups |
| `BACKUP_INTERVAL_HOURS` | `6` | Backup interval in hours |
| `BACKUP_MAX_COUNT` | `10` | Max recent backup files to retain |
| `DISCORD_WEBHOOK_URL` | (empty) | Discord Webhook URL for channel notifications |
| `DISCORD_LANGUAGE` | `es` | Language for Discord notification messages (`es` / `en`) |
| `AUTO_RESTART_HOURS` | `0` | Scheduled restart interval in hours (0 = disabled) |

> 📌 *Check out the [Advanced Configuration Guide](Documents/configuration-guide.md#-english) for the full list of rate multipliers and raw `.ini` options.*

### ⚠️ Known Limitations

- **Architecture**: Only supports `linux/amd64`. It is not compatible with ARM architecture (such as Raspberry Pi or Apple Silicon natively), due to limitations of the official SteamCMD binary and ARK server executable.
- **Game Version**: This container is built exclusively for **ARK: Survival Evolved** (the original game). It is NOT compatible with **ARK: Survival Ascended**.

### 📂 File Structure

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
