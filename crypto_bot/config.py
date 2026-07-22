import os

SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "LINK/USD"
]  # v4.8: XRP rimosso (storico negativo). AVAX, DOGE, ADA rimossi precedentemente.

TRADE_AMOUNT_USDT = 15           # default / fallback
TRADE_AMOUNT_TRENDING_UP = 20    # v4.8: ridotto da 40 (breakout non ancora provato)
TRADE_AMOUNT_RANGING = 15        # v4.8: ridotto da 25

VOLUME_FILTER_MULT = 1.5         # era 1.2 — filtra falsi breakout su volume basso
ADX_THRESHOLD = 25

MAX_OPEN_POSITIONS = 2           # era 4 — concentrazione sui segnali migliori
MAX_EXPOSURE_PCT = 0.45          # v4.8: ridotto da 70% — protezione capitale prima

MAX_DAILY_LOSS_USDT = 5          # v4.8: ridotto da 30 — su $210 era troppo permissivo
MAX_WEEKLY_LOSS_USDT = 12        # v4.8: ridotto da 60

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

# --- Separazione regime ↔ strategia (data-driven) ---
# I dati reali (/stats) mostrano che i motori breakout (MultiTF, TRIX) perdono
# sistematicamente in mercato RANGING (0% win rate) mentre il Mean Reversion
# vince (83%). In un laterale le "rotture" sono finte → whipsaw.
# Con questo flag i motori breakout entrano SOLO in TRENDING_UP, dove hanno edge.
# In RANGING lavora solo il Mean Reversion. Reversibile: metti False per tornare indietro.
BREAKOUT_ONLY_TRENDING_UP = True

# v4.12: MR disabilitato — 56 trade dimostrano RANGING WR 36% / -$2.49
# Reversibile: metti True per riattivare. Le posizioni MR aperte vengono
# comunque gestite (SL/TP/TIMEOUT) anche con MR_ENABLED = False.
MR_ENABLED = False

MIN_CAPITAL_USD = 160            # hard stop: sotto questa equity il bot si mette in pausa automatica

LOOP_SLEEP_SECONDS = 60

LOG_FILE = os.path.expanduser("~/crypto_bot/bot.log")
STATE_FILE = os.path.expanduser("~/crypto_bot/positions.json")
MR_STATE_FILE = os.path.expanduser("~/crypto_bot/mr_positions.json")
TRADES_FILE = os.path.expanduser("~/crypto_bot/trades.jsonl")  # diario strutturato (1 trade per riga)
