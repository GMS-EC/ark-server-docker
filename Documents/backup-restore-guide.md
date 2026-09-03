<div align="center">
  <h1>📦 Guía de Copias de Seguridad y Restauración / Backup & Restoration Guide</h1>
  <p>
    <b>Select Language / Selecciona Idioma:</b><br>
    <a href="#-español"><b>🇪🇸 Español</b></a> &nbsp;|&nbsp; <a href="#-english"><b>🇬🇧 English</b></a>
  </p>
</div>

---

<details open>
<summary><h2 id="-español" style="display:inline-block;">🇪🇸 Español (Haz clic aquí para contraer / desplegar)</h2></summary>

### 📦 Guía de Copias de Seguridad y Restauración

Esta guía detalla el funcionamiento del sistema de copias de seguridad de tu servidor de ARK, qué contiene cada archivo guardado y cómo restaurar tu partida tanto de forma **100% automatizada por comando** como de forma **manual por SFTP (FileZilla / WinSCP)**.

---

#### 🗺️ 1. Anatomía de los Archivos de Guardado de ARK

Cuando realizas una copia de seguridad o exploras los datos del servidor por SFTP, encontrarás diferentes extensiones de archivo:

| Archivo / Extensión | Ubicación en el Servidor | ¿Para qué sirve? |
| :--- | :--- | :--- |
| **`<Mapa>.ark`** *(ej. `TheIsland.ark`)* | `ShooterGame/Saved/SavedArks/` | **El mundo activo.** Contiene el terreno, estructuras construidas por jugadores, dinos salvajes y dinos domesticados. |
| **`*.arkprofile`** *(ej. `76561198...arkprofile`)* | `ShooterGame/Saved/SavedArks/` | **Perfil de Jugador.** Guarda el nivel, experiencia, inventario personal y engramas. El número largo corresponde al **SteamID64** del jugador. |
| **`*.arktribe`** *(ej. `1551505882.arktribe`)* | `ShooterGame/Saved/SavedArks/` | **Datos de Tribu.** Guarda la membresía, registros de tribu y qué estructuras o criaturas pertenecen a cada tribu. |
| **`Game.ini`** | `ShooterGame/Saved/Config/LinuxServer/` | **Configuración de Juego.** Engramas personalizados, niveles extra, límites de crianza y multiplicadores avanzados. |
| **`GameUserSettings.ini`** | `ShooterGame/Saved/Config/LinuxServer/` | **Ajustes Principales.** Dificultad, contraseñas, vista en tercera persona, retícula y parámetros generales. |
| **`<Mapa>_DD.MM.YYYY_...ark`** | `ShooterGame/Saved/SavedArks/` | **Autoguardados automáticos del juego.** ARK genera estos respaldos cada 15-30 minutos en caliente. Solo se usan como histórico en caso de corrupción extrema. |
| **`*.profilebak` / `*.tribebak`** | `ShooterGame/Saved/SavedArks/` | **Respaldos temporales automáticos.** Copias de seguridad que ARK realiza justo antes de sobreescribir un personaje o tribu. |

---

#### 🗂️ 2. Estructura de las Copias de Seguridad (`.tar.bz2`)

El servidor genera copias de seguridad comprimidas en formato `.tar.bz2` dentro de la carpeta mapeada `./ark-backups/` en tu host.

El sistema empaqueta los respaldos con la jerarquía nativa de carpetas de ARK:

```text
main.2026-09-02_22.00.00.tar.bz2
├── Saved/
│   ├── SavedArks/
│   │   ├── TheIsland.ark
│   │   ├── 76561198189918598.arkprofile
│   │   └── 1551505882.arktribe
│   ├── Config/
│   │   └── LinuxServer/
│   │       ├── Game.ini
│   │       └── GameUserSettings.ini
│   └── SaveGames/
├── LEEME_RESTAURACION.txt
└── README_RESTORATION.txt
```

> [!TIP]
> **Compatibilidad Hacia Atrás:** Si tienes copias de seguridad antiguas con archivos sueltos generadas por versiones previas de `arkmanager`, el script de restauración las detecta automáticamente y coloca cada archivo en su carpeta correspondiente.

---

#### ⚡ 3. Método 1: Restauración Automatizada (Recomendado)

Este método es el más rápido, seguro y libre de errores humanos. No necesitas descomprimir nada ni mover carpetas a mano.

##### Paso 1: Colocar la copia en la carpeta de respaldos
Asegúrate de que el archivo comprimido `.tar.bz2` que deseas restaurar se encuentra dentro de la carpeta `./ark-backups/` del host (o la carpeta que tengas montada en tu `docker-compose.yml`).

##### Paso 2: Ejecutar el comando de restauración
Abre una terminal en tu servidor (o vía SSH) y ejecuta:

* **Para restaurar la copia más reciente automáticamente:**
  ```bash
  docker exec -it ark-server /home/steam/scripts/restore.sh latest
  ```

* **Para restaurar una copia específica por su nombre:**
  ```bash
  docker exec -it ark-server /home/steam/scripts/restore.sh main.2026-09-02_21.53.08.tar.bz2
  ```

##### ¿Qué hace el script automáticamente?
1. **Guarda el estado actual (`saveworld`)**.
2. **Crea un respaldo de seguridad preventivo** nombrado `pre_restore_safety_<fecha>` para que nunca pierdas tu progreso actual.
3. **Detiene el servidor** limpiamente (`arkmanager stop`).
4. **Detecta el formato del backup** (organizado o legado) y extrae los archivos en sus rutas exactas.
5. **Ajusta los permisos de usuario** (`steam:steam`).
6. **Reinicia el servidor** (`arkmanager start`).

---

#### 🖐️ 4. Método 2: Restauración Manual por SFTP (FileZilla / WinSCP)

Si descargaste la copia a tu equipo, ya la descomprimiste o prefieres mover los archivos mediante un cliente gráfico de SFTP (como FileZilla):

> [!CAUTION]
> **PASO 0 OBLIGATORIO: Detén el servidor antes de transferir archivos**<br>
> Si el servidor está encendido, ARK mantiene el mapa y los jugadores en memoria RAM. Cualquier archivo que subas será sobreescrito por el juego al guardar o se corromperá la base de datos.<br>
> En la terminal de Linux de tu servidor ejecuta:
> ```bash
> docker compose stop
> ```
> *(o `docker stop ark-server`)*

##### Opción A: Si tu copia de seguridad tiene la carpeta `Saved/` (Formato Organizado)
1. En FileZilla, navega en el panel remoto (Linux) hasta la carpeta:
   ```
   .../steamcmd/ark/ShooterGame/
   ```
2. Arrastra la carpeta descomprimida `Saved/` directamente dentro de `ShooterGame/`.
3. Confirma la sobreescritura de archivos. ¡Todo el mapa, personajes y configuraciones quedarán en su sitio en un solo paso!

##### Opción B: Si tu copia tiene archivos sueltos (Formato Legado / arkmanager plano)
Si descomprimiste un archivo que tiene todos los archivos mezclados en una sola carpeta, debes subirlos por separado:

1. **Mapa, Jugadores y Tribus:**
   - Sube `TheIsland.ark`, todos los `*.arkprofile` y los `*.arktribe` a:
     👉 `ShooterGame/Saved/SavedArks/`
2. **Archivos de Configuración (`.ini`):**
   - Sube `Game.ini` y `GameUserSettings.ini` a:
     👉 `ShooterGame/Saved/Config/LinuxServer/`
   *(⚠️ Si los colocas dentro de `SavedArks/`, el juego los ignorará).*
3. **Carpeta `SaveGames` (si contiene datos):**
   - Sube la carpeta a:
     👉 `ShooterGame/Saved/SaveGames/`

##### Paso Final: Iniciar el servidor
Una vez terminada la transferencia, arranca nuevamente el contenedor:
```bash
docker compose start
```
*(o `docker compose up -d`)*

---

#### 💾 5. Generar Copias de Seguridad Manuales e Inmediatas

Además de las copias automáticas cada `BACKUP_INTERVAL_HOURS`, puedes forzar una copia de seguridad en cualquier momento:

```bash
docker exec -it ark-server /home/steam/scripts/backup.sh
```

El script guardará el mundo, generará el archivo organizado en `./ark-backups/` y aplicará la rotación de copias configurada (`BACKUP_MAX_COUNT`).

---

#### ⚙️ 6. Variables de Entorno Relacionadas (`.env`)

| Variable | Valor por Defecto | Descripción |
| :--- | :--- | :--- |
| `BACKUP_ENABLED` | `true` | Habilita el ciclo de copias automáticas programadas. |
| `BACKUP_INTERVAL_HOURS` | `6` | Horas entre cada copia automática (ej. `6` realiza 4 copias al día). |
| `BACKUP_MAX_COUNT` | `10` | Cantidad máxima de respaldos a conservar antes de purgar los más viejos. |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Ruta dentro del contenedor donde se guardan los archivos comprimidos. |

</details>

---

<details>
<summary><h2 id="-english" style="display:inline-block;">🇬🇧 English (Click here to collapse / expand)</h2></summary>

### 📦 Backup and Restoration Guide

This guide details how your ARK server backup system works, what each saved file contains, and how to restore your game using either the **100% automated single-command method** or the **manual SFTP method (FileZilla / WinSCP)**.

---

#### 🗺️ 1. ARK Save File Anatomy

When creating backups or exploring server files via SFTP, you will encounter several file types:

| File / Extension | Server Location | Purpose |
| :--- | :--- | :--- |
| **`<Map>.ark`** *(e.g., `TheIsland.ark`)* | `ShooterGame/Saved/SavedArks/` | **The active world.** Contains terrain data, player structures, wild dinos, and tamed creatures. |
| **`*.arkprofile`** *(e.g., `76561198...arkprofile`)* | `ShooterGame/Saved/SavedArks/` | **Player Profile.** Stores character level, experience, inventory, and learned engrams. The number is the player's **SteamID64**. |
| **`*.arktribe`** *(e.g., `1551505882.arktribe`)* | `ShooterGame/Saved/SavedArks/` | **Tribe Data.** Stores tribe membership, admin logs, and ownership of structures and dinos. |
| **`Game.ini`** | `ShooterGame/Saved/Config/LinuxServer/` | **Game Configuration.** Custom engrams, extra level caps, breeding overrides, and advanced multipliers. |
| **`GameUserSettings.ini`** | `ShooterGame/Saved/Config/LinuxServer/` | **Core Server Settings.** Difficulty offset, passwords, third-person view, crosshair, and gameplay rules. |
| **`<Map>_DD.MM.YYYY_...ark`** | `ShooterGame/Saved/SavedArks/` | **In-game historical autosaves.** ARK writes these every 15-30 minutes while running. Used only for emergency recovery. |
| **`*.profilebak` / `*.tribebak`** | `ShooterGame/Saved/SavedArks/` | **Automatic temporary backups.** Safety files created by ARK immediately before updating player or tribe files. |

---

#### 🗂️ 2. Backup Archive Structure (`.tar.bz2`)

The server generates compressed `.tar.bz2` backups inside the host volume `./ark-backups/`.

The system packages backups maintaining ARK's native directory structure:

```text
main.2026-09-02_22.00.00.tar.bz2
├── Saved/
│   ├── SavedArks/
│   │   ├── TheIsland.ark
│   │   ├── 76561198189918598.arkprofile
│   │   └── 1551505882.arktribe
│   ├── Config/
│   │   └── LinuxServer/
│   │       ├── Game.ini
│   │       └── GameUserSettings.ini
│   └── SaveGames/
├── LEEME_RESTAURACION.txt
└── README_RESTORATION.txt
```

> [!TIP]
> **Backward Compatibility:** If you have older flat backups created by previous versions of `arkmanager`, the restoration script detects them automatically and organizes them into their proper directories.

---

#### ⚡ 3. Method 1: Automated Restoration (Recommended)

This method is the fastest, safest, and eliminates human error. No manual extraction or folder moving is required.

##### Step 1: Place the backup in your backup directory
Ensure the `.tar.bz2` archive you want to restore is located inside `./ark-backups/` on your host (or the folder mapped in `docker-compose.yml`).

##### Step 2: Run the restoration command
Open a terminal on your server (or via SSH) and run:

* **To automatically restore the most recent backup:**
  ```bash
  docker exec -it ark-server /home/steam/scripts/restore.sh latest
  ```

* **To restore a specific backup by file name:**
  ```bash
  docker exec -it ark-server /home/steam/scripts/restore.sh main.2026-09-02_21.53.08.tar.bz2
  ```

##### What does the script do automatically?
1. **Flushes active world state to disk (`saveworld`)**.
2. **Generates an automatic pre-restoration safety backup** named `pre_restore_safety_<timestamp>` so you never lose current progress.
3. **Gracefully stops the server** (`arkmanager stop`).
4. **Detects the archive format** (organized or legacy flat) and extracts files to their exact paths.
5. **Fixes file permissions** (`steam:steam`).
6. **Restarts the server** (`arkmanager start`).

---

#### 🖐️ 4. Method 2: Manual SFTP Restoration (FileZilla / WinSCP)

If you downloaded the backup to your PC, extracted it, or prefer using a graphical SFTP client:

> [!CAUTION]
> **MANDATORY STEP 0: Stop the server before transferring files**<br>
> While running, ARK holds map and player data in RAM. Any files uploaded to disk while running will be overwritten on next save or cause database corruption.<br>
> In your Linux terminal, run:
> ```bash
> docker compose stop
> ```
> *(or `docker stop ark-server`)*

##### Option A: If your backup contains the `Saved/` directory (Organized Format)
1. In FileZilla, navigate in the remote panel (Linux) to:
   ```
   .../steamcmd/ark/ShooterGame/
   ```
2. Drag the extracted `Saved/` directory directly into `ShooterGame/`.
3. Confirm overwriting existing files. World saves, profiles, and settings will all land in their correct locations!

##### Option B: If your backup contains loose files (Legacy / flat arkmanager backup)
If you extracted an archive where all files are in a single folder, upload them to their respective destinations:

1. **Map, Players, and Tribes:**
   - Upload `TheIsland.ark`, all `*.arkprofile` files, and `*.arktribe` files to:
     👉 `ShooterGame/Saved/SavedArks/`
2. **Configuration Files (`.ini`):**
   - Upload `Game.ini` and `GameUserSettings.ini` to:
     👉 `ShooterGame/Saved/Config/LinuxServer/`
   *(⚠️ If placed in `SavedArks/`, the server will ignore them).*
3. **`SaveGames` Folder (if it contains data):**
   - Upload to:
     👉 `ShooterGame/Saved/SaveGames/`

##### Final Step: Start the server
Once the file transfer is complete, restart the container:
```bash
docker compose start
```
*(or `docker compose up -d`)*

---

#### 💾 5. Triggering Manual On-Demand Backups

In addition to scheduled backups every `BACKUP_INTERVAL_HOURS`, you can trigger an instant organized backup anytime:

```bash
docker exec -it ark-server /home/steam/scripts/backup.sh
```

This saves the world, creates the organized archive in `./ark-backups/`, and applies automatic rotation (`BACKUP_MAX_COUNT`).

---

#### ⚙️ 6. Environment Variables (`.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `BACKUP_ENABLED` | `true` | Enables periodic automated backups. |
| `BACKUP_INTERVAL_HOURS` | `6` | Hours between automatic backups (e.g., `6` produces 4 backups daily). |
| `BACKUP_MAX_COUNT` | `10` | Maximum number of backups to keep before purging older ones. |
| `BACKUP_DIR` | `/home/steam/ark-backups` | Internal container path where compressed archives are stored. |

</details>
