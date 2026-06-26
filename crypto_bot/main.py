"""
CryptoBot Omar v4
Engines attivi:
  1. MultiTF 5m/15m — trend following (TRENDING_UP)
  2. TRIX+ADX 15m   — trend following con filtro noise (TRENDING_UP/RANGING)
  3. Mean Reversion  — RSI + BB touch + Fast RSI (RANGING + TRENDING_DOWN)
Obiettivo: +$5 USD/giorno su capitale ~$210 USDT Kraken
"""

import os
import time
import logging
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

# --- Config & moduli ---
from config import (
    SYMBOLS, LOOP_SLEEP_SECONDS, HEARTBEAT_HOURS,
    ATR_SL_MULT, ATR_TP_MULT, TRAILING_ATR_MULT, TRADE_AMOUNT_USDT,
    LOG_FILE, DCA_AMOUNT_USDT, STATE_FILE,
)
from market_regime import get_regime
from strategy_multiTF import get_signal_multitf
from strategy_trix import get_signal_trix
from strategy_meanrev import get_signal_mr
from mean_rev_manager import MeanRevManager
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

import json

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

positions: dict = _load_positions()   # symbol → {entry_price, sl, tp, qty, engine, atr}
mr_manager = MeanRevManager()
risk_manager = RiskManager()


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


def place_buy(symbol: str, amount_usd: float, price: float, sl: float, tp: float, engine: str, atr: float = 0.0):
    qty = amount_usd / price
    try:
        exchange.create_market_buy_order(symbol, qty)
        positions[symbol] = {
            "entry_price": price,
            "sl": sl,
            "tp": tp,
            "qty": qty,
            "engine": engine,
            "entry_time": datetime.now().isoformat(),
            "trailing_sl": sl,
            "atr": atr,
        }
        msg = (f"✅ BUY {engine} {symbol}\n"
               f"  Prezzo: {price:.4f}\n"
               f"  SL: {sl:.4f}  TP: {tp:.4f}\n"
               f"  Qty: {qty:.4f}  ~{amount_usd:.0f}$")
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
        exchange.create_market_sell_order(symbol, pos["qty"])
        ticker = exchange.fetch_ticker(symbol)
        exit_price = ticker["last"]
        pnl = (exit_price - pos["entry_price"]) * pos["qty"]
        risk_manager.record_pnl(pnl)

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
    for sym, p in positions.items():
        lines.append(f"  [{p['engine']}] {sym} @ {p['entry_price']:.4f}")
    for sym, p in mr_manager.positions.items():
        lines.append(f"  [MR] {sym} @ {p['entry_price']:.4f}")
    tg.send_message("📊 Posizioni aperte:\n" + "\n".join(lines))


def _cmd_pnl():
    tg.send_message(f"📈 PnL\n  Oggi: {risk_manager.daily_pnl:+.2f}$\n"
                    f"  Settimana: {risk_manager.weekly_pnl:+.2f}$\n"
                    f"  MR totale: {mr_manager.total_pnl:+.2f}$")


def _cmd_status():
    tg.send_message(f"🤖 CryptoBot Omar v4 attivo\n"
                    f"  Simboli: {len(SYMBOLS)}\n"
                    f"  Pos aperte: {len(positions) + len(mr_manager.positions)}\n"
                    f"  Daily PnL: {risk_manager.daily_pnl:+.2f}$")


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

log("=" * 60)
log(f"CryptoBot Omar v4 AVVIATO — {len(SYMBOLS)} simboli")
log(f"Engines: MultiTF, TRIX+ADX, MeanReversion (BB+FastRSI)")
log("=" * 60)
tg.send_message(f"🚀 <b>CryptoBot Omar v4 AVVIATO</b>\n"
                f"Simboli: {', '.join(SYMBOLS)}\n"
                f"Engines: MultiTF | TRIX+ADX | MeanRev+BB+FastRSI")


def _fetch_regime_df(symbol: str):
    """Fetch 1h candles for regime detection."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=100)
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df
    except Exception:
        return None


while _running:
    try:
        now = datetime.now()

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
        open_value = len(positions) * TRADE_AMOUNT_USDT + len(mr_manager.positions) * 20

        # Fetch BTC regime per filtro anti-correlazione
        btc_df = _fetch_regime_df("BTC/USD")
        btc_regime = get_regime(btc_df) if btc_df is not None else "UNKNOWN"

        for symbol in SYMBOLS:
            try:
                df_regime = _fetch_regime_df(symbol)
                if df_regime is None:
                    continue
                regime = get_regime(df_regime)

                log(f"[{symbol}] Regime: {regime} | BTC: {btc_regime}")

                has_pos_multi = symbol in positions
                has_pos_mr = mr_manager.has_position(symbol)

                # -------------------------------------------------- #
                # Check SL/TP per posizioni MultiTF e TRIX            #
                # -------------------------------------------------- #
                if has_pos_multi:
                    pos = positions[symbol]
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker["last"]
                    except Exception:
                        continue

                    # Trailing stop
                    new_sl = current_price - TRAILING_ATR_MULT * pos.get("atr", 0)
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
                        pnl = mr_manager.register_sell(symbol, current_price)
                        risk_manager.record_pnl(pnl)
                        emoji = "✅" if pnl >= 0 else "🔴"
                        tg.send_message(f"{emoji} MR {sl_tp} {symbol}\n"
                                        f"  PnL: {pnl:+.3f}$")
                        log(f"[MR {sl_tp}] {symbol} PnL={pnl:+.3f}$")
                        has_pos_mr = False

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
                    pnl = mr_manager.register_sell(symbol, cp)
                    risk_manager.record_pnl(pnl)
                    emoji = "✅" if pnl >= 0 else "🔴"
                    tg.send_message(f"{emoji} MR EXIT {symbol}\n"
                                    f"  RSI: {rsi_mr:.1f}  PnL: {pnl:+.3f}$")
                    log(f"[MR SELL] {symbol} RSI={rsi_mr:.1f} PnL={pnl:+.3f}$")

                elif sig_mr == "BUY_MR" and not has_pos_mr:
                    # Filtro BTC dominance: in TRENDING_DOWN evita accumulo MR su altcoin
                    if btc_regime == "TRENDING_DOWN" and symbol != "BTC/USD" and len(mr_manager.positions) >= 2:
                        log(f"[MR SKIP {symbol}] BTC TRENDING_DOWN — anti-correlazione")
                    else:
                        ok_mr, reason_mr = mr_manager.can_buy(bal, symbol)
                        if ok_mr and risk_manager.check_exposure(bal, open_value):
                            mr_manager.register_buy(symbol, price_mr, atr_mr)
                            tg.send_message(f"🟢 MR BUY {symbol}\n"
                                            f"  RSI: {rsi_mr:.1f}  BB touch ✓  FastRSI ✓\n"
                                            f"  SL: {price_mr - 1.0*atr_mr:.4f}  TP: {price_mr + 2.5*atr_mr:.4f}")
                            log(f"[MR BUY] {symbol} RSI={rsi_mr:.1f} price={price_mr:.4f}")
                        else:
                            log(f"[MR SKIP {symbol}] {reason_mr}")

                # -------------------------------------------------- #
                # Engine 2: TRIX + ADX (15m)                         #
                # -------------------------------------------------- #
                if not has_pos_multi:
                    sig_trix, trix_val, price_trix, atr_trix = get_signal_trix(
                        exchange, symbol, has_pos_multi, regime
                    )
                    if sig_trix == "BUY_TRIX" and not has_pos_multi:
                        if risk_manager.check_exposure(bal, open_value) and len(positions) < 4:
                            sl = price_trix - ATR_SL_MULT * atr_trix
                            tp = price_trix + ATR_TP_MULT * atr_trix
                            place_buy(symbol, TRADE_AMOUNT_USDT, price_trix, sl, tp, "TRIX", atr_trix)

                # -------------------------------------------------- #
                # Engine 1: MultiTF 5m + 15m                         #
                # -------------------------------------------------- #
                sig_mtf, rsi_mtf, price_mtf, atr_mtf = get_signal_multitf(
                    exchange, symbol, has_pos_multi, regime
                )
                rsi_str = f"{rsi_mtf:.1f}" if rsi_mtf is not None else "N/A"
                log(f"[{symbol}] MultiTF={sig_mtf} RSI={rsi_str}")

                if sig_mtf in ("BUY_5M", "BUY_15M") and not has_pos_multi:
                    if risk_manager.check_exposure(bal, open_value) and len(positions) < 4:
                        sl = price_mtf - ATR_SL_MULT * atr_mtf
                        tp = price_mtf + ATR_TP_MULT * atr_mtf
                        place_buy(symbol, TRADE_AMOUNT_USDT, price_mtf, sl, tp, sig_mtf, atr_mtf)

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
tg.send_message("⛔ CryptoBot Omar v4 fermato.")
