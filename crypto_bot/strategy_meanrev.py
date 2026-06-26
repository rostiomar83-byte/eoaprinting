"""
Mean Reversion strategy con:
- BB lower band touch come filtro entrata (riduce falsi segnali)
- Fast RSI(7) come conferma secondaria
- Cooldown 90 min dopo stop loss (gestito in mean_rev_manager.py)
- Regime: RANGING (normale) o TRENDING_DOWN (soglie più conservative)
"""

from datetime import datetime
import pandas as pd
import ta

MR_RSI_BUY = 35             # soglia RSI per RANGING
MR_RSI_BUY_WEEKEND = 22     # weekend: mercato più volatile
MR_RSI_BUY_TRENDING = 28    # soglia più stretta in downtrend
MR_RSI_EXIT = 58            # uscita normale
MR_RSI_EXIT_TRENDING = 50   # uscita più veloce in downtrend

RSI_FAST_PERIOD = 7
RSI_FAST_OVERSOLD = 32      # Fast RSI: conferma oversold
RSI_FAST_OVERBOUGHT = 68    # Fast RSI: conferma uscita

BB_WINDOW = 20
BB_STD = 2.0                # BB standard: 2 deviazioni


def _fetch_ohlcv(exchange, symbol: str, timeframe: str = "5m", limit: int = 150) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def get_signal_mr(exchange, symbol: str, has_position: bool, regime: str = None):
    """
    Returns (signal, rsi, price, atr)
    signal: 'BUY_MR', 'SELL_MR', 'HOLD'
    """
    if regime not in ("RANGING", "TRENDING_DOWN"):
        return "HOLD", None, None, None

    df = _fetch_ohlcv(exchange, symbol)

    close = df["close"]
    price = close.iloc[-1]

    # ATR per stop loss / take profit
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1]

    # RSI standard (14)
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

    # Fast RSI (7) - conferma secondaria
    rsi_fast = ta.momentum.RSIIndicator(close, window=RSI_FAST_PERIOD).rsi().iloc[-1]

    # Bollinger Bands - filtro entrata/uscita
    bb = ta.volatility.BollingerBands(close, window=BB_WINDOW, window_dev=BB_STD)
    bb_lower = bb.bollinger_lband().iloc[-1]
    bb_upper = bb.bollinger_hband().iloc[-1]
    bb_mid = bb.bollinger_mavg().iloc[-1]

    # VWAP approssimativo su 5m
    vwap = None
    try:
        typical = (df["high"] + df["low"] + close) / 3
        vwap = (typical * df["volume"]).sum() / df["volume"].sum()
    except Exception:
        pass

    in_downtrend = (regime == "TRENDING_DOWN")
    is_weekend = datetime.now().weekday() >= 5

    # --- USCITA ---
    mr_exit_threshold = MR_RSI_EXIT_TRENDING if in_downtrend else MR_RSI_EXIT
    # Uscita anticipata: RSI sopra soglia OPPURE prezzo tocca BB mid in downtrend
    if has_position:
        rsi_exit_ok = rsi >= mr_exit_threshold
        fast_exit_ok = rsi_fast >= RSI_FAST_OVERBOUGHT
        bb_exit_ok = in_downtrend and price >= bb_mid
        if rsi_exit_ok or fast_exit_ok or bb_exit_ok:
            return "SELL_MR", rsi, price, atr

    # --- ENTRATA ---
    if has_position:
        return "HOLD", rsi, price, atr

    if in_downtrend:
        rsi_threshold = MR_RSI_BUY_TRENDING
    elif is_weekend:
        rsi_threshold = MR_RSI_BUY_WEEKEND
    else:
        rsi_threshold = MR_RSI_BUY

    rsi_ok = rsi <= rsi_threshold
    fast_rsi_ok = rsi_fast <= RSI_FAST_OVERSOLD  # Fast RSI conferma oversold
    bb_touch_ok = price <= bb_lower               # Prezzo tocca o rompe BB lower

    if rsi_ok and fast_rsi_ok and bb_touch_ok:
        if vwap is None or price < vwap:
            return "BUY_MR", rsi, price, atr

    return "HOLD", rsi, price, atr
