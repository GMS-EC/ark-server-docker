# BUILD THE SERVER IMAGE
FROM cm2network/steamcmd:root

LABEL org.opencontainers.image.title="ARK: Survival Evolved Server with ARK Server Manager Web Panel" \
      org.opencontainers.image.description="ARK Dedicated Server with automated backups, cluster multi-map management & ARK Server Manager Web UI"

# Install system dependencies & Python for ARK Server Manager
RUN dpkg --add-architecture i386 && \
    apt-get update && apt-get install -y --no-install-recommends \
    perl \
    perl-modules \
    libcompress-raw-zlib-perl \
    libcompress-raw-bzip2-perl \
    libio-compress-perl \
    curl \
    lsof \
    libc6-i386 \
    lib32gcc-s1 \
    bzip2 \
    gettext-base \
    procps \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

LABEL name="ark-server-docker" \
      description="ARK: Survival Evolved Dedicated Server Docker container with ARK Server Manager web panel, arkmanager and automated backups"

ENV HOME=/home/steam \
    PUID=1000 \
    PGID=1000 \
    SESSION_NAME="ARK Server" \
    SERVER_PASSWORD="" \
    ADMIN_PASSWORD="adminpass" \
    MAX_PLAYERS=10 \
    WORLD="TheIsland" \
    SERVER_PORT=7777 \
    QUERY_PORT=27015 \
    RCON_PORT=27020 \
    RCON_ENABLED=true \
    SERVER_PVE=false \
    BATTLEEYE=false \
    CLUSTER_ID="" \
    CLUSTER_DIR_OVERRIDE="/home/steam/clusters" \
    MOD_IDS="" \
    ADDITIONAL_ARGS="" \
    BETA="public" \
    UPDATE_ON_START=true \
    ARKST_OUTPUT_FORMATTING=true \
    BACKUP_ENABLED=true \
    BACKUP_INTERVAL_HOURS=6 \
    BACKUP_DIR=/home/steam/ark-backups \
    BACKUP_MAX_COUNT=10 \
    DISCORD_WEBHOOK_URL="" \
    DISCORD_LANGUAGE=es \
    AUTO_RESTART_HOURS=0 \
    SCHEDULE_ENABLED=false \
    SCHEDULE_START="20:00" \
    SCHEDULE_STOP="00:00" \
    TZ=UTC \
    SCHEDULE_WARN_MINUTES=10 \
    XP_MULTIPLIER="" \
    TAME_SPEED_MULTIPLIER="" \
    HARVEST_AMOUNT_MULTIPLIER="" \
    HATCH_SPEED_MULTIPLIER="" \
    MATURATION_SPEED_MULTIPLIER="" \
    MATING_INTERVAL_MULTIPLIER="" \
    CRAFT_SPEED_MULTIPLIER="" \
    PANEL_PORT=8080 \
    PANEL_USER="admin" \
    PANEL_PASSWORD="adminpassword" \
    AUTOSTART_SERVER=true

# Install ark-server-tools
RUN curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh | bash -s steam --install-service --commit=master && \
    ln -sf /usr/local/bin/arkmanager /usr/bin/arkmanager

# Create necessary directories
RUN mkdir -p /home/steam/steamcmd/ark /home/steam/ark-backups /home/steam/clusters /var/log/arktools /etc/arkmanager /app/data && \
    chown -R steam:steam /home/steam/steamcmd/ark /home/steam/ark-backups /home/steam/clusters /var/log/arktools /etc/arkmanager /app

# Setup ARK Server Manager Web Panel
WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r /app/requirements.txt || \
    pip3 install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/app/
COPY web/ /app/web/
RUN chown -R steam:steam /app

COPY ./scripts /home/steam/scripts/
COPY Documents/branding /branding

RUN sed -i 's/\r$//' /home/steam/scripts/*.sh && chmod +x /home/steam/scripts/*.sh

WORKDIR /home/steam

EXPOSE 7777-7800/udp 27015-27035/udp 27020-27035/tcp 8080/tcp

HEALTHCHECK --start-period=30m --interval=1m --timeout=30s --retries=5 \
            CMD /home/steam/scripts/healthcheck.sh

ENTRYPOINT ["/home/steam/scripts/init.sh"]
