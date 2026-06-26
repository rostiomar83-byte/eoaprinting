import pandas as pd
import ta
from config import ADX_THRESHOLD


def get_regime(df: pd.DataFrame) -> str:
    """
    Classifica il regime di mercato basandosi su ADX, Aroon e EMA.
    Returns: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING'
    """
    if len(df) < 50:
        return "RANGING"

    close = df["close"]

    adx_ind = ta.trend.ADXIndicator(df["high"], df["low"], close, window=14)
    adx = adx_ind.adx().iloc[-1]
    adx_pos = adx_ind.adx_pos().iloc[-1]
    adx_neg = adx_ind.adx_neg().iloc[-1]

    aroon = ta.trend.AroonIndicator(df["high"], df["low"], window=25)
    aroon_up = aroon.aroon_up().iloc[-1]
    aroon_down = aroon.aroon_down().iloc[-1]

    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]

    if adx > ADX_THRESHOLD:
        if adx_pos > adx_neg and aroon_up > 70 and ema20 > ema50:
            return "TRENDING_UP"
        if adx_neg > adx_pos and aroon_down > 70 and ema20 < ema50:
            return "TRENDING_DOWN"

    return "RANGING"
