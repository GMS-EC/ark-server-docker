#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/home/steam/bin:$PATH"
set -e

# 1. Verificar si el panel web ARK Server Manager responde correctamente
if curl -sf "http://127.0.0.1:${PANEL_PORT:-8080}/health" > /dev/null 2>&1; then
    exit 0
fi

# Fallback al endpoint /login
if curl -sf "http://127.0.0.1:${PANEL_PORT:-8080}/login" > /dev/null 2>&1; then
    exit 0
fi

# 2. Si el panel aún está inicializando, verificar si ShooterGameServer ya corre
if pgrep -f "ShooterGameServer" > /dev/null 2>&1; then
    exit 0
fi

# 3. Si el horario programado está activo y estamos fuera de la ventana, el proceso puede estar legítimamente detenido
if [ "${SCHEDULE_ENABLED:-false}" = "true" ] && [ -n "$SCHEDULE_START" ] && [ -n "$SCHEDULE_STOP" ]; then
    _NOW_H=$(date +%H)
    _NOW_M=$(date +%M)
    _NOW_MINUTES=$(( 10#$_NOW_H * 60 + 10#$_NOW_M ))
    _START_H="${SCHEDULE_START%%:*}"
    _START_M="${SCHEDULE_START#*:}"
    _START_MINUTES=$(( 10#$_START_H * 60 + 10#$_START_M ))
    _STOP_H="${SCHEDULE_STOP%%:*}"
    _STOP_M="${SCHEDULE_STOP#*:}"
    _STOP_MINUTES=$(( 10#$_STOP_H * 60 + 10#$_STOP_M ))

    if [ "$_START_MINUTES" -le "$_STOP_MINUTES" ]; then
        _IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] && [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
    else
        _IN_WINDOW=$([ "$_NOW_MINUTES" -ge "$_START_MINUTES" ] || [ "$_NOW_MINUTES" -lt "$_STOP_MINUTES" ] && echo true || echo false)
    fi

    if [ "$_IN_WINDOW" = "false" ]; then
        exit 0
    fi
fi

exit 1
