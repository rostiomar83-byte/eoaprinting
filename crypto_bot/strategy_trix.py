"""
TRIX + ADX strategy (rating 9.7)
- TRIX: Triple EMA percentuale — filtra rumore meglio di MACD
- ADX: conferma che il trend è abbastanza forte
- 4H EMA filter: entra solo se sopra EMA50 su 4H (struttura rialzista)
- Volume: richiede 1.2× media 20p (era 0.8× — troppo permissivo)
- Entry: TRIX incrocia signal line al rialzo in trend confermato
- Exit: TRIX incrocia al ribasso O trailing ATR
"""

import pandas as pd
import ta
from config import ADX_THRESHOLD

TRIX_PERIOD = 14
TRIX_SIGNAL = 9        # EMA della TRIX
MIN_ADX_TRIX = 20      # ADX minimo per TRIX
ATR_TRAIL_MULT = 1.8
VOLUME_MULT_TRIX = 1.2  # era 0.8 — filtro volume potenziato


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _trix(close: pd.Series, period: int) -> pd.Series:
    ema1 = _ema(close, period)
    ema2 = _ema(ema1, period)
    ema3 = _ema(ema2, period)
    return ema3.pct_change() * 100


def get_signal_trix(exchange, symbol: str, has_position: bool,
                    regime: str = None, above_4h_ema: bool = True):
    """
    Returns (signal, trix_value, price, atr)
    signal: 'BUY_TRIX', 'SELL_TRIX', 'HOLD'
    above_4h_ema: filtro struttura 4H calcolato in main loop
    """
    if regime == "TRENDING_DOWN" and not has_position:
        return "HOLD", None, None, None

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=200)
    except Exception:
        return "HOLD", None, None, None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if len(df) < 100:
        return "HOLD", None, None, None

    close = df["close"]
    price = close.iloc[-1]

    # ATR
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]

    # ADX
    adx = ta.trend.ADXIndicator(df["high"], df["low"], close, window=14).adx().iloc[-1]
    if adx < MIN_ADX_TRIX:
        return "HOLD", None, price, atr

    # TRIX e signal line
    trix = _trix(close, TRIX_PERIOD)
    signal_line = _ema(trix, TRIX_SIGNAL)

    trix_now = trix.iloc[-1]
    trix_prev = trix.iloc[-2]
    sig_now = signal_line.iloc[-1]
    sig_prev = signal_line.iloc[-2]

    # Volume filter potenziato
    vol_avg = df["volume"].rolling(20).mean().iloc[-1]
    vol_now = df["volume"].iloc[-1]
    vol_ok = vol_now > vol_avg * VOLUME_MULT_TRIX

    # --- ENTRATA: crossover TRIX al rialzo + 4H EMA filter ---
    if not has_position and above_4h_ema:
        bullish_cross = (trix_prev < sig_prev) and (trix_now > sig_now)
        trix_positive = trix_now > 0
        if bullish_cross and trix_positive and vol_ok:
            return "BUY_TRIX", round(trix_now, 4), price, atr

    # --- USCITA: crossover TRIX al ribasso ---
    if has_position:
        bearish_cross = (trix_prev > sig_prev) and (trix_now < sig_now)
        if bearish_cross:
            return "SELL_TRIX", round(trix_now, 4), price, atr

    trix_val = round(trix_now, 4) if trix_now == trix_now else None
    return "HOLD", trix_val, price, atr
