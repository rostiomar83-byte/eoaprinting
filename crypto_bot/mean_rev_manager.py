"""
Gestisce le posizioni Mean Reversion con:
- Cooldown 90 min dopo stop loss
- Max 3 posizioni MR contemporanee
- Stop loss ATR-based, take profit ATR-based
- Salvataggio stato su disco (json)
"""

import json
import os
from datetime import datetime, timedelta

from config import MR_STATE_FILE, FEE_RATE

MR_AMOUNT_USD = 20
MR_ATR_SL = 1.0
MR_ATR_TP = 2.5
MAX_MR_POSITIONS = 3
MAX_MR_HOLD_HOURS = 12
MR_COOLDOWN_MINUTES = 90


class MeanRevManager:
    def __init__(self):
        self.positions: dict = {}
        self.total_pnl: float = 0.0
        self.cooldown_until: dict = {}  # symbol → datetime
        self._load()

    # ------------------------------------------------------------------ #
    # Persistenza                                                          #
    # ------------------------------------------------------------------ #

    def _load(self):
        if not os.path.exists(MR_STATE_FILE):
            return
        try:
            with open(MR_STATE_FILE) as f:
                data = json.load(f)
            self.positions = data.get("positions", {})
            self.total_pnl = data.get("total_pnl", 0.0)
            raw_cooldowns = data.get("cooldown_until", {})
            self.cooldown_until = {
                k: datetime.fromisoformat(v) for k, v in raw_cooldowns.items()
            }
        except Exception:
            pass

    def _save(self):
        data = {
            "positions": self.positions,
            "total_pnl": self.total_pnl,
            "cooldown_until": {
                k: v.isoformat() for k, v in self.cooldown_until.items()
            },
        }
        os.makedirs(os.path.dirname(MR_STATE_FILE), exist_ok=True)
        with open(MR_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------ #
    # Logica                                                               #
    # ------------------------------------------------------------------ #

    def can_buy(self, balance: float, symbol: str = None) -> tuple:
        if symbol and symbol in self.cooldown_until:
            if datetime.now() < self.cooldown_until[symbol]:
                remaining = int((self.cooldown_until[symbol] - datetime.now()).total_seconds() // 60)
                return False, f"Cooldown {symbol}: {remaining} min dopo stop loss"
            else:
                del self.cooldown_until[symbol]

        if len(self.positions) >= MAX_MR_POSITIONS:
            return False, f"Max posizioni MR ({MAX_MR_POSITIONS}) raggiunto"

        if balance < MR_AMOUNT_USD:
            return False, f"Balance insufficiente: {balance:.2f} USD < {MR_AMOUNT_USD}"

        return True, "OK"

    def register_buy(self, symbol: str, price: float, atr: float):
        sl = price - MR_ATR_SL * atr
        tp = price + MR_ATR_TP * atr
        self.positions[symbol] = {
            "entry_price": price,
            "sl": sl,
            "tp": tp,
            "atr": atr,
            "amount_usd": MR_AMOUNT_USD,
            "qty": MR_AMOUNT_USD / price,
            "entry_time": datetime.now().isoformat(),
        }
        self._save()

    def register_sell(self, symbol: str, price: float) -> float:
        pos = self.positions.get(symbol)
        if not pos:
            return 0.0

        qty = pos["qty"]
        gross = (price - pos["entry_price"]) * qty
        fees = (pos["entry_price"] + price) * qty * FEE_RATE
        pnl = gross - fees   # PnL netto commissioni Kraken

        self.total_pnl += pnl

        if pnl < 0:
            self.cooldown_until[symbol] = datetime.now() + timedelta(minutes=MR_COOLDOWN_MINUTES)

        self.positions.pop(symbol, None)
        self._save()
        return pnl

    def check_sl_tp(self, symbol: str, current_price: float):
        """Restituisce 'SL', 'TP' o None."""
        pos = self.positions.get(symbol)
        if not pos:
            return None

        # Timeout posizione
        entry_time = datetime.fromisoformat(pos["entry_time"])
        if (datetime.now() - entry_time).total_seconds() > MAX_MR_HOLD_HOURS * 3600:
            return "TIMEOUT"

        if current_price <= pos["sl"]:
            return "SL"
        if current_price >= pos["tp"]:
            return "TP"
        return None

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def get_position(self, symbol: str) -> dict:
        return self.positions.get(symbol, {})
