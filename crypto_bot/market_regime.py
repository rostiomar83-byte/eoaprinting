import pandas as pd
import ta
from config import ADX_THRESHOLD


def get_regime(df: pd.DataFrame) -> str:
    """
    Classifica il regime di mercato basandosi su ADX, Aroon e EMA.
    Returns: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING'

    Fix v4.8: la versione precedente richiedeva ADX + Aroon>70 + EMA tutti
    simultaneamente → troppo strict → con ADX 33-40 tornava RANGING anche in
    trend forti, permettendo al MR di comprare contro il trend.
    Ora: se ADX > soglia, si prova ogni combinazione in ordine di certezza e
    si torna sempre TRENDING (mai RANGING con ADX alto).
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
        # Conferma forte: DI+ + EMA
        if adx_pos > adx_neg and ema20 > ema50:
            return "TRENDING_UP"
        if adx_neg > adx_pos and ema20 < ema50:
            return "TRENDING_DOWN"
        # Conferma parziale: Aroon + EMA
        if aroon_up > aroon_down and ema20 > ema50:
            return "TRENDING_UP"
        if aroon_down > aroon_up and ema20 < ema50:
            return "TRENDING_DOWN"
        # Fallback: solo DI+/DI- (ADX già alto, trend in atto)
        return "TRENDING_UP" if adx_pos >= adx_neg else "TRENDING_DOWN"

    return "RANGING"
