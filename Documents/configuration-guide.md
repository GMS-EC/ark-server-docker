<div align="center">
  <h1>⚙️ Guía de Configuración Avanzada / Advanced Configuration Guide</h1>
  <p>
    <b>Select Language / Selecciona Idioma:</b><br>
    <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
  </p>
</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### ⚙️ Guía de Configuración Avanzada y Personalización `.ini`

Esta guía detalla cómo personalizar completamente tu servidor de ARK, desde las variables de entorno en el archivo `.env` hasta la edición avanzada de los archivos `GameUserSettings.ini` y `Game.ini`.

---

#### 📄 1. Variables de Entorno de Docker (`.env`)

En la arquitectura v2.0, el archivo `.env` y el `docker-compose.yml` se reservan **exclusivamente para la infraestructura técnica** del contenedor:

| Variable | Valor por Defecto | Descripción Técnica |
|----------|-------------------|---------------------|
| `TZ` | `America/Guayaquil` | Zona horaria del contenedor para programaciones y registros de consola. |
| `PANEL_USER` | `admin` | Usuario administrador para iniciar sesión en la interfaz gráfica. |
| `PANEL_PASSWORD` | `adminpassword` | Contraseña para iniciar sesión en el panel web. |
| `PUID` / `PGID` | `1000` | ID de usuario y grupo de Linux para asegurar permisos en los volúmenes montados. |

---

> 💡 **Nota sobre el puerto del panel:** El contenedor ejecuta internamente el panel web en el puerto `8080` de manera fija y automática. Si deseas acceder desde otro puerto en tu máquina (como `8586`), cámbialo directamente en la sección `ports:` de tu `docker-compose.yml` (`- "8586:8080"`), sin necesidad de crear variables redundantes en `.env`.

#### 🎮 2. Configuración Centralizada en el Panel Web (100% In-App)

Para eliminar duplicidades, evitar reiniciar contenedores y brindar una experiencia moderna (estilo Dockraft), toda la configuración del juego se gestiona de forma interactiva y visual desde el navegador web:

* 🎛️ **Pestaña Ajustes (Settings)**:
  - **Identidad & Acceso**: Nombre de la Sesión (`SessionName`), Contraseña de Entrada (`ServerPassword`), Contraseña Admin / RCON (`ServerAdminPassword`), Límite Máximo de Supervivientes (`MaxPlayers`), y selector de **Autoinicio del Servidor**.
  - **Multiplicadores de Tasas (Rates)**: XP, Tameo, Cosecha, Crianza, Eclosión e Intervalo de Apareamiento guardados directamente en `GameUserSettings.ini` y `Game.ini`.
  - **Modos y Reglas**: Alternar PvE / PvP, visualización de supervivientes en el mapa, retícula y vista en 3ra persona.
* 🧩 **Pestaña Mods**:
  - Búsqueda en Steam Workshop, presets populares en 1 clic (Awesome Spyglass, Dino Storage v2, S+, etc.) y actualización automática de mods.
* ⏰ **Pestaña Tareas (Tasks)**:
  - **Power Schedule**: Horario de encendido y apagado diario (`HH:MM`) con avisos in-game.
  - **Respaldos Automáticos**: Intervalo en horas y rotación de copias máximas a conservar.
  - **Dino Wipes y Reinicios Programados**: `DestroyWildDinos` periódico y reinicios con aviso de 5 minutos.
* 🔔 **Pestaña Webhooks (Discord)**:
  - URL del webhook de Discord e **idioma de los mensajes** (`Español` / `English`).
  - **Matriz de Eventos Activos**: Casillas para activar/desactivar notificaciones individuales (Inicio de carga, Servidor online, Apagado, Aviso por horario, Respaldos, Dino Wipe, Reinicios y Jugadores).
  - Botón de **Probar Notificación** en vivo.
* 🌐 **Pestaña Clúster**:
  - Creación y vinculación de hasta 12 mapas oficiales interconectados por obeliscos compartidos (`/clusters/ArkCluster`) con aislamiento automático de carpetas y puertos sin colisiones.

##### ⚡ Configuración Centralizada en la Interfaz Web (Versión 2.0+)
En la versión 2.0+, para evitar duplicaciones y reiniciar el contenedor, las siguientes áreas se configuran **100% dentro del Panel Web**:
* **Webhooks de Discord** (Pestaña *Webhooks*): URL del Webhook, idioma (`es` / `en`) y botón para probar notificaciones en vivo.
* **Automatizaciones y Horarios** (Pestaña *Tareas*):
  - **Power Schedule**: Horario de encendido y apagado (`HH:MM`) con aviso in-game previo.
  - **Respaldos Automáticos**: Intervalo (cada X horas) y copias máximas a retener.
  - **Dino Wipes y Reinicios Programados**: `DestroyWildDinos` periódico y reinicio con cuenta regresiva de 5 minutos.
* **Mods Workshop** (Pestaña *Mods*): Búsqueda, instalación en 1 clic de presets populares y actualización de mods.
* **Tasas y Multiplicadores** (Pestaña *Ajustes*): Multiplicadores de XP, tameo, recolección y crianza guardados directamente en `GameUserSettings.ini`.
* **Clúster Multi-Mapa** (Pestaña *Clúster*): Gestión de hasta 12 mapas interconectados por obeliscos con puertos automáticos.

*(Nota: Cualquier variable definida previamente en Docker es importada automáticamente al iniciar el servidor para no perder ninguna configuración).*

##### ⚡ Multiplicadores de Rates Recomendados (Solo / Dúo)
| Variable | Descripción | Valor Oficial | Recomendado PvE Dúo |
|----------|-------------|---------------|----------------------|
| `XP_MULTIPLIER` | Multiplicador de experiencia obtenida | `1.0` | `2.0` |
| `TAME_SPEED_MULTIPLIER` | Velocidad de domesticación de criaturas | `1.0` | `3.0` |
| `HARVEST_AMOUNT_MULTIPLIER` | Cantidad de recursos recolectados por golpe | `1.0` | `2.0` |
| `HATCH_SPEED_MULTIPLIER` | Velocidad de eclosión de huevos / gestación | `1.0` | `5.0` |
| `MATURATION_SPEED_MULTIPLIER` | Velocidad de crecimiento de las crías de dinosaurios | `1.0` | `5.0` |
| `MATING_INTERVAL_MULTIPLIER` | Tiempo de espera entre apareamientos | `1.0` | `0.5` |
| `CRAFT_SPEED_MULTIPLIER` | Velocidad al fabricar ítems en inventario | `1.0` | `2.0` |

---

#### 🛠️ 2. Banderas Adicionales (`ADDITIONAL_ARGS`)

Permite pasar argumentos tipo `-flag` directamente a la línea de comandos de lanzamiento del ejecutable del servidor de ARK (`ShooterGameServer`). En la versión 2.0+, se configura directamente desde el campo **Argumentos Adicionales** en la pestaña **Ajustes** del panel web:

```bash
-ServerHardcore -ForceAllowCaveFlyers -DisableStructureDecayPvE -AllowFlyerCarryPvE
```

##### Banderas Populares Recomendadas:
- `-automanagedmods`: Habilita la descarga y actualización automática de mods de la Workshop de Steam.
- `-ForceAllowCaveFlyers`: Permite volar montado en voladores dentro de cuevas.
- `-AllowFlyerCarryPvE`: Permite a los voladores agarrar dinosaurios o jugadores salvajes en modo PvE.
- `-DisableStructureDecayPvE`: Desactiva la demolición automática de estructuras inactivas en PvE.
- `-DisableDinoDecayPvE`: Desactiva la desaparición de dinosaurios domados inactivos en PvE.
- `-PreventDownloadSurvivors=False`: Permite transferir personajes al servidor.

---

#### 📝 3. Edición de Archivos `.ini` (`GameUserSettings.ini` y `Game.ini`)

> 💡 **¡Recomendado desde el Panel Web!**  
> Ya no necesitas abrir terminal, SSH ni FileZilla para editar estos archivos. En el panel web (**http://localhost:8080**), puedes:
> - **Pestaña Configuración:** Ajustar multiplicadores (XP, Tameo, Crianza), contraseñas y puertos desde formularios visuales.
> - **Pestaña Archivos:** Abrir y editar `GameUserSettings.ini` y `Game.ini` con el editor de código integrado estilo VSCode, guardando cambios al instante.

Ubicación en el sistema de archivos del host: `./steamcmd/ark/ShooterGame/Saved/Config/LinuxServer/`

##### 🔹 Edición de `GameUserSettings.ini`

Ubicación del bloque `[ServerSettings]`:
```ini
[ServerSettings]
; Dificultad Máxima (Dinos salvajes hasta nivel 150)
DifficultyOffset=1.000000
OverrideOfficialDifficulty=5.000000

; Calidad de Vida y Visuales en el Juego
; Permite subir velocidad a dinosaurios voladores
bAllowFlyerSpeedLeveling=True
; Muestra tu posición en el mapa (tecla M)
ShowMapPlayerLocation=True
; Muestra la retícula / mira en pantalla
ServerCrosshair=True
; Muestra números de daño flotante al golpear
ShowFloatingDamageText=True
; Muestra indicador visual de impacto acertado
AllowHitMarkers=True
; Permite cambiar a vista en 3ra persona
AllowThirdPersonPlayer=True

; Construcción y Estructuras
; Permite recoger estructuras mal colocadas en los primeros 30 seg
StructurePickupTimeAfterPlacement=30.0
; Habilita estructuras integradas estilo S+
AllowIntegratedSPlusStructures=True
```

Ubicación del bloque `[/Script/ShooterGame.ShooterGameUserSettings]`:
```ini
[/Script/ShooterGame.ShooterGameUserSettings]
; Muestra un haz de luz sobre tu cadáver/mochila al morir
bEnableCorpseLocator=True
```

##### 🔹 Edición de `Game.ini`

Ubicación del bloque `[/script/shootergame.shootergamemode]`:
```ini
[/script/shootergame.shootergamemode]
; Desactivar colisión de estructuras al construir
bDisableStructurePlacementCollision=True

; Multiplicadores de Peso por Nivel (Stat Index 7 = Peso / Weight)
; Doble de peso por nivel para el jugador
PerLevelStatsMultiplier_Player[7]=2.0
; x2.5 de peso por nivel para dinosaurios domesticados
PerLevelStatsMultiplier_DinoTamed[7]=2.5
```

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to expand / collapse)</h2></summary>

### ⚙️ Advanced Configuration Guide & `.ini` Customization

This guide details how to fully customize your ARK server, from environment variables in `.env` to advanced editing of `GameUserSettings.ini` and `Game.ini`.

---

#### 📄 1. Environment Variables (`.env`)

##### 👤 Permissions & Hardware Resources
| Variable | Default | Technical Description |
|----------|---------|-----------------------|
| `PUID` | `1000` | System user ID for `steam`. Ensures saved files match Linux permissions. |
| `PGID` | `1000` | System group ID for `steam`. |

##### 🎮 Basic Server Settings
| Variable | Default | Technical Description |
|----------|---------|-----------------------|
| `SESSION_NAME` | `ARK Server` | Server name displayed in the in-game list and Steam browser. |
| `SERVER_PASSWORD` | *(empty)* | Password required to join. Leave empty for public access. |
| `ADMIN_PASSWORD` | `adminpass` | Password for admin commands in chat (`enablecheats YOUR_PASSWORD`). |
| `MAX_PLAYERS` | `10` | Maximum simultaneous player slots allowed. |
| `WORLD` | `TheIsland` | Official map name (`TheIsland`, `ScorchedEarth_P`, `TheCenter`, `Ragnarok`, `Aberration_P`, `Extinction`, `Valguero_P`, `Genesis`, `CrystalIsles`, `Genesis2`, `LostIsland`, `Fjordur`). |

##### 🔌 Network Ports
| Variable | Default | Protocol | Description |
|----------|---------|----------|-------------|
| `SERVER_PORT` | `7777` | UDP | Main game communication port. |
| `QUERY_PORT` | `27015` | UDP | Steam server browser and query port. |
| `RCON_PORT` | `27020` | TCP | Remote administration RCON port for external connections. Optional (in-game broadcasts and saveworld work internally without publishing this port). |

##### 🏰 Server Clusters
| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_ID` | *(empty)* | Cluster ID for linking multiple servers and enabling cross-travel. |
| `CLUSTER_DIR_OVERRIDE` | `/home/steam/clusters` | Custom shared directory path for cluster data storage (automatic by default matching volume `/home/steam/clusters`). |

##### 🔄 Steam Updates & Branches
| Variable | Default | Description |
|----------|---------|-------------|
| `BETA` | `public` | Steam server update branch (`public`, `preaquatica`, etc.). |
| `UPDATE_ON_START` | `true` | Automatically update server and mods when the container starts. |

##### 🛠️ Advanced arkmanager & Console Options
| Variable | Default | Description |
|----------|---------|-------------|
| `ADDITIONAL_ARGS` | *(empty)* | Additional `-flag` command line arguments (e.g. `-ServerHardcore -ForceAllowCaveFlyers`). |
| `ARKMANAGER_OPTS` | *(empty)* | Raw newline-separated entries injected directly into `arkmanager.cfg`. |

##### 📦 Backups, Notifications & Restarts
| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_ENABLED` | `true` | Enable or disable automated scheduled backups. |
| `BACKUP_INTERVAL_HOURS` | `6` | Backup frequency interval in hours. |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Container directory where backup files are saved. |
| `BACKUP_MAX_COUNT` | `10` | Maximum backup files to retain (older files are purged automatically). |
| `DISCORD_WEBHOOK_URL` | *(empty)* | Discord Webhook URL for status and event channel notifications. |
| `DISCORD_LANGUAGE` | `es` | Language for Discord alert messages (`es` / `en`). |
| `AUTO_RESTART_HOURS` | `0` | Scheduled restart interval in hours (0 = disabled). |

##### ⏰ Automatic Power Schedule & Timezone
| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULE_ENABLED` | `false` | Enables or disables automatic power start/stop schedule for the ARK server process. |
| `SCHEDULE_START` | `20:00` | Server power-on time in 24-hour `HH:MM` format (e.g. `20:00`). |
| `SCHEDULE_STOP` | `00:00` | Server power-off time in 24-hour `HH:MM` format (e.g. `00:00` or `02:00`). Supports midnight-crossing windows. |
| `TZ` | `UTC` | Container timezone (e.g. `America/Guayaquil`, `Europe/Madrid`). Determines how `SCHEDULE_START`, `SCHEDULE_STOP`, and log timestamps are evaluated. |
| `SCHEDULE_WARN_MINUTES` | `10` | Advance notice in minutes to send in-game chat broadcast and Discord notification before scheduled shutdown (0 = disabled). |

##### ⚡ Recommended Server Rates (Solo / Duo)
| Variable | Description | Official Rate | Recommended PvE Duo |
|----------|-------------|---------------|---------------------|
| `XP_MULTIPLIER` | Experience gain multiplier | `1.0` | `2.0` |
| `TAME_SPEED_MULTIPLIER` | Dino taming speed multiplier | `1.0` | `3.0` |
| `HARVEST_AMOUNT_MULTIPLIER` | Resource gathering multiplier | `1.0` | `2.0` |
| `HATCH_SPEED_MULTIPLIER` | Egg hatch / gestation speed multiplier | `1.0` | `5.0` |
| `MATURATION_SPEED_MULTIPLIER` | Baby dino maturation speed multiplier | `1.0` | `5.0` |
| `MATING_INTERVAL_MULTIPLIER` | Cooldown between matings | `1.0` | `0.5` |
| `CRAFT_SPEED_MULTIPLIER` | Item crafting speed multiplier | `1.0` | `2.0` |

---

#### 🛠️ 2. Additional Command Line Flags (`ADDITIONAL_ARGS`)

Example `.env` usage:
```bash
ADDITIONAL_ARGS=-ServerHardcore -ForceAllowCaveFlyers -DisableStructureDecayPvE -AllowFlyerCarryPvE
```

##### Popular Command Line Flags:
- `-automanagedmods`: Enables automatic downloading and updating of Steam Workshop mods.
- `-ForceAllowCaveFlyers`: Allows flying mounts inside caves.
- `-AllowFlyerCarryPvE`: Allows flyers to pick up wild dinos/players in PvE.
- `-DisableStructureDecayPvE`: Disables automatic structure decay in PvE.
- `-DisableDinoDecayPvE`: Disables automatic dino unclaiming in PvE.
- `-PreventDownloadSurvivors=False`: Enables character transfers into the server.

---

#### 📝 3. Direct `.ini` File Customization (`GameUserSettings.ini` & `Game.ini`)

File location: `./steamcmd/ark/ShooterGame/Saved/Config/LinuxServer/`

##### 🔹 Editing `GameUserSettings.ini`

Under `[ServerSettings]`:
```ini
[ServerSettings]
; Max Difficulty (Wild dinos up to level 150)
DifficultyOffset=1.000000
OverrideOfficialDifficulty=5.000000

; Quality of Life & Visuals
; Enables leveling up movement speed on flying dinos
bAllowFlyerSpeedLeveling=True
; Displays your location on the map (M key)
ShowMapPlayerLocation=True
; Enables in-game crosshair
ServerCrosshair=True
; Shows floating damage numbers when hitting targets
ShowFloatingDamageText=True
; Shows visual hit markers on target impact
AllowHitMarkers=True
; Allows switching to 3rd person view
AllowThirdPersonPlayer=True

; Building & Structures
; Allows picking up misplaced structures within 30s
StructurePickupTimeAfterPlacement=30.0
; Enables integrated S+ building features
AllowIntegratedSPlusStructures=True
```

Under `[/Script/ShooterGame.ShooterGameUserSettings]`:
```ini
[/Script/ShooterGame.ShooterGameUserSettings]
; Shows a green light beam over your body/backpack on death
bEnableCorpseLocator=True
```

##### 🔹 Editing `Game.ini`

Under `[/script/shootergame.shootergamemode]`:
```ini
[/script/shootergame.shootergamemode]
; Disable structure placement collisions
bDisableStructurePlacementCollision=True

; Stat Multipliers Per Level (Stat Index 7 = Weight)
; Double weight gain per level for players
PerLevelStatsMultiplier_Player[7]=2.0
; x2.5 weight gain per level for tamed dinos
PerLevelStatsMultiplier_DinoTamed[7]=2.5
```

</details>
