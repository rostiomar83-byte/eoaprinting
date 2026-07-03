"""
Diario di trading strutturato + motore di statistiche.

Ogni trade chiuso viene registrato in TRADES_FILE (formato JSONL: un oggetto
JSON per riga). Questo è il "journaling" da trader professionista: dati puliti
e interrogabili, non testo di log da parsare.

compute_stats() legge tutto lo storico e calcola le metriche che contano:
win rate, profit factor, avg win/loss, e la performance spezzata per motore,
simbolo, ora del giorno e regime di mercato — così si scopre COSA funziona
davvero e si tara la strategia sui propri numeri reali.
"""

import json
import os
from datetime import datetime

from config import TRADES_FILE


def record_trade(symbol: str, engine: str, reason: str, entry: float,
                 exit_price: float, qty: float, pnl: float,
                 regime: str = "", rsi: float = None):
    """Appende un trade chiuso al diario. Non solleva mai: il logging non
    deve poter rompere il ciclo di trading."""
    try:
        rec = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "hour": datetime.now().hour,
            "weekday": datetime.now().weekday(),  # 0=lun .. 6=dom
            "symbol": symbol,
            "engine": engine,
            "reason": reason,
            "entry": round(float(entry), 6),
            "exit": round(float(exit_price), 6),
            "qty": round(float(qty), 8),
            "pnl": round(float(pnl), 4),
            "regime": regime,
            "rsi": round(float(rsi), 1) if rsi is not None else None,
        }
        os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
        with open(TRADES_FILE, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def load_trades() -> list:
    """Carica tutti i trade dal diario. Righe corrotte vengono saltate."""
    if not os.path.exists(TRADES_FILE):
        return []
    trades = []
    try:
        with open(TRADES_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    trades.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return trades


def _agg(trades: list) -> dict:
    """Aggrega una lista di trade in metriche sintetiche."""
    n = len(trades)
    if n == 0:
        return {"n": 0, "pnl": 0.0, "wr": 0.0, "wins": 0, "losses": 0,
                "avg_win": 0.0, "avg_loss": 0.0, "pf": 0.0}
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "n": n,
        "pnl": sum(t["pnl"] for t in trades),
        "wr": 100.0 * len(wins) / n,
        "wins": len(wins),
        "losses": len(losses),
        "avg_win": (gross_win / len(wins)) if wins else 0.0,
        "avg_loss": (gross_loss / len(losses)) if losses else 0.0,
        # Profit factor = soldi vinti / soldi persi. >1 = sistema in profitto.
        "pf": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
    }


def _breakdown(trades: list, key: str) -> dict:
    """Raggruppa i trade per un campo (engine/symbol/hour/regime) e aggrega."""
    groups: dict = {}
    for t in trades:
        groups.setdefault(t.get(key), []).append(t)
    return {k: _agg(v) for k, v in groups.items()}


def _fmt_pf(pf: float) -> str:
    return "∞" if pf == float("inf") else f"{pf:.2f}"


def daily_report(daily_pnl: float, bal: float, open_pos: int) -> str:
    """Report serale (ore 20) con riepilogo della giornata."""
    today = datetime.now().strftime("%Y-%m-%d")
    trades = [t for t in load_trades() if t.get("time", "").startswith(today)]

    emoji = "✅" if daily_pnl >= 0 else "🔴"
    lines = [
        f"{emoji} <b>Report giornaliero — {datetime.now().strftime('%d/%m/%Y')}</b>",
        "",
        f"PnL oggi: <b>{daily_pnl:+.2f}$</b>",
        f"Balance USDT: <b>{bal:.2f}$</b>",
        f"Posizioni aperte: {open_pos}",
    ]

    if trades:
        g = _agg(trades)
        lines.append("")
        lines.append(f"Trade oggi: {g['n']}  ({g['wins']}W / {g['losses']}L)")
        lines.append(f"Win rate: {g['wr']:.0f}%  |  PnL trade: {g['pnl']:+.2f}$")
        # dettaglio per motore (solo quelli attivi oggi)
        by_eng = _breakdown(trades, "engine")
        if by_eng:
            lines.append("")
            for eng, s in sorted(by_eng.items(), key=lambda kv: kv[1]["pnl"], reverse=True):
                lines.append(f"  {eng}: {s['pnl']:+.2f}$  ({s['n']} trade, WR {s['wr']:.0f}%)")
    else:
        lines.append("")
        lines.append("Nessun trade chiuso oggi.")

    return "\n".join(lines)


def compute_stats() -> str:
    """Report testuale completo, pronto per Telegram (HTML)."""
    trades = load_trades()
    if not trades:
        return ("📊 <b>Statistiche</b>\nNessun trade registrato ancora.\n"
                "Il diario parte da ora: i prossimi trade verranno tracciati.")

    g = _agg(trades)
    lines = ["📊 <b>STATISTICHE DI TRADING</b>", ""]
    lines.append(f"Trade totali: <b>{g['n']}</b>  "
                 f"({g['wins']}W / {g['losses']}L)")
    lines.append(f"Win rate: <b>{g['wr']:.1f}%</b>")
    lines.append(f"PnL netto totale: <b>{g['pnl']:+.2f}$</b>")
    lines.append(f"Profit factor: <b>{_fmt_pf(g['pf'])}</b>  "
                 f"(&gt;1 = sistema in profitto)")
    lines.append(f"Avg win: +{g['avg_win']:.3f}$  |  "
                 f"Avg loss: -{g['avg_loss']:.3f}$")
    if g["avg_loss"] > 0:
        lines.append(f"R medio realizzato: <b>1:{g['avg_win']/g['avg_loss']:.1f}</b>")

    # --- Per motore ---
    lines.append("\n<b>Per motore:</b>")
    for eng, s in sorted(_breakdown(trades, "engine").items(),
                         key=lambda kv: kv[1]["pnl"], reverse=True):
        lines.append(f"  {eng}: {s['pnl']:+.2f}$  "
                     f"({s['n']} trade, WR {s['wr']:.0f}%, PF {_fmt_pf(s['pf'])})")

    # --- Per simbolo ---
    lines.append("\n<b>Per simbolo:</b>")
    for sym, s in sorted(_breakdown(trades, "symbol").items(),
                         key=lambda kv: kv[1]["pnl"], reverse=True):
        lines.append(f"  {sym}: {s['pnl']:+.2f}$  "
                     f"({s['n']} trade, WR {s['wr']:.0f}%)")

    # --- Ore migliori e peggiori (solo se abbastanza dati) ---
    by_hour = _breakdown(trades, "hour")
    if len(trades) >= 10:
        ranked = sorted(by_hour.items(), key=lambda kv: kv[1]["pnl"], reverse=True)
        best = ranked[0]
        worst = ranked[-1]
        lines.append("\n<b>Orari (UTC server):</b>")
        lines.append(f"  Migliore: ore {best[0]:02d}:00 → {best[1]['pnl']:+.2f}$ "
                     f"({best[1]['n']} trade)")
        lines.append(f"  Peggiore: ore {worst[0]:02d}:00 → {worst[1]['pnl']:+.2f}$ "
                     f"({worst[1]['n']} trade)")

    # --- Per regime ---
    by_regime = _breakdown(trades, "regime")
    if any(by_regime):
        lines.append("\n<b>Per regime:</b>")
        for reg, s in sorted(by_regime.items(),
                             key=lambda kv: kv[1]["pnl"], reverse=True):
            label = reg if reg else "n/d"
            lines.append(f"  {label}: {s['pnl']:+.2f}$ ({s['n']} trade, WR {s['wr']:.0f}%)")

    return "\n".join(lines)
