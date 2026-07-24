#BUILD THE SERVER IMAGE
FROM --platform=linux/amd64 cm2network/steamcmd:root

LABEL org.opencontainers.image.title="ARK: Survival Evolved Server" \
      org.opencontainers.image.description="ARK Dedicated Server with automated backups & arkmanager"

# Install dependencies
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
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

LABEL name="ark-server-docker" \
      description="ARK: Survival Evolved Dedicated Server Docker container with arkmanager and automated backups"

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
    CLUSTER_DIR_OVERRIDE="" \
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
    CRAFT_SPEED_MULTIPLIER=""

# Install ark-server-tools
RUN curl -sL https://raw.githubusercontent.com/arkmanager/ark-server-tools/master/netinstall.sh | bash -s steam --install-service

# Create necessary directories
RUN mkdir -p /home/steam/steamcmd/ark /home/steam/ark-backups && \
    chown -R steam:steam /home/steam/steamcmd/ark /home/steam/ark-backups /var/log/arktools

COPY ./scripts /home/steam/scripts/
COPY Documents/branding /branding

RUN chmod +x /home/steam/scripts/*.sh

WORKDIR /home/steam

HEALTHCHECK --start-period=10m --interval=1m --timeout=15s \
            CMD /home/steam/scripts/healthcheck.sh

ENTRYPOINT ["/home/steam/scripts/init.sh"]
