"""
MultiTimeframe trend-following strategy (5m + 15m).
- BUY solo in TRENDING_UP + sopra 4H EMA50: RSI pullback 40-58, EMA rising, volume ok
- BB Squeeze: breakout in RANGING con conferma 4H EMA + volume potenziato
- SELL solo in TRENDING_DOWN: RSI 42-60, EMA falling, volume ok
"""

import pandas as pd
import ta
from config import ADX_THRESHOLD, VOLUME_FILTER_MULT

RSI_BUY_MIN = 40
RSI_BUY_MAX = 58
RSI_SELL_MIN = 42
RSI_SELL_MAX = 60

BB_SQUEEZE_MULT = 0.6   # BB bandwidth < 60% della media storica → squeeze


def _fetch(exchange, symbol: str, timeframe: str, limit: int = 150) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df


def _detect_bb_squeeze(df: pd.DataFrame) -> bool:
    """Restituisce True se il mercato è in compressione (BB squeeze)."""
    close = df["close"]
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bandwidth = bb.bollinger_wband()
    current_bw = bandwidth.iloc[-1]
    avg_bw = bandwidth.rolling(50).mean().iloc[-1]
    if avg_bw and avg_bw > 0:
        return current_bw < avg_bw * BB_SQUEEZE_MULT
    return False


def get_signal_multitf(exchange, symbol: str, has_position: bool,
                        regime: str = None, above_4h_ema: bool = True):
    """
    Returns (signal, rsi, price, atr)
    signal: 'BUY_5M', 'BUY_15M', 'SELL_5M', 'SELL_15M', 'HOLD'
    above_4h_ema: filtro struttura 4H calcolato in main loop (evita duplicare fetch)
    """
    try:
        df_5m = _fetch(exchange, symbol, "5m")
        df_15m = _fetch(exchange, symbol, "15m")
    except Exception:
        return "HOLD", None, None, None

    if len(df_5m) < 60 or len(df_15m) < 60:
        return "HOLD", None, None, None

    close_5m = df_5m["close"]
    close_15m = df_15m["close"]
    price = close_5m.iloc[-1]

    # ATR su 5m
    atr = ta.volatility.AverageTrueRange(df_5m["high"], df_5m["low"], close_5m, window=14).average_true_range().iloc[-1]

    # RSI
    rsi_5m = ta.momentum.RSIIndicator(close_5m, window=14).rsi().iloc[-1]

    # EMA trend
    ema20_5m = ta.trend.EMAIndicator(close_5m, window=20).ema_indicator().iloc[-1]
    ema50_5m = ta.trend.EMAIndicator(close_5m, window=50).ema_indicator().iloc[-1]
    ema_up = ema20_5m > ema50_5m
    ema_down = ema20_5m < ema50_5m

    # Volume
    vol_avg = df_5m["volume"].rolling(20).mean().iloc[-1]
    vol_now = df_5m["volume"].iloc[-1]
    vol_ok = vol_now > vol_avg * VOLUME_FILTER_MULT

    # BB squeeze breakout (RANGING + struttura 4H rialzista)
    if regime == "RANGING" and above_4h_ema:
        squeeze = _detect_bb_squeeze(df_5m)
        if squeeze and not has_position:
            last_candle_bull = df_5m["close"].iloc[-1] > df_5m["open"].iloc[-1]
            if last_candle_bull and vol_ok:
                return "BUY_5M", rsi_5m, price, atr

    # --- BUY in TRENDING_UP + sopra 4H EMA50 ---
    if regime == "TRENDING_UP" and not has_position and above_4h_ema:
        rsi_ok = RSI_BUY_MIN <= rsi_5m <= RSI_BUY_MAX
        if rsi_ok and ema_up and vol_ok:
            # Conferma 15m
            rsi_15m = ta.momentum.RSIIndicator(close_15m, window=14).rsi().iloc[-1]
            ema20_15m = ta.trend.EMAIndicator(close_15m, window=20).ema_indicator().iloc[-1]
            ema50_15m = ta.trend.EMAIndicator(close_15m, window=50).ema_indicator().iloc[-1]
            if ema20_15m > ema50_15m:
                return "BUY_5M", rsi_5m, price, atr

    # --- SELL in TRENDING_DOWN (uscita posizione long) ---
    if regime == "TRENDING_DOWN" and has_position:
        rsi_ok = RSI_SELL_MIN <= rsi_5m <= RSI_SELL_MAX
        if rsi_ok and ema_down and vol_ok:
            return "SELL_5M", rsi_5m, price, atr

    return "HOLD", rsi_5m, price, atr
