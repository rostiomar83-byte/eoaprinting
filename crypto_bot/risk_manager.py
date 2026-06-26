"""
Gestione del rischio giornaliero e settimanale.
Controlla perdita massima, esposizione massima e DCA lunedì.
"""

import json
import os
from datetime import datetime, timedelta

from config import (
    MAX_DAILY_LOSS_USDT,
    MAX_WEEKLY_LOSS_USDT,
    MAX_EXPOSURE_PCT,
    DCA_AMOUNT_USDT,
)

RISK_STATE_FILE = os.path.expanduser("~/crypto_bot/risk_state.json")


class RiskManager:
    def __init__(self):
        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.last_reset_day: str = ""
        self.last_reset_week: str = ""
        self.dca_done_this_week: bool = False
        self._load()
        self._auto_reset()

    def _load(self):
        if not os.path.exists(RISK_STATE_FILE):
            return
        try:
            with open(RISK_STATE_FILE) as f:
                d = json.load(f)
            self.daily_pnl = d.get("daily_pnl", 0.0)
            self.weekly_pnl = d.get("weekly_pnl", 0.0)
            self.last_reset_day = d.get("last_reset_day", "")
            self.last_reset_week = d.get("last_reset_week", "")
            self.dca_done_this_week = d.get("dca_done_this_week", False)
        except Exception:
            pass

    def _save(self):
        os.makedirs(os.path.dirname(RISK_STATE_FILE), exist_ok=True)
        with open(RISK_STATE_FILE, "w") as f:
            json.dump({
                "daily_pnl": self.daily_pnl,
                "weekly_pnl": self.weekly_pnl,
                "last_reset_day": self.last_reset_day,
                "last_reset_week": self.last_reset_week,
                "dca_done_this_week": self.dca_done_this_week,
            }, f, indent=2)

    def _auto_reset(self):
        today = datetime.now().strftime("%Y-%m-%d")
        week = datetime.now().strftime("%Y-W%W")

        if today != self.last_reset_day:
            self.daily_pnl = 0.0
            self.last_reset_day = today

        if week != self.last_reset_week:
            self.weekly_pnl = 0.0
            self.last_reset_week = week
            self.dca_done_this_week = False

        self._save()

    def record_pnl(self, pnl: float):
        self._auto_reset()
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self._save()

    def can_trade(self) -> tuple:
        self._auto_reset()
        if self.daily_pnl <= -MAX_DAILY_LOSS_USDT:
            return False, f"Daily loss limit raggiunto: {self.daily_pnl:.2f} USD"
        if self.weekly_pnl <= -MAX_WEEKLY_LOSS_USDT:
            return False, f"Weekly loss limit raggiunto: {self.weekly_pnl:.2f} USD"
        return True, "OK"

    def check_exposure(self, balance: float, open_positions_value: float) -> bool:
        """True se possiamo aprire nuove posizioni senza superare MAX_EXPOSURE_PCT."""
        max_exposed = balance * MAX_EXPOSURE_PCT
        return open_positions_value < max_exposed

    def should_dca(self) -> bool:
        """DCA automatico il lunedì mattina (8-10h) se non già eseguito questa settimana."""
        self._auto_reset()
        if self.dca_done_this_week:
            return False
        now = datetime.now()
        is_monday = now.weekday() == 0
        is_morning = 8 <= now.hour < 10
        return is_monday and is_morning

    def mark_dca_done(self):
        self.dca_done_this_week = True
        self._save()
