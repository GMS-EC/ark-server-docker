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
- 🛠️ [**Guía de Administración del Servidor**](Documents/management-guide.md#-español) — Uso de `arkmanager`, notificaciones de Discord, reinicios y horarios.
- 📦 [**Guía de Copias de Seguridad y Restauración**](Documents/backup-restore-guide.md#-español) — Backups organizados (`Saved/`), restauración en 1 clic desde el panel web y manual por SFTP (FileZilla).

### 🌟 Principales Capacidades

- **Panel de Control Web Integrado (ARK Server Manager)**: Interfaz gráfica web moderna en el puerto `8080` (FastAPI + WebSockets) con consola en vivo, monitoreo de CPU/RAM/Disco en tiempo real, gestión de supervivientes, explorador de archivos completo y creación/restauración de backups con un solo clic.
- **Seguridad Reforzada**: Rate limiting inteligente contra fuerza bruta (bloqueo de 10 minutos tras 5 intentos fallidos), sesiones protegidas de 60 minutos con clave criptográfica persistente y compresión Gzip nativa.
- **Copias de Seguridad Automáticas y Estructuradas**: Backups periódicos organizados (`Saved/SavedArks`, `Saved/Config`) con rotación inteligente por cantidad configurable 100% desde la pestaña Tareas.
- **Restauración en 1 Clic y Soporte Manual**: Restauración visual con un solo clic desde el panel web (con salvaguarda preventiva automática) y soporte manual arrastrando carpetas por SFTP.
- **Notificaciones a Discord Multi-idioma**: Alertas en tiempo real con selector de idioma (Español / Inglés) y matriz de eventos estilo Dockraft desde la pestaña Webhooks.
- **Reinicios Programados**: Reinicios automáticos periódicos con advertencias in-game (15m, 10m, 5m, 1m) y auto-guardado gestionados en la pestaña Tareas.
- **Horario Automático de Encendido/Apagado**: Encendido y apagado programado del proceso del juego para ahorro de CPU/RAM con protección de jugadores activos y avisos in-game desde la pestaña Tareas.
- **Multiplicadores de Rates y Reglas**: Control visual e interactivo en la pestaña Ajustes para XP, Doma, Crianza, Calidad de Vida (GUS.ini) y selección de Mapa.
- **Soporte para Mods y Clústeres**: Instalación de mods Workshop en 1 clic (pestaña Mods) y clúster multi-mapa interconectado (pestaña Clúster).
- **Healthcheck Inteligente**: Detecta cuando el servidor está online o cargando mapas/mods pesados.

### 🖥️ Requisitos del Servidor y Guía de Dimensionamiento

| Recurso | Mínimo | Recomendado (1 Mapa) |
|---------|--------|----------------------|
| CPU     | 2 núcleos | 4+ núcleos  |
| RAM     | 6GB    | 8GB+        |
| Almacenamiento | 30GB | 50GB+    |

#### 📊 Referencia Orientativa de Consumo de RAM

> [!NOTE]
> *Un servidor en `TheIsland` con 3 jugadores y mods de utilidad opera cómodamente con **8GB de RAM**. Mapas extensos (como Ragnarok, Genesis o Fjordur) o packs de mods pesados pueden requerir entre **10GB y 14GB+ de RAM** por mapa.*
> 📌 *Consulta la [Guía de Administración y Dimensionamiento por Mapa](Documents/management-guide.md#-español) para ver la tabla completa de consumo de memoria RAM por cada mapa oficial.*

#### 🌐 Dimensionamiento para Clústeres Multi-mapa (`CLUSTER_ID`)

Si planeas configurar un **clúster multi-mapa** para permitir viajes entre servidores:

1. **Instancias Independientes**: Un clúster **no** es un "único servidor más grande". Cada mapa adicional en el clúster ejecuta su propio proceso ejecutable (`ShooterGameServer`) en paralelo, con su propio archivo de guardado y configuración.
2. **Escalamiento Lineal de RAM**: El consumo de memoria RAM escala de forma **prácticamente lineal por cada mapa adicional**, casi de forma independiente a la cantidad de jugadores conectados en cada uno (el costo base de cargar el mapa en memoria existe incluso con 0 jugadores).
3. **Presupuesto de Memoria**: Si tu mapa base requiere 8GB de RAM, agregar un segundo mapa al clúster (ej. *ScorchedEarth* además de *TheIsland*) requerirá presupuestar aproximadamente el doble de memoria (un segundo bloque completo de memoria para la segunda instancia), y así sucesivamente por cada mapa adicional.
4. **Monitoreo Recomendado**: Se recomienda verificar el uso real de memoria de tus contenedores mediante `docker stats` al agregar cada mapa nuevo al clúster.

### 🖥️ Panel Web ARK Server Manager (`http://localhost:8080`)

Una vez iniciado el contenedor, abre tu navegador en **`http://localhost:8080`** (o la IP de tu servidor):
* **Usuario por defecto:** `admin`
* **Contraseña por defecto:** `adminpassword` *(configurable en `.env`)*

#### ✨ Módulos Integrados en el Panel Web:
1. **📊 Métricas y Rendimiento en Tiempo Real:** Monitor de CPU, memoria RAM del contenedor y del proceso ARK (`ShooterGameServer`), espacio en disco y tiempo de actividad (uptime) con gráfico histórico dinámico y optimización *Page Visibility API*.
2. **💻 Consola en Vivo con WebSockets:** Transmisión de logs en streaming directo, barra de comandos rápidos RCON, filtro de búsqueda, descarga de logs y auditoría visual de eventos.
3. **🌐 Red de Clúster Multi-Mapa:** Administración centralizada de hasta 12 mapas de ARK simultáneos, asignación automática de puertos, aislamiento de guardado protegido (`AltSaveDir`), sincronización de tasas en 1 clic y explorador en vivo de la nube de obeliscos (`/clusters`).
4. **🧩 Gestor de Mods de Steam Workshop:** Catálogo visual con 1-clic para instalar mods populares (Structures Plus, Awesome Spyglass, Dino Storage v2, etc.), instalador manual por ID y actualizador de mods.
5. **📁 Explorador y Editor de Archivos:** Navegación por carpetas del servidor y nube compartida de clúster con menú contextual (clic derecho), editor de texto con resaltado de sintaxis para `.ini`, compresión ZIP, descarga y subida protegida.
6. **📦 Copias de Seguridad y Restauración:** Creación de respaldos en 1 clic, rotación automática (`BACKUP_MAX_COUNT`), descarga directa y restauración visual inmediata con salvaguarda preventiva automática.
7. **👥 Gestión de Supervivientes:** Monitoreo de jugadores conectados en tiempo real con SteamID, ping y tiempo en sesión, con acciones de *Kick*, *Ban* y gestión de Lista Blanca.
8. **⚙️ Configuración del Servidor:** Ajuste visual de multiplicadores de jugabilidad (XP, Tameo, Cosecha, Incubación, Crianza), contraseñas, modos PvE/PvP y protección BattlEye.
9. **⏰ Tareas y Horarios Automatizados:** Programación de encendido/apagado (`SCHEDULE_START`/`SCHEDULE_STOP`) con avisos in-game, reinicios periódicos (`AUTO_RESTART_HOURS`) y repoblación de fauna (*Dino Wipe*).
10. **🔔 Webhooks de Discord:** Alertas enriquecidas con embeds personalizables para inicio, paradas, avisos, respaldos y dino wipes.
11. **🛡️ Seguridad Reforzada:** Protección inteligente contra fuerza bruta (máximo 5 intentos fallidos, bloqueo de 10 minutos con código 429), sesiones protegidas de 60 minutos con clave criptográfica persistente y compresión Gzip nativa.

---

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
    # Límite de RAM del contenedor. Cambia el valor según cuánta
    # memoria quieras asignarle a tu servidor (ej. 8g, 12g, 16g).
    mem_limit: 12g
    ports:
      - "8080:8080"                    # Panel Web ARK Server Manager (HTTP)
      - "7777-7800:7777-7800/udp"      # Puertos de Juego UDP (Principal + hasta 12 Mapas Clúster)
      - "27015-27035:27015-27035/udp"  # Puertos Query Steam UDP (Buscador de Servidores)
      - "27020-27035:27020-27035/tcp"  # Puertos RCON TCP (Consola Remota y Administración)
    environment:
      # --- ARK Server Manager Web Panel ---
      - PANEL_PORT=8080
      - PANEL_USER=admin
      - PANEL_PASSWORD=adminpassword
      - AUTOSTART_SERVER=true
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
      # --- Updates & Maintenance ---
      - UPDATE_ON_START=true
      - AUTO_RESTART_HOURS=0
      # --- Timezone ---
      - TZ=UTC

      # En v2.0+, Webhooks, Horarios, Respaldos, Dino Wipes, Mods y Tasas
      # se configuran y administran 100% dentro del Panel Web.
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
      - ./clusters:/home/steam/clusters
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### ⚙️ Variables de Entorno de Docker (Infraestructura Esencial)

El contenedor Docker solo requiere variables para la infraestructura base:

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `TZ` | `America/Guayaquil` | Zona horaria del contenedor para sincronizar horarios y logs. |
| `PANEL_PORT` | `8080` | Puerto HTTP para acceder al panel de administración web. |
| `PANEL_USER` | `admin` | Usuario administrador del panel web. |
| `PANEL_PASSWORD` | `adminpassword` | Contraseña de acceso al panel web (recomendado cambiar). |
| `PUID` / `PGID` | `1000` | ID de usuario y grupo en Linux para permisos de archivos (opcional). |

#### ⚡ Funciones Centralizadas 100% en el Panel Web (Sin Duplicación en Docker)
A partir de la versión 2.0+, las siguientes funciones se gestionan y guardan dinámicamente desde la interfaz web, sin necesidad de definir variables en Docker:
* 🔔 **Webhooks de Discord**: URL del webhook, idioma y prueba de notificación en vivo desde la pestaña **Webhooks**.
* ⏰ **Automatizaciones y Tareas**: Horario de actividad (Power Schedule con encendido/apagado programado), respaldos periódicos, rotación de copias máximas, dino wipes automáticos y reinicios programados desde la pestaña **Tareas**.
* 🧩 **Mods de Steam Workshop**: Búsqueda, presets populares en 1 clic y auto-actualización desde la pestaña **Mods**.
* 🎛️ **Tasas y Multiplicadores**: Multiplicadores de XP, domesticación, recolección y crianza desde la pestaña **Ajustes**.
* 🌐 **Clúster Multi-Mapa**: Gestión de hasta 12 mapas vinculados con puertos y carpetas automáticas desde la pestaña **Clúster**.

*(Nota de compatibilidad: Si tu contenedor posee variables de Docker previas como `DISCORD_WEBHOOK_URL` o `SCHEDULE_START`, el panel las importa automáticamente en el primer arranque para mantener todas tus preferencias sin pérdida).*

#### 🔌 Puertos de Red Requeridos

| Puerto | Protocolo | Variable | Descripción |
|--------|-----------|----------|-------------|
| `8080` | TCP | `PANEL_PORT` | Panel de Control Web **ARK Server Manager** (interfaz gráfica completa para gestión y monitoreo). |
| `7777-7800` | UDP | `SERVER_PORT` | Puerto principal de juego (7777) y rango para hasta 12 mapas de clúster vinculados. |
| `27015-27035` | UDP | `QUERY_PORT` | Puertos de consulta de Steam para buscador de servidores (principal y clúster). |
| `27020-27035` | TCP | `RCON_PORT` | Puertos RCON para consola remota, administración y avisos broadcast in-game. |

> ℹ️ **Nota sobre RCON y Seguridad:** `RCON_ENABLED=true` es **obligatorio** para que los avisos in-game (`broadcast`) y autoguardados (`saveworld`) funcionen en reinicios y apagos automáticos (ya que `arkmanager` se conecta por `localhost` internamente). El puerto `27020/tcp` está publicado en `ports:` por defecto para permitir conexiones de clientes RCON externos o bots de Discord. Si **no** utilizas herramientas RCON externas, puedes comentar la línea `27020:27020/tcp` en `docker-compose.yml` para cerrar el acceso externo sin afectar los avisos internos del servidor.

> 📌 *Consulta la [Guía de Configuración Avanzada](Documents/configuration-guide.md#-español) para ver la lista completa de variables avanzadas (PUID/PGID, clústeres, rates y arkmanager).*

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
│               ├── SavedArks/      # Partida servidor principal
│               ├── ScorchedEarth/  # Partidas independientes de clúster
│               └── Config/         # GameUserSettings.ini y Game.ini
├── ark-backups/            (copias de seguridad comprimidas .tar.bz2)
├── clusters/               (datos compartidos de obeliscos del clúster)
├── app/                    (backend FastAPI de ARK Server Manager)
├── web/                    (interfaz gráfica web y plantillas)
└── scripts/
    ├── init.sh             # Entrypoint principal
    ├── start.sh            # Lanzador de ShooterGameServer
    ├── healthcheck.sh      # Monitor de salud
    └── generate-config.sh  # Generador de arkmanager.cfg
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
- 🛠️ [**Server Management Guide**](Documents/management-guide.md#-english) — `arkmanager` CLI, Discord alerts, scheduled restarts, and power schedule.
- 📦 [**Backup & Restoration Guide**](Documents/backup-restore-guide.md#-english) — Clean organized backups (`Saved/`), 1-click restore from web panel, and step-by-step SFTP manual restore.

### 🌟 Core Capabilities

- **Automated Structured Backups**: Built-in periodic backups maintaining ARK's native folder hierarchy (`Saved/SavedArks`, `Saved/Config`) with count-based rotation (`BACKUP_MAX_COUNT`).
- **1-Click Web Restoration & SFTP Support**: Instant 1-click restore from the web panel with automated safety backups, plus plug-and-play FileZilla folder drag & drop.
- **Multi-language Discord Webhooks**: Real-time alerts (`DISCORD_LANGUAGE=es/en`) for server status, backups, updates, and restarts.
- **Scheduled Restarts**: Periodic automated restarts (`AUTO_RESTART_HOURS`) with in-game warnings (15m, 10m, 5m, 1m) and auto-save.
- **Automatic Power Schedule**: Start and stop server process on a schedule (`SCHEDULE_ENABLED`, `SCHEDULE_START`, `SCHEDULE_STOP`, `TZ`) to conserve CPU/RAM with active player protection and in-game warnings.
- **Server Rate Multipliers**: Direct `.env` configuration for XP, Taming, Harvesting, Hatching, and Maturation rates.
- **Mod & Cluster Support**: Automatic Steam Workshop mod installation (`MOD_IDS`) and cross-server transfer configuration (`CLUSTER_ID`).
- **Smart Healthcheck**: Accurately detects when the server is online or stuck loading heavy mods/maps.

### 🖥️ Server Requirements & Sizing Guide

| Resource | Minimum | Recommended (1 Map) |
|----------|---------|---------------------|
| CPU      | 2 cores | 4+ cores            |
| RAM      | 6GB     | 8GB+                |
| Storage  | 30GB    | 50GB+               |

#### 📊 Orientative RAM Consumption Reference

> [!NOTE]
> *A server running `TheIsland` with 3 active players and utility mods operates comfortably with **8GB of RAM**. Large expansion maps (such as Ragnarok, Genesis, or Fjordur) or heavy modpacks can require **10GB to 14GB+ of RAM** per map.*
> 📌 *Check the [Server Management & Map RAM Sizing Guide](Documents/management-guide.md#-english) for the complete RAM consumption breakdown by official map.*

#### 🌐 Sizing Guidelines for Multi-map Clusters (`CLUSTER_ID`)

If you plan to deploy a **multi-map cluster** allowing players to travel between servers:

1. **Independent Instances**: A cluster is **not** a single larger server. Every additional map in the cluster runs its own completely separate server process (`ShooterGameServer`) in parallel, with its own save data and configuration.
2. **Linear RAM Scaling**: Memory consumption scales **almost linearly for each additional map**, nearly independent of the number of active players connected to each map (the base memory cost of loading the map exists even with 0 active players).
3. **Memory Budgeting**: If your base map requires 8GB of RAM, adding a second map to the cluster (e.g. *ScorchedEarth* alongside *TheIsland*) requires budgeting approximately double the memory (an additional full memory block for the second instance), scaling further with each added map.
4. **Recommended Monitoring**: We strongly advise monitoring real-time container memory usage with `docker stats` as you add each new map to your cluster.

### 🖥️ ARK Server Manager Web Dashboard (`http://localhost:8080`)

Once the container is running, access the web panel in your browser at **`http://localhost:8080`** (or your server's IP):
* **Default Username:** `admin`
* **Default Password:** `adminpassword` *(configurable in `.env`)*

#### ✨ Integrated Web Panel Features:
1. **📊 Real-Time Metrics & Performance:** Monitors container CPU, ARK process RAM (`ShooterGameServer`), disk usage, and server uptime with dynamic historical graphs and *Page Visibility API* background throttling.
2. **💻 Live WebSocket Console:** Real-time log streaming, quick RCON bar, log search filter, full log download, and visual audit log.
3. **🌐 Multi-Map Cluster Network:** Centralized management for up to 12 simultaneous official ARK maps, automated port allocation, protected save directory isolation (`AltSaveDir`), 1-click rate synchronization, and live obelisk cloud explorer (`/clusters`).
4. **🧩 Steam Workshop Mods Manager:** Visual 1-click catalog for essential community mods (Structures Plus, Awesome Spyglass, Dino Storage v2, etc.), manual ID installer, and one-click mod updater.
5. **📁 File Manager & Editor:** Full folder navigation and cluster cloud access with right-click context menus, built-in text editor for `.ini` files, ZIP compression, download, and secure upload.
6. **📦 Backup & Restoration:** 1-click custom-named backup creation, automated retention rotation (`BACKUP_MAX_COUNT`), direct browser downloads, and 1-click restoration with automatic pre-safety backups.
7. **👥 Player Management:** Live connected survivor tracker with SteamID, ping, and online duration, plus instant *Kick*, *Ban*, and Whitelist actions.
8. **⚙️ Server Settings:** Visual multiplier controls (XP, Taming, Harvesting, Breeding, Maturation), passwords, PvE/PvP modes, and BattlEye protection.
9. **⏰ Automated Tasks & Power Schedule:** Scheduled start/stop windows (`SCHEDULE_START`/`SCHEDULE_STOP`) with in-game warnings, periodic auto-restarts (`AUTO_RESTART_HOURS`), and wild dino repopulation (*Dino Wipe*).
10. **🔔 Discord Webhooks:** Rich visual embeds with customizable colors for server startup, online status, shutdown warnings, backups, and dino wipes.
11. **🛡️ Hardened Security:** Intelligent brute-force protection (maximum 5 failed attempts, 10-minute lockout with HTTP 429), 60-minute session expiry with persistent crypto key, and native Gzip compression.

---

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
    # Container RAM limit. Change the value depending on how much
    # memory you want to allocate to your server (e.g. 8g, 12g, 16g).
    mem_limit: 12g
    ports:
      - "8080:8080"                    # ARK Server Manager Web Panel (HTTP)
      - "7777-7800:7777-7800/udp"      # Game UDP Ports (Primary + up to 12 Cluster Maps)
      - "27015-27035:27015-27035/udp"  # Steam Query UDP Ports (Server Browser)
      - "27020-27035:27020-27035/tcp"  # RCON TCP Ports (Remote Console & Administration)
    environment:
      # --- ARK Server Manager Web Panel ---
      - PANEL_PORT=8080
      - PANEL_USER=admin
      - PANEL_PASSWORD=adminpassword
      - AUTOSTART_SERVER=true
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
      # --- Updates & Maintenance ---
      - UPDATE_ON_START=true
      - AUTO_RESTART_HOURS=0
      # --- Timezone ---
      - TZ=UTC

      # En v2.0+, Webhooks, Horarios, Respaldos, Dino Wipes, Mods y Tasas
      # se configuran y administran 100% dentro del Panel Web.
    volumes:
      - ./steamcmd/ark:/home/steam/steamcmd/ark
      - ./ark-backups:/home/steam/ark-backups
      - ./clusters:/home/steam/clusters
    labels:
      icon: https://raw.githubusercontent.com/GMS-EC/ark-server-docker/main/Documents/logo.png
```

### ⚙️ Docker Environment Variables (Essential Infrastructure)

The Docker container only requires variables for core infrastructure:

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `America/Guayaquil` | Container timezone for schedule synchronization and log timestamps. |
| `PANEL_PORT` | `8080` | HTTP port to access the web administration control panel. |
| `PANEL_USER` | `admin` | Admin username to log in to the web panel. |
| `PANEL_PASSWORD` | `adminpassword` | Access password for the web panel (change recommended). |
| `PUID` / `PGID` | `1000` | Linux user and group ID for mounted storage permissions (optional). |

#### ⚡ 100% In-App Web Panel Centralized Features (No Docker Duplication)
From version 2.0 onwards, all server gameplay and management settings are dynamically configured and saved via the Web UI:
* 🔔 **Discord Webhooks**: Webhook URL, language selector (`Español` / `English`), live test button, and event filter matrix via the **Webhooks** tab.
* ⏰ **Automations & Tasks**: Power Schedule (start/stop schedule with advance warning), automated backups, max retention rotation, automatic dino wipes, and scheduled restarts via the **Tasks** tab.
* 🧩 **Steam Workshop Mods**: Mod search, 1-click popular presets, and auto-update toggles via the **Mods** tab.
* 🎛️ **Rates, Map & Rules**: Map selector (`world`), Session Name, passwords, XP/Taming/Breeding multipliers, and Quality of Life toggles via the **Settings** tab.
* 🌐 **Multi-Map Cluster**: Interconnect up to 12 official maps with automatic ports and isolated directories via the **Cluster** tab.

*(Backward compatibility notice: If your container has legacy Docker variables like `DISCORD_WEBHOOK_URL` or `SCHEDULE_START`, the panel automatically imports them on first startup so no preferences are ever lost).*

#### 🔌 Required Network Ports

| Port | Protocol | Variable | Description |
|------|----------|----------|-------------|
| `8080` | TCP | `PANEL_PORT` | Web Control Panel **ARK Server Manager** (full graphical interface for administration). |
| `7777-7800` | UDP | `SERVER_PORT` | Primary game port (7777) and active port range for up to 12 linked cluster maps. |
| `27015-27035` | UDP | `QUERY_PORT` | Steam query port range for server browser listings (primary & cluster nodes). |
| `27020-27035` | TCP | `RCON_PORT` | RCON port range for remote console, external management, and in-game broadcasts. |

> ℹ️ **Note on RCON & Security:** `RCON_ENABLED=true` is **mandatory** for automated in-game warning broadcasts (`broadcast`) and world saves (`saveworld`) during scheduled restarts/shutdowns (since `arkmanager` connects internally via `localhost`). Port `27020/tcp` is published under `ports:` by default to allow external RCON tools or Discord bots to connect. If you do **not** use external RCON tools, you can comment out `- "27020:27020/tcp"` in `docker-compose.yml` to block external access without impacting internal automated broadcasts.

> 📌 *Check the [Advanced Configuration Guide](Documents/configuration-guide.md#-english) for the complete list of advanced variables (PUID/PGID, clusters, rates, and arkmanager).*

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
│               ├── SavedArks/      # Primary server save files
│               ├── ScorchedEarth/  # Isolated cluster map save files
│               └── Config/         # GameUserSettings.ini & Game.ini
├── ark-backups/            (compressed .tar.bz2 backup archives)
├── clusters/               (shared obelisk tribute & character files)
├── app/                    (ARK Server Manager FastAPI backend)
├── web/                    (web UI assets & templates)
└── scripts/
    ├── init.sh             # Main container entrypoint
    ├── start.sh            # ShooterGameServer process launcher
    ├── healthcheck.sh      # Container health monitor
    └── generate-config.sh  # arkmanager.cfg generator
```

### 👨‍💻 Author & Maintainer

Actively maintained by **[GMS-EC](https://gmsec.cc/)**.

- 🌐 **Official Website**: [gmsec.cc](https://gmsec.cc/)
- 🐳 **Docker Hub Repository**: [marcusm99/ark-server-docker](https://hub.docker.com/r/marcusm99/ark-server-docker)
- 🐙 **GitHub Repository**: [@GMS-EC/ark-server-docker](https://github.com/GMS-EC/ark-server-docker)

</details>
