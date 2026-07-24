# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-07-24

### Fixed
- **Healthcheck Sizing for HDDs & Mods**: Updated Dockerfile `HEALTHCHECK` with `--start-period=25m`, `--timeout=30s`, and `--retries=5` to prevent false `unhealthy` container status during slow startup on mechanical HDDs with heavy mod packs.
- **System Timezone Symlinking**: Updated `scripts/init.sh` to dynamically link `/etc/localtime` and `/etc/timezone` to `/usr/share/zoneinfo/${TZ}`, ensuring system utilities (`date`, `arkmanager`, `healthcheck.sh`) evaluate local time correctly.
- **GitHub API Rate Limit Bypass**: Added `--commit=master` flag to `netinstall.sh` in Dockerfile to bypass GitHub API rate-limiting issues during GitHub Actions CI builds.
- **Directory Creation**: Guaranteed `/var/log/arktools` and `/etc/arkmanager` creation in `mkdir -p` prior to `chown` in Dockerfile and `init.sh` to prevent container boot warnings.

### Changed
- **Documentation Refinements**: Added power schedule vs. auto-restart comparison table, HDD healthcheck tuning guide, and aligned default environment variables across README and documentation files.

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
