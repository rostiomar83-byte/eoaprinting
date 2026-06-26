import os

SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD",
    "AVAX/USD", "LINK/USD", "DOGE/USD", "ADA/USD"
]

TRADE_AMOUNT_USDT = 30       # max 4 posizioni × 30 = 120 USDT esposti
TRADE_AMOUNT_15M = 15

VOLUME_FILTER_MULT = 1.2
ADX_THRESHOLD = 25

MAX_OPEN_POSITIONS = 4
MAX_EXPOSURE_PCT = 0.70      # max 70% del capitale esposto

MAX_DAILY_LOSS_USDT = 30
MAX_WEEKLY_LOSS_USDT = 60

HEARTBEAT_HOURS = [8, 14, 20]

ATR_SL_MULT = 2.0
ATR_TP_MULT = 3.5
TRAILING_ATR_MULT = 1.5

RSI_PERIOD = 14

DCA_AMOUNT_USDT = 10         # DCA lunedì mattina

LOOP_SLEEP_SECONDS = 60

LOG_FILE = os.path.expanduser("~/crypto_bot/bot.log")
STATE_FILE = os.path.expanduser("~/crypto_bot/positions.json")
MR_STATE_FILE = os.path.expanduser("~/crypto_bot/mr_positions.json")
