#!/bin/bash
# Watchdog: rilancia il bot se crasha
BOT_DIR="$HOME/crypto_bot"
LOG="$BOT_DIR/watchdog.log"
PIDFILE="$BOT_DIR/bot.pid"

cd "$BOT_DIR" || exit 1

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] Avvio main.py" >> "$LOG"
    python3 main.py >> "$BOT_DIR/nohup.log" 2>&1
    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] main.py uscito con codice $EXIT_CODE" >> "$LOG"
    sleep 10
done
