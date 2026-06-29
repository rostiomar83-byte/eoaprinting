import os

SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "LINK/USD"
]  # AVAX, DOGE, ADA rimossi: spread/volatilità sfavorevoli per capital ridotto

TRADE_AMOUNT_USDT = 30           # default / fallback
TRADE_AMOUNT_TRENDING_UP = 40    # sizing aggressivo: trend già confermato
TRADE_AMOUNT_RANGING = 25        # sizing conservativo: laterale / segnale più debole

VOLUME_FILTER_MULT = 1.5         # era 1.2 — filtra falsi breakout su volume basso
ADX_THRESHOLD = 25

MAX_OPEN_POSITIONS = 2           # era 4 — concentrazione sui segnali migliori
MAX_EXPOSURE_PCT = 0.70          # max 70% del capitale esposto

MAX_DAILY_LOSS_USDT = 30
MAX_WEEKLY_LOSS_USDT = 60

HEARTBEAT_HOURS = [8, 14, 20]

ATR_SL_MULT = 1.5                # era 2.0 → perdite più piccole per trade
ATR_TP_MULT = 5.0                # era 3.5 → R:R = 1:3.3 (matematica del profitto)
PARTIAL_TP_ATR_MULT = 2.0        # vendi 50% a 2×ATR, sposta SL a breakeven
TRAILING_ATR_MULT = 1.5          # trailing in regime RANGING
TRAILING_ATR_TRENDING_UP = 2.0   # trailing più largo in TRENDING_UP (respira il trend)

RSI_PERIOD = 14

# Costi di esecuzione — Kraken spot, market order (taker)
FEE_RATE = 0.0026               # 0.26% per lato → 0.52% round-trip
# Gate anti-fee-bleed: il partial TP (2×ATR) deve lasciare ≥0.25% NETTO dopo fee.
# Se la volatilità non basta a coprire le commissioni, il trade NON si apre.
MIN_TP1_NET_PCT = 0.0025

DCA_AMOUNT_USDT = 10             # DCA lunedì mattina

TRADE_HOUR_START = 7             # no nuovi ingressi 23:00-07:00 UTC
TRADE_HOUR_END = 23              # sessione asiatica: volume basso, spread alti

# --- Volatility Guard (scudo anti-crollo) ---
# Quando l'ATR% attuale supera VOL_SPIKE_MULT × la sua media storica, la
# volatilità sta esplodendo (tipico prima/durante i crolli): il bot BLOCCA i
# nuovi ingressi. Le posizioni aperte restano gestite normalmente dai loro stop.
# Se BTC entra in spike → risk-off globale (nessun nuovo long su nessun asset).
VOL_GUARD_ENABLED = True
VOL_SPIKE_MULT = 1.8            # 1.8× la volatilità media → blocco ingressi
VOL_BASELINE_PERIODS = 50      # finestra (candele 1h) per la media ATR%

LOOP_SLEEP_SECONDS = 60

LOG_FILE = os.path.expanduser("~/crypto_bot/bot.log")
STATE_FILE = os.path.expanduser("~/crypto_bot/positions.json")
MR_STATE_FILE = os.path.expanduser("~/crypto_bot/mr_positions.json")
TRADES_FILE = os.path.expanduser("~/crypto_bot/trades.jsonl")  # diario strutturato (1 trade per riga)
