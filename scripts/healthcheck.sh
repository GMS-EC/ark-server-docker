#!/bin/bash
set -e

# 1. Verify that ShooterGameServer process exists
if ! pgrep "ShooterGameServer" > /dev/null 2>&1; then
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
