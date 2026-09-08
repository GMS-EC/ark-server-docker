# 📚 Centro de Documentación / Documentation Center

<p align="center">
  <b>Language / Idioma:</b><br>
  <a href="#-guías-en-español"><b>🇪🇸 Guías en Español</b></a> | <a href="#-english-guides"><b>🇬🇧 English Guides</b></a>
</p>

---

## 🇪🇸 Guías en Español

Bienvenido al centro de documentación oficial del servidor dedicado de ARK: Survival Evolved en Docker. Todas las guías cuentan con acordeones interactivos para alternar entre **Español** e **Inglés**.

1. [**🌐 Guía de Conexión (`connect-guide.md`)**](connect-guide.md#-español)
   - Conexión por LAN local o consola in-game (`open IP:7777`).
   - Agregar el servidor a la lista de **Favoritos de Steam** (`IP:27015`).
   - **Conexión sin abrir puertos usando ZeroTier**: Configuración paso a paso para jugar con amigos sin tocar el router.

2. [**⚙️ Guía de Configuración Avanzada (`configuration-guide.md`)**](configuration-guide.md#-español)
   - Gestión visual de configuraciones (Ajustes, Tasas, Calidad de Vida y Mapas) sin duplicar variables en `.env`.
   - Multiplicadores recomendados para servidores Solo/Dúo (XP, Doma, Crianza, Crafteo).
   - Personalización visual y mediante el editor `.ini` integrado (`GameUserSettings.ini` y `Game.ini`).
   - Argumentos adicionales del ejecutable (`ADDITIONAL_ARGS`) configurados desde la web.

3. [**🛠️ Guía de Administración (`management-guide.md`)**](management-guide.md#-español)
   - Comandos principales de `arkmanager` y consola RCON web interactiva.
   - Gestión de respaldos automáticos y restauración en 1 clic desde el panel web.
   - Notificaciones Webhook a Discord (con selector de idioma y eventos activos) y gestión de Tareas (Reinicios vs. Horario Automático).
   - Diagnóstico y ajuste de salud (`HEALTHCHECK`) para servidores en discos mecánicos (HDD) o con mods pesados.

4. [**📦 Guía de Copias de Seguridad y Restauración (`backup-restore-guide.md`)**](backup-restore-guide.md#-español)
   - Anatomía de archivos de guardado (`.ark`, `*.arkprofile`, `*.arktribe`, `.ini`).
   - Restauración visual e inmediata desde el panel web y copias de seguridad preventivas.
   - Restauración manual detallada paso a paso por SFTP (FileZilla / WinSCP) para backups organizados y legados.
   - Generación de backups manuales con nombre personalizado desde el panel web.

---

## 🇬🇧 English Guides

Welcome to the official documentation center for the ARK: Survival Evolved Dedicated Server in Docker. All guides feature interactive collapsible sections to switch between **English** and **Spanish**.

1. [**🌐 Connection Guide (`connect-guide.md`)**](connect-guide.md#-english)
   - Connecting via Local LAN or in-game console (`open IP:7777`).
   - Adding your server to **Steam Favorites** (`IP:27015`).
   - **Connecting without Port Forwarding via ZeroTier**: Step-by-step setup to play with friends without touching your router.

2. [**⚙️ Advanced Configuration Guide (`configuration-guide.md`)**](configuration-guide.md#-english)
   - Visual settings management (Settings, Rates, QoL rules, and Maps) without duplicate `.env` variables.
   - Recommended rates for Solo/Duo servers (XP, Taming, Breeding, Crafting).
   - Visual and integrated in-app `.ini` editing (`GameUserSettings.ini` and `Game.ini`).
   - ShooterGameServer flags and additional arguments (`ADDITIONAL_ARGS`) managed via web.

3. [**🛠️ Server Management Guide (`management-guide.md`)**](management-guide.md#-english)
   - Common `arkmanager` commands and web RCON interactive console.
   - Managing automatic backups and 1-click restore from web panel.
   - Discord Webhook alerts (language selector and active event filters) and Tasks management (Scheduled Restarts vs. Power Schedule).
   - Healthcheck diagnostics and tuning (`HEALTHCHECK`) for Mechanical HDDs or heavy mod setups.

4. [**📦 Backup and Restoration Guide (`backup-restore-guide.md`)**](backup-restore-guide.md#-english)
   - ARK save file anatomy (`.ark`, `*.arkprofile`, `*.arktribe`, `.ini`).
   - Visual and immediate restoration from web panel with automatic safety backups.
   - Step-by-step manual SFTP restoration (FileZilla / WinSCP) for organized and legacy archives.
   - On-demand manual backups with custom names from web panel.
