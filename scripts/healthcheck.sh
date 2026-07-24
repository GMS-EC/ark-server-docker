#!/bin/bash
set -e

# 0. If schedule is enabled and server is outside window, process is expected to be stopped
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

    if [ "$_IN_WINDOW" = "false" ] && ! pgrep -f "ShooterGameServer" > /dev/null 2>&1; then
        exit 0
    fi
fi

# 1. Verify that ShooterGameServer process exists
if ! pgrep -f "ShooterGameServer" > /dev/null 2>&1; then
    exit 1
fi

# 2. Query arkmanager for server online status
STATUS_OUTPUT=$(su - steam -c "arkmanager status @main" 2>/dev/null || arkmanager status @main 2>/dev/null || true)

if echo "$STATUS_OUTPUT" | grep -qi "Server online:[[:space:]]*Yes"; then
    exit 0
fi

# 3. If process exists but server is not yet online (or arkmanager didn't respond),
# return exit 1. Docker treats exit 1 during --start-period as 'starting',
# avoiding aggressive restarts while allowing unhealthy detection if stuck past start-period.
exit 1
