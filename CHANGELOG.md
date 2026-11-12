# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-11-12

### Added
- **Sidebar Navigation & Contextual Topbar**: Replaced the crowded horizontal navigation bar with a grouped sidebar (`sidebar.html`: *Operación*, *Infraestructura*, *Sistema*) paired with a contextual `.topbar` (`header.html`) displaying the active section title (`#topbar-section-title`), live server status pill, active cluster selector, logout button, and mobile drawer toggle with backdrop/`Escape` dismissal (`toggleMobileSidebar`, `closeMobileSidebar`).
- **Unified SVG Icon System**: Created a reusable SVG macro library (`web/templates/components/icons.html`) replacing all Unicode/UI emojis across navigation items, section headers, cards, alerts, toast notifications (`app.js`), and the File Explorer (`files.js`).
- **Shared Popular Mods Catalog**: Extracted the Steam Workshop popular mods list into a shared Jinja macro (`web/templates/components/popular_mods.html` `popular_mods_list`) reused by both the Mods and Server Installer tabs.
- **Modular FastAPI Routers**: Split route handlers out of monolithic `app/main.py` into 8 domain routers under `app/routers/` (`backups.py`, `cluster.py`, `files.py`, `mods.py`, `players.py`, `settings.py`, `tasks.py`, `webhooks.py`).
- **Shared Process & Filesystem Utilities**: Added `app/core/process_utils.py` (`find_ark_processes()` with thread-safe TTL cache and `ArkProcessInfo` snapshots) and expanded `app/core/fs_utils.py` with shared `is_subpath()`, atomic write helpers (`atomic_write_text()`, `atomic_write_json()`), and TTL-cached directory sizing (`get_dir_size_cached()`, `invalidate_dir_size_cache()`).
- **File Explorer Drag-and-Drop Queue & Path Persistence**: Added persistent current-folder navigation (`sessionStorage`), drag-and-drop upload overlay (`#files-drop-overlay`), and upload queue state management in `web/static/js/files.js`.
- **Automated Changelog-Driven Versioning & Footer Display**: Added `get_app_version()` (`app/config.py`) reading `CHANGELOG.md` directly (copied into Docker via `Dockerfile`) to drive `FastAPI.version`, Jinja's `get_app_version()`, `<span class="footer-ver">` in `footer.html`, static asset query cache-busters (`?v=...` in `base.html` and `index.html`), and dynamic Service Worker cache naming in `web/static/sw.js`; removed the duplicate version badge from `sidebar.html`.
- **Automated Test Suite & Dev Dependencies**: Added `requirements-dev.txt`, `pytest.ini`, and 30 unit/integration tests across `tests/test_phase1_security.py`, `tests/test_phase2_backend.py`, `tests/test_phase3_4.py`, and `tests/test_phase5_coverage.py`, along with updated verification instructions in `CONTRIBUTING.md`.
- **Live Task Scheduler Status API**: Added `/api/tasks/status` endpoint and live scheduler status display in the Tasks tab.

### Changed
- **100% Opaque Visual Palette & CSS Architecture**: Removed all alpha transparency, translucent overlays, and `backdrop-filter` rules in `web/static/css/style.css`; consolidated duplicate CSS rules; replaced nested `.card` containers with lightweight `.subcard`, `.subcard-summary`, and `.subcard-check` components; migrated 450+ static inline styles into reusable CSS classes (`.tab-header`, `.setting-grid`, `.kpi-row`, `.drop-overlay`, `.upload-widget`, `.modal-box-*`); and unified responsive breakpoints.
- **Cross-Tab UI Deduplication**: Streamlined `banner.html`, replaced duplicated CPU/RAM/Disk widgets in `console.html` with a compact `.console-control-bar`, and removed redundant manual quick-action buttons from `tasks.html` and circular navigation cards from `backups.html` and `settings.html`.
- **Backend Performance & Module Structure**: Precompiled INI section/key-value regexes in `app/core/ark_settings_manager.py`, removed circular dependency on settings from `cluster_manager.py`, added debounced JSON persistence (`flush()`) in `app/core/activity_manager.py`, and improved data directory resolution in `app/config.py`.
- **Pinned Runtime Dependencies & Git Ignore Rules**: Pinned exact package versions in `requirements.txt` and expanded `.gitignore` to exclude `.secret_key`, runtime JSON config/state files, `backups/`, `.pytest_cache/`, and local virtual environments.

### Security
- **Session Nonces, Revocation & API Rate Limiting**: Added per-token nonces and SHA-256 token revocation on `/logout`, fail-closed empty `PANEL_PASSWORD` enforcement (`is_auth_bypassed()` opt-in via `ALLOW_EMPTY_PASSWORD=true`), pruned and bounded the in-memory login rate-limit tracker, enforced constant-time credential verification, added sliding-window endpoint rate limiting (`require_api_rate_limit`) in `app/core/security.py`, and added HTTPS `Secure` cookies, HSTS, `Content-Security-Policy`, and `Permissions-Policy` headers.
- **File Manager & Backup Archive Hardening**: Added `PROTECTED_FILES` access blocking, storage quota validation, symlink blocking, sanitized 500 internal error responses (no exception detail leakage), ZipSlip/TarSlip path traversal checks, and ZipBomb ratio (`MAX_ZIP_COMPRESSION_RATIO = 100`) and uncompressed size guards in `app/core/file_manager.py`, `app/routers/files.py`, and `app/core/backup_manager.py`.
- **Webhook SSRF Protection & Redaction**: Added `is_safe_webhook_url()` DNS/private/loopback/link-local IP validation with `follow_redirects=False` and `mask_webhook_url()` masking in `app/core/webhook_manager.py`.
- **RCON, CLI & Config Sanitization**: Stripped NUL/CR/LF control characters, added `redact_rcon_command()` error-log redaction, `sanitize_steam_id()`, and shared `escape_rcon_quoted_text()` (fixing `PlayerManager.message_player()` quote escaping and validating SteamIDs in `app/routers/players.py` and `app/core/rcon_client.py`); added `_sanitize_cli_param()` in `app/core/cluster_manager.py`, Workshop ID validation, and quote/newline sanitization in `scripts/generate-config.sh`; and added default/empty `PANEL_PASSWORD`/`ADMIN_PASSWORD` startup warnings in `scripts/init.sh`.
- **Container Install Verification, SRI & XSS Hardening**: Verified `arkmanager-netinstall.sh` download size and shebang prior to execution in `Dockerfile`, added Chart.js CDN Subresource Integrity (`integrity` + `crossorigin="anonymous"`) in `web/templates/base.html`, escaped dynamic HTML (including `escapeHtml(nodeTitle)`) and inline handler strings across `app.js` and `files.js`, and capped DOM audit-log rendering to the 100 most recent entries.

### Fixed
- **Non-Cancelling WebSocket Heartbeat & Reconnection**: Replaced timeout-wrapped `receive_text` with a background zero-width keepalive task in `app/main.py` so idle console connections stay alive without dropping incoming commands, cleaned up orphan reconnect sockets, and halted reconnect loops on `1008` session expiry.
- **Task Scheduler & Safe-Restart Reliability**: Prevented duplicate safe-restart countdown tasks, improved persisted save feedback/reload in `tasks.html`, and fixed shared `/api/metrics` cache mutation.
- **Player History Persistence**: Debounced JSON writes and pruned stale or oversized entries in `app/core/player_manager.py`.
- **Mobile Banner Toggle Target**: Fixed the mobile overview toggle button in `web/templates/components/banner.html` to target `#server-overview-banner`.

## [2.0.0] - 2026-09-08

### Added
- **ARK Server Manager Web Panel**: Modern, responsive web management interface built with FastAPI, WebSockets, Chart.js, and vanilla CSS inspired by Dockraft.
- **Multi-Map Cluster Management**: Centralized management for up to 12 official ARK maps sharing the same obelisk directory (`/clusters/ArkCluster`) with automatic port and save directory isolation.
- **Steam Workshop Mods Manager**: Integrated visual catalog with 1-click popular presets (S+, Awesome Spyglass, Dino Storage v2, etc.) and auto-updater.
- **Web File Manager & Editor**: Integrated file explorer with syntax highlighting, file creation, editing, ZIP extraction, and direct access to map saves and cluster obelisk data.
- **Visual Backup & Restore**: Browser-based snapshot creation, download, and one-click restore with automated safety backups.
- **Interactive Webhooks Configurator**: Discord notification builder with embed color customization and test notification delivery.
- **Survivor & Tribe Management**: Live player tracker with kick/ban moderation and tribe administration.
- **Task Scheduler**: Visual interface for power schedules, automated backups, log rotation, and periodic server restarts.
- **Security & Rate Limiting**: 5-attempt login lockout (10-minute ban), 60-minute token expiration, and persistent session encryption.

### Changed
- **Centralized Management**: Replaced obsolete standalone bash scripts with centralized web panel APIs and management background tasks.
- **Docker Compose Ports**: Enabled active port ranges by default for Game UDP (`7777-7800`), Query UDP (`27015-27035`), and RCON TCP (`27020-27035`).
- **Data Protection**: Automatic `AltSaveDir` isolation for all cluster maps to prevent map overwrite or accidental data loss.

### Fixed
- **Container Cgroups RAM Limit**: Accurately detects container RAM limits via cgroups v1/v2 rather than host system RAM, reflecting Docker/CasaOS resource boundaries.
- **ShooterGameServer Live Process RAM**: Direct inspection of the ShooterGameServer process RSS instead of the arkmanager bash wrapper PID, showing true server memory consumption.
- **Top Banner Metric Alignment**: Fixed .overview-item layout to keep values closely paired with their respective labels.
- **Server Readiness Console Notification**: Real-time socket and RCON probe broadcasting [OK] ¡SERVIDOR DE ARK 100% ONLINE Y DISPONIBLE! in the terminal upon complete boot.
- **Web UI & Docker Environment Auto-Sync**: Preserves and imports Docker environment variables (Discord webhooks, schedules, backup intervals) directly into runtime config so they can be edited inside the UI without duplication.
- **Tasks & Automations Grid Alignment**: Balanced equal-height cards for power schedules, automated backups, and dino wipes.
- **Windows CRLF Compatibility**: Enforced Unix LF line endings across all bash scripts and templates, plus Docker build-time `sed` sanitization.

## [1.1.1] - 2026-07-24

### Fixed
- **Healthcheck Sizing for HDDs & Mods**: Updated Dockerfile `HEALTHCHECK` with `--start-period=25m`, `--timeout=30s`, and `--retries=5` to prevent false `unhealthy` container status during slow startup on mechanical HDDs with heavy mod packs.
- **System Timezone Symlinking**: Updated `scripts/init.sh` to dynamically link `/etc/localtime` and `/etc/timezone` to `/usr/share/zoneinfo/${TZ}`, ensuring system utilities (`date`, `arkmanager`, `healthcheck.sh`) evaluate local time correctly.
- **GitHub API Rate Limit Bypass**: Added `--commit=master` flag to `netinstall.sh` in Dockerfile to bypass GitHub API rate-limiting issues during GitHub Actions CI builds.
- **Directory Creation**: Guaranteed `/var/log/arktools` and `/etc/arkmanager` creation in `mkdir -p` prior to `chown` in Dockerfile and `init.sh` to prevent container boot warnings.
- **Binary PATH Export**: Exported `/usr/local/bin` in container scripts (`init.sh`, `start.sh`, `healthcheck.sh`, `restore.sh`) to prevent `arkmanager: command not found` errors when switching users with `su - steam`.
- **Local Time Log Formatting**: Updated `scripts/start.sh` backup messages to display local time format instead of forced UTC.
- **RCON Broadcast Error Suppression**: Muted stderr output on `arkmanager broadcast` during schedule warning when RCON port is offline during early startup.

### Changed
- **Documentation Refinements**: Added power schedule vs. auto-restart comparison table, HDD healthcheck tuning guide, and aligned default environment variables across README and documentation files.
- **Container RAM Limit Variable (`MEM_LIMIT`)**: Added configurable `MEM_LIMIT` variable (default: `12G`) with `mem_limit` and `deploy.resources.limits.memory` in `docker-compose.yml`, `.env.example`, README, and configuration guides.

## [1.1.0] - 2026-07-23

### Added
- **Automatic Power Schedule (`SCHEDULE_ENABLED`)**: Automated game process start/stop schedule (`SCHEDULE_START`, `SCHEDULE_STOP`, `SCHEDULE_WARN_MINUTES`, `TZ`) to conserve CPU/RAM during off-peak hours while keeping the Docker container running.
- **Active Player Protection**: Power schedule postpones process shutdown if active players are connected.
- **Timezone Support (`TZ`)**: Container level timezone support via `tzdata` package to evaluate schedules and log timestamps in local time.
- **Schedule-aware Healthcheck**: Updated `scripts/healthcheck.sh` to report healthy status when the ARK process is intentionally stopped outside the active window.
- **Automated Backups & Rotation**: Count-based rotation (`BACKUP_MAX_COUNT`) and configurable backup intervals (`BACKUP_INTERVAL_HOURS`).
- **One-Command Save Restoration**: Executable `scripts/restore.sh` script with automatic pre-restoration safety backups.
- **Multi-language Discord Webhooks**: Real-time channel notifications for server events, backups, restarts, and power schedule in Spanish or English (`DISCORD_LANGUAGE=es/en`).
- **Scheduled Restarts**: Periodic automated server restarts (`AUTO_RESTART_HOURS`) with in-game warnings and pre-save.
- **Mod Installation Error Handling**: Tolerant Steam Workshop mod installation script handling missing or private mod IDs gracefully.
- **Environment Variable Validation**: Early format and integer validation for port, schedule, backup, and rate environment variables.
- **Repository Guidelines & Governance**: Added `.gitattributes` for LF normalization, `.gitignore`, `CONTRIBUTING.md`, and issue templates.
- **CI Build & Lint Workflows**: GitHub Actions workflow for ShellCheck linting and dry-run Docker image build verification on PRs.

### Changed
- **Default RCON Security**: Updated `docker-compose.yml` quickstart example default to `RCON_ENABLED=false` to prevent accidental public RCON exposure with default credentials.
- **Documentation**: Expanded README.md and management guides with RAM/CPU sizing references and multi-map cluster resource scaling guidelines.

### Fixed
- **Line Ending Normalization**: Converted `Dockerfile`, `docker-compose.yml`, `.env.example`, and repository scripts to Unix LF line endings.
