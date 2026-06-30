"""
Crypto Price Alert Bot — Telegram
=================================
Un bot Telegram che avvisa quando una criptovaluta supera (o scende sotto)
un prezzo target. Usa l'API pubblica e gratuita di CoinGecko (nessuna chiave
richiesta).

Pensato come:
  - pezzo di portfolio (mostra che sai costruire bot reali e stabili)
  - base per una versione a pagamento (alert illimitati in abbonamento)

Avvio:
  export TELEGRAM_TOKEN="il_token_di_BotFather"
  python price_alert_bot.py

Comandi Telegram:
  /start, /help          → istruzioni
  /add btc > 70000       → avvisami quando BTC supera 70000$
  /add eth < 3000        → avvisami quando ETH scende sotto 3000$
  /list                  → elenca i tuoi alert
  /del 2                 → cancella l'alert numero 2
"""

import os
import json
import time
import threading
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ALERTS_FILE = os.path.expanduser("~/price_alerts.json")
CHECK_EVERY_SECONDS = 60
API = "https://api.coingecko.com/api/v3/simple/price"

# Ticker comuni → id CoinGecko. Per altri, si prova il ticker stesso come id.
COIN_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "xrp": "ripple",
    "link": "chainlink", "ada": "cardano", "doge": "dogecoin", "avax": "avalanche-2",
    "bnb": "binancecoin", "matic": "matic-network", "dot": "polkadot",
    "ltc": "litecoin", "trx": "tron", "atom": "cosmos", "near": "near",
}

_alerts = []          # [{chat_id, coin_id, ticker, direction, target}]
_last_update_id = 0
_lock = threading.Lock()


# ------------------------------------------------------------------ #
# Persistenza                                                          #
# ------------------------------------------------------------------ #

def _load():
    global _alerts
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE) as f:
                _alerts = json.load(f)
        except Exception:
            _alerts = []


def _save():
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump(_alerts, f, indent=2)
    except Exception:
        pass


# ------------------------------------------------------------------ #
# Telegram                                                             #
# ------------------------------------------------------------------ #

def send(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def get_updates():
    global _last_update_id
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": _last_update_id + 1, "timeout": 30},
            timeout=35,
        )
        return r.json().get("result", [])
    except Exception:
        return []


# ------------------------------------------------------------------ #
# Prezzi                                                               #
# ------------------------------------------------------------------ #

def fetch_prices(coin_ids):
    """Ritorna {coin_id: prezzo_usd} per la lista di id richiesti."""
    if not coin_ids:
        return {}
    try:
        r = requests.get(API, params={
            "ids": ",".join(sorted(set(coin_ids))),
            "vs_currencies": "usd",
        }, timeout=15)
        data = r.json()
        return {cid: v["usd"] for cid, v in data.items() if "usd" in v}
    except Exception:
        return {}


# ------------------------------------------------------------------ #
# Comandi                                                              #
# ------------------------------------------------------------------ #

HELP = (
    "🤖 <b>Crypto Price Alert Bot</b>\n\n"
    "Ti avviso quando una crypto raggiunge il prezzo che vuoi.\n\n"
    "<b>Comandi:</b>\n"
    "/add btc &gt; 70000 — avviso se BTC supera 70000$\n"
    "/add eth &lt; 3000 — avviso se ETH scende sotto 3000$\n"
    "/list — i tuoi alert\n"
    "/del 2 — cancella l'alert n.2\n"
    "/help — questo messaggio"
)


def handle(chat_id, text):
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd in ("/start", "/help"):
        send(chat_id, HELP)

    elif cmd == "/add":
        # formato: /add <ticker> <>|< > <prezzo>
        try:
            ticker = parts[1].lower()
            direction = parts[2]
            target = float(parts[3])
            if direction not in (">", "<"):
                raise ValueError
        except (IndexError, ValueError):
            send(chat_id, "Formato: <code>/add btc &gt; 70000</code> oppure <code>/add eth &lt; 3000</code>")
            return
        coin_id = COIN_IDS.get(ticker, ticker)
        # Verifica che la moneta esista davvero (e diamo il prezzo attuale)
        price = fetch_prices([coin_id]).get(coin_id)
        if price is None:
            send(chat_id, f"Non trovo la moneta <b>{ticker}</b>. Usa il ticker (btc, eth, sol...).")
            return
        with _lock:
            _alerts.append({
                "chat_id": chat_id, "coin_id": coin_id, "ticker": ticker.upper(),
                "direction": direction, "target": target,
            })
            _save()
        arrow = "sopra" if direction == ">" else "sotto"
        send(chat_id, f"✅ Alert creato: <b>{ticker.upper()}</b> {arrow} <b>{target:,.2f}$</b>\n"
                      f"   (prezzo ora: {price:,.2f}$)")

    elif cmd == "/list":
        mine = [(i, a) for i, a in enumerate(_alerts, 1) if a["chat_id"] == chat_id]
        if not mine:
            send(chat_id, "Nessun alert attivo. Creane uno con /add.")
            return
        lines = ["📋 <b>I tuoi alert:</b>"]
        for i, a in mine:
            arrow = "sopra" if a["direction"] == ">" else "sotto"
            lines.append(f"  {i}. {a['ticker']} {arrow} {a['target']:,.2f}$")
        send(chat_id, "\n".join(lines))

    elif cmd == "/del":
        try:
            idx = int(parts[1])
        except (IndexError, ValueError):
            send(chat_id, "Formato: <code>/del 2</code> (numero da /list)")
            return
        with _lock:
            if 1 <= idx <= len(_alerts) and _alerts[idx - 1]["chat_id"] == chat_id:
                removed = _alerts.pop(idx - 1)
                _save()
                send(chat_id, f"🗑 Alert rimosso: {removed['ticker']} {removed['direction']} {removed['target']:,.2f}$")
            else:
                send(chat_id, "Numero non valido. Controlla con /list.")

    else:
        send(chat_id, "Comando non riconosciuto. Usa /help")


# ------------------------------------------------------------------ #
# Loop di controllo prezzi                                            #
# ------------------------------------------------------------------ #

def price_watch_loop():
    while True:
        try:
            with _lock:
                coin_ids = [a["coin_id"] for a in _alerts]
            prices = fetch_prices(coin_ids)
            triggered = []
            with _lock:
                for a in _alerts:
                    p = prices.get(a["coin_id"])
                    if p is None:
                        continue
                    hit = (a["direction"] == ">" and p >= a["target"]) or \
                          (a["direction"] == "<" and p <= a["target"])
                    if hit:
                        triggered.append((a, p))
                # rimuovi gli alert scattati (one-shot)
                for a, _ in triggered:
                    if a in _alerts:
                        _alerts.remove(a)
                if triggered:
                    _save()
            for a, p in triggered:
                arrow = "📈 superato" if a["direction"] == ">" else "📉 sceso sotto"
                send(a["chat_id"],
                     f"🔔 <b>ALERT {a['ticker']}</b>\n"
                     f"   {arrow} {a['target']:,.2f}$\n"
                     f"   Prezzo attuale: <b>{p:,.2f}$</b>")
        except Exception:
            pass
        time.sleep(CHECK_EVERY_SECONDS)


# ------------------------------------------------------------------ #
# Main                                                                 #
# ------------------------------------------------------------------ #

def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit("Manca TELEGRAM_TOKEN. Esegui: export TELEGRAM_TOKEN=\"...\"")
    _load()
    threading.Thread(target=price_watch_loop, daemon=True).start()
    print("Bot avviato. In ascolto dei comandi Telegram...")
    global _last_update_id
    while True:
        for upd in get_updates():
            _last_update_id = upd["update_id"]
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            if text and chat_id is not None:
                handle(chat_id, text)


if __name__ == "__main__":
    main()
