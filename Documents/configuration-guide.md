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

#### 📄 1. Variables de Entorno (`.env`)

El archivo `.env` permite configurar el servidor sin necesidad de modificar archivos internamente:

##### 👤 Permisos y Proceso
| Variable | Valor por Defecto | Descripción Técnica |
|----------|-------------------|---------------------|
| `PUID` | `1000` | ID del usuario `steam` en el sistema. Asegura que los archivos guardados pertenezcan a tu usuario en Linux. |
| `PGID` | `1000` | ID del grupo `steam` en el sistema. |

##### 🎮 Configuración Básica del Servidor
| Variable | Valor por Defecto | Descripción Técnica |
|----------|-------------------|---------------------|
| `SESSION_NAME` | `ARK Server` | El nombre con el que el servidor aparecerá en la lista global de ARK y en Steam. |
| `SERVER_PASSWORD` | *(vacío)* | Contraseña obligatoria para ingresar al servidor. Dejar en blanco para acceso público. |
| `ADMIN_PASSWORD` | `adminpass` | Contraseña para usar comandos de administrador en el chat (`enablecheats TU_CONTRASEÑA`). |
| `MAX_PLAYERS` | `10` | Cantidad máxima de slots/jugadores simultáneos permitidos. |
| `WORLD` | `TheIsland` | Nombre oficial del mapa a cargar (`TheIsland`, `ScorchedEarth_P`, `TheCenter`, `Ragnarok`, `Aberration_P`, `Extinction`, `Valguero_P`, `Genesis`, `CrystalIsles`, `Genesis2`, `LostIsland`, `Fjordur`). |

##### 🔌 Puertos de Red
| Variable | Valor por Defecto | Protocolo | Descripción |
|----------|-------------------|-----------|-------------|
| `SERVER_PORT` | `7777` | UDP | Puerto principal donde los clientes de ARK transmiten el movimiento y acciones. |
| `QUERY_PORT` | `27015` | UDP | Puerto que responde a las búsquedas de servidores de Steam y en el buscador in-game. |
| `RCON_PORT` | `27020` | TCP | Puerto para administración remota por RCON (ej. ARKon o scripts de comandos). |

##### 🛡️ Reglas y Modos de Juego
| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `SERVER_PVE` | `false` | Si se establece en `true`, activa el modo PvE (los jugadores no pueden atacarse ni dañar estructuras ajenas). |
| `BATTLEEYE` | `false` | Si se establece en `true`, habilita la protección anti-trampas de BattlEye. |
| `RCON_ENABLED` | `true` | Habilita o desactiva la consola de administración remota RCON. |
| `MOD_IDS` | *(vacío)* | Lista de IDs de mods de Steam Workshop separados por coma (ej. `731604991,893735676`). |

##### 🏰 Clústeres de Servidores
| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `CLUSTER_ID` | *(vacío)* | Identificador para conectar varios servidores en un clúster y permitir viajes entre mapas. |
| `CLUSTER_DIR_OVERRIDE` | *(vacío)* | Ruta personalizada para el directorio compartido de datos del clúster. |

##### 🔄 Actualizaciones y Ramas de Steam
| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `BETA` | `public` | Rama de actualización en Steam (`public`, `preaquatica`, etc.). |
| `UPDATE_ON_START` | `true` | Si se establece en `true`, verifica e instala actualizaciones del servidor y mods al arrancar. |

##### 🛠️ Opciones Avanzadas de arkmanager y Consola
| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `ADDITIONAL_ARGS` | *(vacío)* | Argumentos adicionales tipo `-flag` para el ejecutable (ej. `-ServerHardcore -ForceAllowCaveFlyers`). |
| `ARKMANAGER_OPTS` | *(vacío)* | Entradas crudas separadas por salto de línea para inyectar directamente en `arkmanager.cfg`. |

##### 📦 Backups, Notificaciones y Reinicios
| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `BACKUP_ENABLED` | `true` | Habilita o desactiva las copias de seguridad automáticas programadas. |
| `BACKUP_INTERVAL_HOURS` | `6` | Intervalo en horas entre cada respaldo automático. |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Directorio dentro del contenedor donde se almacenan las copias. |
| `BACKUP_MAX_COUNT` | *(vacío)* | Número máximo de respaldos a conservar (los más viejos se eliminan automáticamente). |
| `DISCORD_WEBHOOK_URL` | *(vacío)* | URL del Webhook de Discord para notificaciones de estado y eventos. |
| `DISCORD_LANGUAGE` | `es` | Idioma de los mensajes de alerta en Discord (`es` / `en`). |
| `AUTO_RESTART_HOURS` | `0` | Intervalo en horas para reinicios automáticos con avisos in-game (0 = desactivado). |

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

`ADDITIONAL_ARGS` permite pasar argumentos tipo `-flag` directamente a la línea de comandos de lanzamiento del ejecutable del servidor de ARK (`ShooterGameServer`).

Ejemplo de uso en tu `.env`:
```bash
ADDITIONAL_ARGS=-ServerHardcore -ForceAllowCaveFlyers -DisableStructureDecayPvE -AllowFlyerCarryPvE
```

##### Banderas Populares Recomendadas:
- `-automanagedmods`: Habilita la descarga y actualización automática de mods de la Workshop de Steam.
- `-ForceAllowCaveFlyers`: Permite volar montado en voladores dentro de cuevas.
- `-AllowFlyerCarryPvE`: Permite a los voladores agarrar dinosaurios o jugadores salvajes en modo PvE.
- `-DisableStructureDecayPvE`: Desactiva la demolición automática de estructuras inactivas en PvE.
- `-DisableDinoDecayPvE`: Desactiva la desaparición de dinosaurios domados inactivos en PvE.
- `-PreventDownloadSurvivors=False`: Permite transferir personajes al servidor.

---

#### 📝 3. Edición Directa de Archivos `.ini` (`GameUserSettings.ini` y `Game.ini`)

Ubicación en tu PC: `./steamcmd/ark/ShooterGame/Saved/Config/LinuxServer/`

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

##### 👤 Permissions & System
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
| `RCON_PORT` | `27020` | TCP | Remote administration RCON port. |

##### 🏰 Server Clusters
| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_ID` | *(empty)* | Cluster ID for linking multiple servers and enabling cross-travel. |
| `CLUSTER_DIR_OVERRIDE` | *(empty)* | Custom shared directory path for cluster data storage. |

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
| `BACKUP_MAX_COUNT` | *(empty)* | Maximum backup files to retain (older files are purged automatically). |
| `DISCORD_WEBHOOK_URL` | *(empty)* | Discord Webhook URL for status and event channel notifications. |
| `DISCORD_LANGUAGE` | `es` | Language for Discord alert messages (`es` / `en`). |
| `AUTO_RESTART_HOURS` | `0` | Scheduled restart interval in hours (0 = disabled). |

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
