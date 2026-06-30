# 🔔 Crypto Price Alert Bot (Telegram)

A simple, reliable **Telegram bot** that notifies you when a cryptocurrency
crosses a price you choose. Built in Python, uses the free **CoinGecko** API
(no API key needed).

> Built by someone who runs trading & automation bots in production — so it's
> made to be **stable**, not just a demo.

## ✨ Features

- 📈 Alerts when a coin goes **above** or **below** a target price
- 💬 Fully controlled from Telegram chat (no UI needed)
- 💾 Alerts saved to disk (survive restarts)
- 🆓 No paid API — uses public CoinGecko endpoint
- 🧵 Background price checker + command listener (multi-threaded)

## 🚀 Setup (2 minutes)

1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram → get the token
2. Install dependency:
   ```bash
   pip install requests
   ```
3. Run:
   ```bash
   export TELEGRAM_TOKEN="your_token_here"
   python price_alert_bot.py
   ```

## 💬 Commands

| Command | What it does |
|---------|--------------|
| `/add btc > 70000` | Alert when BTC goes **above** $70,000 |
| `/add eth < 3000` | Alert when ETH drops **below** $3,000 |
| `/list` | List your active alerts |
| `/del 2` | Delete alert number 2 |
| `/help` | Show help |

Supported tickers out of the box: BTC, ETH, SOL, XRP, LINK, ADA, DOGE, AVAX,
BNB, MATIC, DOT, LTC, TRX, ATOM, NEAR — and any other CoinGecko id.

## 🖥️ 24/7 hosting (optional)

Run it on a cheap VPS with auto-restart so it never goes down:
```bash
nohup python price_alert_bot.py > bot.log 2>&1 &
```
(or use systemd / a watchdog script for production)

## 🛠️ Customization / hire me

Need a custom version — stock alerts, multiple exchanges, a subscription tier,
or a totally different bot? I build custom Telegram bots and automations.

---
MIT License — free to use and modify.
