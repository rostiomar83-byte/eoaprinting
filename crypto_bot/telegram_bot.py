"""
Interfaccia Telegram per il bot.
Comandi: /start, /stop, /balance, /positions, /pnl, /status, /log
"""

import os
import threading
import requests


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_bot_running = True
_last_update_id = 0


def send_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram cap: 4096 chars. Splitting avoids silent truncation on /stats, /log, daily report.
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, max(1, len(text)), chunk_size)]
    try:
        for chunk in chunks:
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
            }, timeout=10)
    except Exception:
        pass


def _get_updates():
    global _last_update_id
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": _last_update_id + 1, "timeout": 30}, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []


def _handle_command(text: str, handlers: dict):
    text = text.strip().lower()
    for cmd, fn in handlers.items():
        if text.startswith(cmd):
            fn()
            return
    send_message("Comando non riconosciuto. Usa /help")


def poll_commands(handlers: dict):
    """
    Chiama questa funzione in un thread separato.
    handlers = {"/balance": fn_balance, "/positions": fn_positions, ...}
    """
    global _last_update_id, _bot_running
    while _bot_running:
        updates = _get_updates()
        for upd in updates:
            _last_update_id = upd["update_id"]
            msg = upd.get("message", {})
            txt = msg.get("text", "")
            if not txt:
                continue
            # Sicurezza: esegui SOLO comandi provenienti dalla chat autorizzata.
            # Senza questo controllo chiunque scriva al bot potrebbe vedere il
            # bilancio/posizioni o fermare il trading con /stop.
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID):
                continue
            _handle_command(txt, handlers)


def start_polling(handlers: dict):
    t = threading.Thread(target=poll_commands, args=(handlers,), daemon=True)
    t.start()


def stop_polling():
    global _bot_running
    _bot_running = False
