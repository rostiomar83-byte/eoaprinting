#!/bin/bash
# Deploy: copia i file aggiornati da questo repo alla cartella del bot sul VM
# Esegui dal VM: bash ~/eoaprinting/crypto_bot/deploy.sh

BOT_DIR="$HOME/crypto_bot"
REPO_DIR="$HOME/eoaprinting/crypto_bot"

echo "=== Deploy CryptoBot Omar v4 ==="

# Ferma il bot
echo "[1/4] Stop bot..."
pkill -f "python3 main.py" 2>/dev/null
pkill -f "watchdog.sh" 2>/dev/null
sleep 3

# Backup vecchi file
echo "[2/4] Backup..."
cp -r "$BOT_DIR" "${BOT_DIR}_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

# Copia file aggiornati (preserva .env e file di stato json)
echo "[3/4] Copia file..."
for f in config.py market_regime.py strategy_meanrev.py strategy_trix.py \
          strategy_multiTF.py mean_rev_manager.py risk_manager.py \
          telegram_bot.py main.py requirements.txt watchdog.sh; do
    cp "$REPO_DIR/$f" "$BOT_DIR/$f"
    echo "  ✓ $f"
done
chmod +x "$BOT_DIR/watchdog.sh"

# Riavvio
echo "[4/4] Riavvio bot..."
cd "$BOT_DIR"
nohup bash watchdog.sh &
echo "  PID watchdog: $!"

echo "=== Deploy completato ==="
echo "Log: tail -f $BOT_DIR/bot.log"
