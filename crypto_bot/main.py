"""
CryptoBot Omar v4.4 — Professional Edition
Engines attivi:
  1. MultiTF 5m/15m — trend following + 4H EMA filter (TRENDING_UP)
  2. TRIX+ADX 15m   — trend following + 4H EMA + volume 1.2× (TRENDING_UP/RANGING)
  3. Mean Reversion  — RSI + BB touch + Fast RSI (RANGING + TRENDING_DOWN)
Miglioramenti v4.1:
  - Time filter: nessun nuovo ingresso 23:00-07:00 UTC (sessione asiatica)
  - R:R 1:3.3  (SL=1.5 ATR, TP=5 ATR)
  - Partial TP: vendi 50% a 2×ATR, sposta SL a breakeven
  - Sizing adattivo: $40 TRENDING_UP, $25 RANGING
  - 4H EMA50 filter su MultiTF e TRIX
  - Volume filter 1.5× (MultiTF) e 1.2× (TRIX)
  - Max 2 posizioni MultiTF/TRIX simultanee (era 4)
  - Cooldown 60 min dopo SL perdente
  - Trailing stop 2.0 ATR in TRENDING_UP (era 1.5)
  - Simboli ridotti a 5 top-liquidity
Obiettivo: +$5-10 USD/giorno su capitale ~$210 USDT Kraken
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta

import ccxt
from dotenv import load_dotenv

load_dotenv()

# --- Config & moduli ---
from config import (
    SYMBOLS, LOOP_SLEEP_SECONDS, HEARTBEAT_HOURS,
    ATR_SL_MULT, ATR_TP_MULT, TRAILING_ATR_MULT, TRAILING_ATR_TRENDING_UP,
    PARTIAL_TP_ATR_MULT, TRADE_AMOUNT_USDT,
    TRADE_AMOUNT_TRENDING_UP, TRADE_AMOUNT_RANGING,
    LOG_FILE, DCA_AMOUNT_USDT, STATE_FILE,
    TRADE_HOUR_START, TRADE_HOUR_END,
    FEE_RATE, MIN_TP1_NET_PCT, MAX_OPEN_POSITIONS,
    VOL_GUARD_ENABLED, VOL_SPIKE_MULT, VOL_BASELINE_PERIODS,
)
from market_regime import get_regime
from strategy_multiTF import get_signal_multitf
from strategy_trix import get_signal_trix
from strategy_meanrev import get_signal_mr
from mean_rev_manager import MeanRevManager, MR_AMOUNT_USD
from risk_manager import RiskManager
import telegram_bot as tg

# ------------------------------------------------------------------ #
# Logging                                                              #
# ------------------------------------------------------------------ #

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
    datefmt="%Y-%m-%d %H:%M:%S",
)


def log(msg: str):
    logging.info(msg)


# ------------------------------------------------------------------ #
# Exchange                                                             #
# ------------------------------------------------------------------ #

exchange = ccxt.kraken({
    "apiKey": os.getenv("KRAKEN_API_KEY", ""),
    "secret": os.getenv("KRAKEN_PRIVATE_KEY", ""),
    "enableRateLimit": True,
})

# ------------------------------------------------------------------ #
# State                                                                #
# ------------------------------------------------------------------ #

def _load_positions() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        if data:
            log(f"[STATE] Caricate {len(data)} posizioni da disco: {list(data.keys())}")
        return data
    except Exception:
        return {}

def _save_positions():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(positions, f, indent=2)

positions: dict = _load_positions()   # symbol → {entry_price, sl, tp, qty, engine, atr, ...}
mr_manager = MeanRevManager()
risk_manager = RiskManager()

multitf_cooldown: dict = {}   # symbol → datetime fine cooldown dopo SL perdente
MULTITF_COOLDOWN_MIN = 60


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def get_balance() -> float:
    try:
        bal = exchange.fetch_balance()
        for k in ("USD", "USDT", "ZUSD"):
            if k in bal and bal[k].get("free", 0) > 0:
                return bal[k]["free"]
        return 0.0
    except Exception as e:
        log(f"[BALANCE ERR] {e}")
        return 0.0


def _net_pnl(entry: float, exit_price: float, qty: float) -> float:
    """PnL al netto delle commissioni Kraken (taker su entrambi i lati)."""
    gross = (exit_price - entry) * qty
    fees = (entry + exit_price) * qty * FEE_RATE
    return gross - fees


def _amt(symbol: str, qty: float) -> float:
    """Arrotonda la quantità alla precisione richiesta da Kraken (evita reject)."""
    try:
        return float(exchange.amount_to_precision(symbol, qty))
    except Exception:
        return qty


def _atr_valid(atr) -> bool:
    """ATR utilizzabile: non None, non NaN, > 0. Evita posizioni senza stop."""
    return atr is not None and atr == atr and atr > 0


def _edge_ok(atr: float, price: float) -> bool:
    """
    True se il partial TP (PARTIAL_TP_ATR_MULT×ATR) copre il round-trip fee
    + un margine netto minimo. Blocca gli scalp che bruciano solo commissioni.
    """
    if not _atr_valid(atr) or price <= 0:
        return False
    tp1_move_pct = (PARTIAL_TP_ATR_MULT * atr) / price
    required = 2 * FEE_RATE + MIN_TP1_NET_PCT
    return tp1_move_pct >= required


def _open_value() -> float:
    """Valore reale delle posizioni aperte (multi + MR), a prezzi d'ingresso."""
    multi = sum(p["qty"] * p["entry_price"] for p in positions.values())
    mr = sum(p["qty"] * p["entry_price"] for p in mr_manager.positions.values())
    return multi + mr


def _atr_1h(df) -> float:
    """ATR(14) su candele 1h — riferimento per dimensionare SL/TP/trailing."""
    try:
        import ta
        atr = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14
        ).average_true_range().iloc[-1]
        return float(atr)
    except Exception:
        return None


def _vol_ratio(df) -> float:
    """
    Rapporto tra volatilità attuale e media storica (ATR% su 1h).
    >1 = sopra la norma, >VOL_SPIKE_MULT = spike (rischio crollo).
    Ritorna 1.0 (neutro) in caso di errore → fail-safe, non blocca.
    """
    try:
        import ta
        atr_series = ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"], window=14
        ).average_true_range()
        atr_pct = atr_series / df["close"]
        baseline = atr_pct.rolling(VOL_BASELINE_PERIODS).mean().iloc[-1]
        current = atr_pct.iloc[-1]
        if baseline and baseline > 0:
            return float(current / baseline)
        return 1.0
    except Exception:
        return 1.0


def place_buy(symbol: str, amount_usd: float, price: float, sl: float, tp: float,
              engine: str, atr: float = 0.0, regime: str = "RANGING"):
    qty = _amt(symbol, amount_usd / price)
    trail_mult = TRAILING_ATR_TRENDING_UP if regime == "TRENDING_UP" else TRAILING_ATR_MULT
    tp1 = price + PARTIAL_TP_ATR_MULT * atr if atr > 0 else float("inf")
    try:
        exchange.create_market_buy_order(symbol, qty)
        positions[symbol] = {
            "entry_price": price,
            "sl": sl,
            "tp": tp,
            "tp1": tp1,
            "qty": qty,
            "engine": engine,
            "entry_time": datetime.now().isoformat(),
            "trailing_sl": sl,
            "trailing_mult": trail_mult,
            "atr": atr,
            "half_sold": False,
        }
        msg = (f"✅ BUY {engine} {symbol}\n"
               f"  Prezzo: {price:.4f}\n"
               f"  SL: {sl:.4f}  TP1: {tp1:.4f}  TP: {tp:.4f}\n"
               f"  Qty: {qty:.4f}  ~{amount_usd:.0f}$  trail×{trail_mult}")
        log(msg)
        tg.send_message(msg)
        _save_positions()
    except Exception as e:
        log(f"[BUY ERR {symbol}] {e}")
        tg.send_message(f"❌ BUY error {symbol}: {e}")


def place_sell(symbol: str, reason: str):
    pos = positions.get(symbol)
    if not pos:
        return
    try:
        exchange.create_market_sell_order(symbol, _amt(symbol, pos["qty"]))
        ticker = exchange.fetch_ticker(symbol)
        exit_price = ticker["last"]
        pnl = _net_pnl(pos["entry_price"], exit_price, pos["qty"])
        risk_manager.record_pnl(pnl)

        # Cooldown 60min dopo SL perdente: evita re-entry immediato sullo stesso asset
        if reason == "TRAILING_SL" and pnl < 0:
            multitf_cooldown[symbol] = datetime.now() + timedelta(minutes=MULTITF_COOLDOWN_MIN)
            log(f"[COOLDOWN] {symbol} bloccato {MULTITF_COOLDOWN_MIN}min fino a "
                f"{multitf_cooldown[symbol].strftime('%H:%M')}")

        emoji = "✅" if pnl >= 0 else "🔴"
        msg = (f"{emoji} SELL {pos['engine']} {symbol} [{reason}]\n"
               f"  Entrata: {pos['entry_price']:.4f} → Uscita: {exit_price:.4f}\n"
               f"  PnL: {pnl:+.3f}$")
        log(msg)
        tg.send_message(msg)
        positions.pop(symbol, None)
        _save_positions()
    except Exception as e:
        log(f"[SELL ERR {symbol}] {e}")
        tg.send_message(f"❌ SELL error {symbol}: {e}")


# ------------------------------------------------------------------ #
# Telegram handlers                                                    #
# ------------------------------------------------------------------ #

def _cmd_balance():
    bal = get_balance()
    tg.send_message(f"💰 Balance USDT libero: {bal:.2f}$\n"
                    f"Daily PnL: {risk_manager.daily_pnl:+.2f}$\n"
                    f"Weekly PnL: {risk_manager.weekly_pnl:+.2f}$")


def _cmd_positions():
    if not positions and not mr_manager.positions:
        tg.send_message("Nessuna posizione aperta.")
        return
    lines = []
    for sym, p in list(positions.items()):
        half = " [50% venduto]" if p.get("half_sold") else ""
        lines.append(f"  [{p['engine']}] {sym} @ {p['entry_price']:.4f}{half}")
    for sym, p in list(mr_manager.positions.items()):
        lines.append(f"  [MR] {sym} @ {p['entry_price']:.4f}")
    tg.send_message("📊 Posizioni aperte:\n" + "\n".join(lines))


def _cmd_pnl():
    tg.send_message(f"📈 PnL\n  Oggi: {risk_manager.daily_pnl:+.2f}$\n"
                    f"  Settimana: {risk_manager.weekly_pnl:+.2f}$\n"
                    f"  MR totale: {mr_manager.total_pnl:+.2f}$")


def _cmd_status():
    cds = [s for s, t in multitf_cooldown.items() if datetime.now() < t]
    guard = "🛡️ RISK-OFF" if _last_risk_off else "🟢 normale"
    tg.send_message(f"🤖 CryptoBot Omar v4.4 attivo\n"
                    f"  Simboli: {len(SYMBOLS)}\n"
                    f"  Pos aperte: {len(positions) + len(mr_manager.positions)}\n"
                    f"  Daily PnL: {risk_manager.daily_pnl:+.2f}$\n"
                    f"  Volatility Guard: {guard}\n"
                    f"  Cooldown: {cds if cds else 'nessuno'}")


def _cmd_stop():
    tg.send_message("⛔ Stop richiesto. Il bot si fermerà al prossimo ciclo.")
    global _running
    _running = False


tg.start_polling({
    "/balance": _cmd_balance,
    "/positions": _cmd_positions,
    "/pnl": _cmd_pnl,
    "/status": _cmd_status,
    "/stop": _cmd_stop,
})

# ------------------------------------------------------------------ #
# Main loop                                                            #
# ------------------------------------------------------------------ #

_running = True
_last_heartbeat_hour = -1
_last_risk_off = False   # stato precedente del Volatility Guard (per alert una-tantum)

log("=" * 60)
log(f"CryptoBot Omar v4.4 AVVIATO — {len(SYMBOLS)} simboli")
log(f"Engines: MultiTF+4H | TRIX+ADX+4H | MeanRev+BB+FastRSI")
log(f"Sizing su ATR 1h | R:R 1:3.3 | PartialTP+fee gate | "
    f"TimeFilter {TRADE_HOUR_START}-{TRADE_HOUR_END}UTC | PnL netto fee | "
    f"VolGuard {VOL_SPIKE_MULT}×")
log("=" * 60)
tg.send_message(f"🚀 <b>CryptoBot Omar v4.4 AVVIATO</b>\n"
                f"Simboli: {', '.join(SYMBOLS)}\n"
                f"Sizing ATR 1h | R:R 1:3.3 | PnL netto fee | 🛡️ Volatility Guard")


def _fetch_regime_df(symbol: str):
    """Fetch 1h candles for regime detection."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=100)
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df
    except Exception:
        return None


def _fetch_4h_ema_above(symbol: str) -> bool:
    """Returns True se close > EMA50 su 4H — struttura rialzista richiesta per nuovi long."""
    try:
        import pandas as pd
        import ta
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="4h", limit=60)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        close = df["close"]
        ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]
        return close.iloc[-1] > ema50
    except Exception:
        return True  # fallback: non bloccare il segnale


while _running:
    try:
        now = datetime.now()
        now_utc = datetime.utcnow()

        # Heartbeat
        if now.hour in HEARTBEAT_HOURS and now.hour != _last_heartbeat_hour:
            _last_heartbeat_hour = now.hour
            bal = get_balance()
            tg.send_message(f"💓 Heartbeat {now.strftime('%H:%M')}\n"
                            f"  Balance: {bal:.2f}$\n"
                            f"  Daily PnL: {risk_manager.daily_pnl:+.2f}$\n"
                            f"  Posizioni: {len(positions) + len(mr_manager.positions)}")

        # DCA lunedì
        if risk_manager.should_dca():
            bal = get_balance()
            if bal >= DCA_AMOUNT_USDT:
                log("[DCA] Lunedì DCA: acquisto BTC/USD")
                tg.send_message(f"💸 DCA lunedì: {DCA_AMOUNT_USDT}$ in BTC")
                risk_manager.mark_dca_done()

        # Verifica limiti giornalieri
        can_trade, reason_trade = risk_manager.can_trade()
        if not can_trade:
            log(f"[RISK] {reason_trade}")
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        bal = get_balance()
        open_value = _open_value()
        equity = bal + open_value   # esposizione misurata su equity totale, non solo free

        # Filtro orario: no nuovi ingressi 23:00-07:00 UTC
        in_trading_hours = TRADE_HOUR_START <= now_utc.hour < TRADE_HOUR_END

        # Fetch BTC regime per filtro anti-correlazione
        btc_df = _fetch_regime_df("BTC/USD")
        btc_regime = get_regime(btc_df) if btc_df is not None else "UNKNOWN"

        # Volatility Guard globale: spike di volatilità su BTC = stress di mercato
        # → risk-off su TUTTI gli asset (nessun nuovo long). Difesa anti-crollo.
        btc_vol = _vol_ratio(btc_df) if btc_df is not None else 1.0
        global_risk_off = VOL_GUARD_ENABLED and btc_vol > VOL_SPIKE_MULT
        if global_risk_off and not _last_risk_off:
            msg = (f"🛡️ <b>RISK-OFF attivato</b>\n"
                   f"  Volatilità BTC {btc_vol:.1f}× la norma — stop nuovi ingressi.\n"
                   f"  Le posizioni aperte restano protette dai loro stop.")
            log(f"[VOL GUARD] RISK-OFF ON — BTC vol {btc_vol:.2f}×")
            tg.send_message(msg)
        elif not global_risk_off and _last_risk_off:
            log(f"[VOL GUARD] RISK-OFF OFF — BTC vol {btc_vol:.2f}× rientrata")
            tg.send_message(f"✅ Risk-off rientrato — volatilità BTC normalizzata ({btc_vol:.1f}×).")
        _last_risk_off = global_risk_off

        for symbol in SYMBOLS:
            try:
                df_regime = _fetch_regime_df(symbol)
                if df_regime is None:
                    continue
                regime = get_regime(df_regime)

                # ATR 1h come riferimento UNICO per SL/TP/trailing/partial.
                # Movimenti 1h (~0.8-1.5%) coprono la fee 0.52% con margine reale.
                # Riusa df_regime (1h) → nessuna chiamata API aggiuntiva.
                atr_h = _atr_1h(df_regime)

                # Cooldown check: no nuovi long dopo SL perdente per 60 min
                in_cooldown = (symbol in multitf_cooldown and
                               datetime.now() < multitf_cooldown[symbol])

                # Volatility Guard per-asset: spike locale O risk-off globale.
                sym_vol = _vol_ratio(df_regime)
                vol_spike = VOL_GUARD_ENABLED and (global_risk_off or sym_vol > VOL_SPIKE_MULT)

                flags = []
                if in_cooldown:
                    flags.append(f"COOLDOWN→{multitf_cooldown[symbol].strftime('%H:%M')}")
                if not in_trading_hours:
                    flags.append("NO-HOURS")
                if vol_spike:
                    flags.append(f"VOL-GUARD({sym_vol:.1f}×)")
                log(f"[{symbol}] Regime:{regime} BTC:{btc_regime}"
                    + (f" [{' '.join(flags)}]" if flags else ""))

                has_pos_multi = symbol in positions
                has_pos_mr = mr_manager.has_position(symbol)

                # -------------------------------------------------- #
                # Check SL/TP per posizioni MultiTF e TRIX            #
                # (gira sempre, anche fuori orario di trading)        #
                # -------------------------------------------------- #
                if has_pos_multi:
                    pos = positions[symbol]
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker["last"]
                    except Exception:
                        continue

                    trail_mult = pos.get("trailing_mult", TRAILING_ATR_MULT)
                    atr_val = pos.get("atr", 0)

                    # Partial TP: vendi 50% a TP1, sposta SL a breakeven
                    if not pos.get("half_sold", False) and _atr_valid(atr_val):
                        tp1 = pos.get("tp1", float("inf"))
                        if current_price >= tp1:
                            half_qty = pos["qty"] / 2
                            try:
                                exchange.create_market_sell_order(symbol, _amt(symbol, half_qty))
                                partial_pnl = _net_pnl(pos["entry_price"], current_price, half_qty)
                                risk_manager.record_pnl(partial_pnl)
                                pos["qty"] = half_qty
                                pos["half_sold"] = True
                                # Breakeven NETTO: copre anche le fee del round-trip
                                breakeven = pos["entry_price"] * (1 + 2 * FEE_RATE)
                                pos["trailing_sl"] = breakeven
                                _save_positions()
                                msg = (f"⚡ PARTIAL TP {pos['engine']} {symbol}\n"
                                       f"  50% @ {current_price:.4f}  Parziale: {partial_pnl:+.3f}$\n"
                                       f"  SL → breakeven netto: {breakeven:.4f}")
                                log(msg)
                                tg.send_message(msg)
                            except Exception as e:
                                log(f"[PARTIAL TP ERR {symbol}] {e}")

                    # Trailing stop con moltiplicatore adattivo per regime
                    new_sl = current_price - trail_mult * atr_val
                    if new_sl > pos["trailing_sl"]:
                        pos["trailing_sl"] = new_sl

                    if current_price <= pos["trailing_sl"]:
                        place_sell(symbol, "TRAILING_SL")
                        continue
                    if current_price >= pos["tp"]:
                        place_sell(symbol, "TP")
                        continue

                # -------------------------------------------------- #
                # Check SL/TP per posizioni MR                        #
                # -------------------------------------------------- #
                if has_pos_mr:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker["last"]
                    except Exception:
                        continue
                    sl_tp = mr_manager.check_sl_tp(symbol, current_price)
                    if sl_tp in ("SL", "TP", "TIMEOUT"):
                        mr_pos = mr_manager.get_position(symbol)
                        mr_qty = _amt(symbol, mr_pos.get("qty", 0))
                        if mr_qty > 0:
                            try:
                                exchange.create_market_sell_order(symbol, mr_qty)
                            except Exception as e:
                                log(f"[MR SELL ERR {symbol}] {e}")
                                tg.send_message(f"❌ MR SELL error {symbol}: {e}")
                        pnl = mr_manager.register_sell(symbol, current_price)
                        risk_manager.record_pnl(pnl)
                        emoji = "✅" if pnl >= 0 else "🔴"
                        tg.send_message(f"{emoji} MR {sl_tp} {symbol}\n"
                                        f"  PnL: {pnl:+.3f}$")
                        log(f"[MR {sl_tp}] {symbol} PnL={pnl:+.3f}$")
                        has_pos_mr = False

                # Nessun nuovo ingresso fuori dalle ore di trading (SL/TP gestiti sopra)
                if not in_trading_hours:
                    continue

                # 4H EMA filter: richiesta struttura rialzista per nuovi long
                above_4h_ema = _fetch_4h_ema_above(symbol)

                # Sizing adattivo per regime di mercato
                trade_amt = TRADE_AMOUNT_TRENDING_UP if regime == "TRENDING_UP" else TRADE_AMOUNT_RANGING

                # -------------------------------------------------- #
                # Engine 3: Mean Reversion (RANGING + TRENDING_DOWN)  #
                # -------------------------------------------------- #
                sig_mr, rsi_mr, price_mr, atr_mr = get_signal_mr(
                    exchange, symbol, has_pos_mr, regime
                )

                if sig_mr == "SELL_MR" and has_pos_mr:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        cp = ticker["last"]
                    except Exception:
                        cp = price_mr
                    mr_pos = mr_manager.get_position(symbol)
                    mr_qty = _amt(symbol, mr_pos.get("qty", 0))
                    if mr_qty > 0:
                        try:
                            exchange.create_market_sell_order(symbol, mr_qty)
                        except Exception as e:
                            log(f"[MR SELL ERR {symbol}] {e}")
                            tg.send_message(f"❌ MR SELL error {symbol}: {e}")
                    pnl = mr_manager.register_sell(symbol, cp)
                    risk_manager.record_pnl(pnl)
                    emoji = "✅" if pnl >= 0 else "🔴"
                    tg.send_message(f"{emoji} MR EXIT {symbol}\n"
                                    f"  RSI: {rsi_mr:.1f}  PnL: {pnl:+.3f}$")
                    log(f"[MR SELL] {symbol} RSI={rsi_mr:.1f} PnL={pnl:+.3f}$")

                elif sig_mr == "BUY_MR" and not has_pos_mr and not has_pos_multi:
                    if vol_spike:
                        log(f"[MR SKIP {symbol}] Volatility Guard (vol {sym_vol:.1f}×)")
                    elif not _atr_valid(atr_h):
                        log(f"[MR SKIP {symbol}] ATR 1h non valido")
                    elif not _edge_ok(atr_h, price_mr):
                        log(f"[MR SKIP {symbol}] edge troppo piccolo: TP non copre fee 0.52%")
                    elif btc_regime == "TRENDING_DOWN" and symbol != "BTC/USD" and len(mr_manager.positions) >= 2:
                        log(f"[MR SKIP {symbol}] BTC TRENDING_DOWN — anti-correlazione")
                    else:
                        ok_mr, reason_mr = mr_manager.can_buy(bal, symbol)
                        if ok_mr and risk_manager.check_exposure(equity, open_value):
                            mr_qty = _amt(symbol, MR_AMOUNT_USD / price_mr)
                            try:
                                exchange.create_market_buy_order(symbol, mr_qty)
                                mr_manager.register_buy(symbol, price_mr, atr_h)
                                tg.send_message(f"🟢 MR BUY {symbol}\n"
                                                f"  RSI: {rsi_mr:.1f}  BB touch ✓  FastRSI ✓\n"
                                                f"  Qty: {mr_qty:.4f}  ~{MR_AMOUNT_USD}$\n"
                                                f"  SL: {price_mr - 1.0*atr_h:.4f}  TP: {price_mr + 2.5*atr_h:.4f}")
                                log(f"[MR BUY] {symbol} RSI={rsi_mr:.1f} price={price_mr:.4f} qty={mr_qty:.4f}")
                            except Exception as e:
                                log(f"[MR BUY ERR {symbol}] {e}")
                                tg.send_message(f"❌ MR BUY error {symbol}: {e}")
                        else:
                            log(f"[MR SKIP {symbol}] {reason_mr}")

                # -------------------------------------------------- #
                # Engine 2: TRIX + ADX (15m) + 4H EMA               #
                # -------------------------------------------------- #
                if not has_pos_multi:
                    sig_trix, trix_val, price_trix, atr_trix = get_signal_trix(
                        exchange, symbol, has_pos_multi, regime, above_4h_ema
                    )
                    if (sig_trix == "BUY_TRIX" and not has_pos_multi and not has_pos_mr
                            and not in_cooldown and not vol_spike and _atr_valid(atr_h)
                            and _edge_ok(atr_h, price_trix)):
                        if risk_manager.check_exposure(equity, open_value) and len(positions) < MAX_OPEN_POSITIONS:
                            sl = price_trix - ATR_SL_MULT * atr_h
                            tp = price_trix + ATR_TP_MULT * atr_h
                            place_buy(symbol, trade_amt, price_trix, sl, tp, "TRIX", atr_h, regime)

                # -------------------------------------------------- #
                # Engine 1: MultiTF 5m + 15m + 4H EMA               #
                # -------------------------------------------------- #
                sig_mtf, rsi_mtf, price_mtf, atr_mtf = get_signal_multitf(
                    exchange, symbol, has_pos_multi, regime, above_4h_ema
                )
                rsi_str = f"{rsi_mtf:.1f}" if rsi_mtf is not None else "N/A"
                log(f"[{symbol}] MultiTF={sig_mtf} RSI={rsi_str}")

                if (sig_mtf in ("BUY_5M", "BUY_15M") and not has_pos_multi and not has_pos_mr
                        and not in_cooldown and not vol_spike and _atr_valid(atr_h)
                        and _edge_ok(atr_h, price_mtf)):
                    if risk_manager.check_exposure(equity, open_value) and len(positions) < MAX_OPEN_POSITIONS:
                        sl = price_mtf - ATR_SL_MULT * atr_h
                        tp = price_mtf + ATR_TP_MULT * atr_h
                        place_buy(symbol, trade_amt, price_mtf, sl, tp, sig_mtf, atr_h, regime)

                elif sig_mtf in ("SELL_5M", "SELL_15M") and has_pos_multi:
                    place_sell(symbol, sig_mtf)

            except Exception as e:
                log(f"[LOOP ERR {symbol}] {e}")
                continue

    except KeyboardInterrupt:
        break
    except Exception as e:
        log(f"[MAIN ERR] {e}")

    time.sleep(LOOP_SLEEP_SECONDS)

log("Bot fermato.")
tg.send_message("⛔ CryptoBot Omar v4.1 fermato.")
