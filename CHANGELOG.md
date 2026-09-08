# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
