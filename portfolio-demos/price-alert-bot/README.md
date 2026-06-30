<h1 align="center">🔔 Crypto Price Alert Bot</h1>

<p align="center">
  <b>A reliable Telegram bot that pings you the moment a crypto hits your target price.</b><br>
  Built in Python · Free CoinGecko API · No API key · Runs 24/7
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white">
  <img src="https://img.shields.io/badge/API-CoinGecko-8DC63F">
  <img src="https://img.shields.io/badge/License-MIT-green">
</p>

---

## 🎬 Demo

> Set an alert in one message, get notified the instant price crosses it.

```
You:  /add btc < 70000
Bot:  ✅ Alert created: BTC below 70,000.00$  (price now: 59,407.00$)
Bot:  🔔 ALERT BTC — dropped below 70,000.00$  ·  Current price: 59,419.00$
```

<!-- Aggiungi qui i tuoi screenshot reali:  ![demo](docs/demo1.png) -->

---

## ✨ Features

- 📈 **Above / below** price alerts on any coin
- 💬 **100% Telegram-driven** — no dashboard, no setup headaches
- 💾 **Persistent** — alerts survive restarts (saved to disk)
- 🆓 **Free data** — public CoinGecko API, zero API keys
- 🧵 **Multi-threaded** — price watcher + command listener run together
- 🛡️ **Production-minded** — error handling so it doesn't crash on a bad request

## 🚀 Quick Start

```bash
pip install requests
export TELEGRAM_TOKEN="your_botfather_token"
python price_alert_bot.py
```

Create your bot token in 30 seconds with [@BotFather](https://t.me/BotFather) → `/newbot`.

## 💬 Commands

| Command | What it does |
|---------|--------------|
| `/add btc > 70000` | Alert when **BTC goes above** $70,000 |
| `/add eth < 3000` | Alert when **ETH drops below** $3,000 |
| `/list` | Show your active alerts |
| `/del 2` | Delete alert #2 |
| `/help` | Show help |

Works with BTC, ETH, SOL, XRP, LINK, ADA, DOGE, AVAX, BNB, MATIC, DOT, LTC,
TRX, ATOM, NEAR — and any other CoinGecko coin id.

## 🧠 How it works

A background thread polls CoinGecko every 60s and checks each alert; a second
thread listens for Telegram commands. Alerts are one-shot and stored in a JSON
file so nothing is lost on restart. Clean, ~250 lines, easy to extend.

## 🖥️ Run it 24/7

```bash
nohup python price_alert_bot.py > bot.log 2>&1 &
```
(or a `systemd` service / watchdog for true production uptime)

---

## 🛠️ Need a custom bot?

I build **custom Telegram bots & Python automations** — price alerts, trading
signals, notifications, web scraping, API integrations, 24/7 hosting.

📩 **Hire me on Fiverr:** _[metti qui il link al tuo gig]_

---

<p align="center"><sub>MIT License · Free to use and modify</sub></p>
