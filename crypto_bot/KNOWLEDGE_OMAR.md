# 📚 KNOWLEDGE — CryptoBot Omar

> Fonte unica di verità del progetto. Se un'analisi o un'altra chat parla di
> codice che non corrisponde a questo documento, **verifica sui file veri prima
> di agire**. La verità è una sola: il repo GitHub `claude/crypto-bot-progress-jxxhty`
> + il VM che gira da quel repo.

Ultimo aggiornamento: **v4.7** — 2026-06-30

---

## 🎯 Obiettivo

Generare profitto costante da ~$210 USDT di capitale su **Kraken spot**, con
rischio basso e gestione professionale. Target realistico: piccoli guadagni
composti (non $5-10/giorno fissi, che richiederebbero rendimenti insostenibili).
Filosofia: **quando perdo, perdo poco; quando vinco, lascio correre.**

---

## 🖥️ Infrastruttura

| Voce | Valore |
|------|--------|
| Exchange | Kraken (spot, market order taker) |
| VM | Google Cloud, user `rostiomar1983` |
| Cartella bot | `~/crypto_bot/` |
| Virtualenv | `/home/rostiomar1983/botenv/bin/python` |
| Avvio/riavvio | `watchdog.sh` (rilancia main.py se crasha, sleep 10s) |
| Repo GitHub | `rostiomar83-byte/eoaprinting` |
| Branch | `claude/crypto-bot-progress-jxxhty` |

**File di stato (NON versionati, protetti da .gitignore):**
- `positions.json` — posizioni MultiTF/TRIX aperte
- `mr_positions.json` — posizioni Mean Reversion aperte
- `risk_state.json` — daily/weekly PnL persistenti
- `trades.jsonl` — diario strutturato dei trade (per /stats)
- `bot.log` — log operativo

---

## ⚙️ Architettura — 3 motori

### 1. MultiTF (5m/15m) — breakout/trend
Trend following su 5m e 15m + filtro 4H EMA50. **Opera SOLO in TRENDING_UP** (da v4.5).

### 2. TRIX + ADX (15m) — breakout/trend
TRIX + ADX + 4H EMA + volume 1.2×. **Opera SOLO in TRENDING_UP** (da v4.5).

### 3. Mean Reversion — il motore vincente
RSI + tocco banda Bollinger inferiore + Fast RSI(7). **Opera SOLO in RANGING** (da v4.7).
**Bloccato anche se BTC è TRENDING_DOWN** (blocco globale aggiunto in v4.7).
Da v4.4 piazza **ordini reali** (prima era virtuale/paper).
Le uscite SELL_MR su posizioni già aperte funzionano in qualsiasi regime.

---

## 📐 Parametri chiave (config.py)

```
SYMBOLS = BTC, ETH, SOL, XRP, LINK   # 5 top-liquidity (AVAX/DOGE/ADA rimossi)
TRADE_AMOUNT_TRENDING_UP = 40        # sizing aggressivo in trend
TRADE_AMOUNT_RANGING     = 25        # sizing conservativo in laterale
MAX_OPEN_POSITIONS = 2               # max posizioni MultiTF/TRIX simultanee
MAX_EXPOSURE_PCT   = 0.70            # max 70% equity esposto
MAX_DAILY_LOSS_USDT  = 30
MAX_WEEKLY_LOSS_USDT = 60
ATR_SL_MULT = 1.5                    # stop loss = 1.5×ATR(1h)
ATR_TP_MULT = 5.0                    # take profit = 5×ATR → R:R 1:3.3
PARTIAL_TP_ATR_MULT = 2.0            # vendi 50% a 2×ATR, SL→breakeven
TRAILING_ATR_MULT = 1.5              # trailing in RANGING
TRAILING_ATR_TRENDING_UP = 2.0       # trailing più largo in trend
FEE_RATE = 0.0026                    # 0.26%/lato = 0.52% round-trip
MIN_TP1_NET_PCT = 0.0025             # il TP1 deve lasciare ≥0.25% netto dopo fee
TRADE_HOUR_START = 7 / END = 23      # no nuovi ingressi 23:00-07:00 UTC
VOL_SPIKE_MULT = 1.8                 # volatilità >1.8× la media → blocco ingressi
BREAKOUT_ONLY_TRENDING_UP = True     # breakout solo in TRENDING_UP (v4.5)
```

---

## 🛡️ Protezioni attive

1. **Fee gate** (`_edge_ok`): un trade si apre solo se il movimento atteso copre
   il round-trip fee 0.52% + margine. Blocca gli scalp che bruciano commissioni.
2. **ATR valido** (`_atr_valid`): mai posizioni senza stop loss (ATR NaN bloccato).
3. **Volatility Guard**: ATR% attuale vs media. Se BTC esplode → risk-off globale
   (nessun nuovo long su nessun asset). Difesa anti-crollo.
4. **4H EMA50 filter**: long solo se il prezzo è sopra EMA50 su 4h (no long in downtrend).
5. **Time filter**: niente ingressi 23:00-07:00 UTC (sessione asiatica, spread alti).
6. **Cooldown 60min** dopo uno stop loss perdente sullo stesso asset.
7. **Regime gate** (v4.5): breakout solo in TRENDING_UP; in RANGING solo Mean Reversion.
8. **MR gate** (v4.7): BUY_MR solo se regime locale == RANGING E BTC non è TRENDING_DOWN.
   Motivo: in RANGING con BTC in downtrend le altcoin continuano a scendere ("catching
   falling knives") — i dati lo hanno dimostrato (WR MR crollato a 42%, SOL 0% WR).
9. **PnL netto fee**: ogni PnL è calcolato al netto delle commissioni reali.
10. **Limiti persistenti**: daily/weekly loss sopravvivono ai riavvii (risk_state.json).
11. **Anti-fantasma** (v4.6): stato locale sincronizzato col conto Kraken reale (vedi sotto).

---

## 📖 Stats Engine / Journaling (v4.4+)

Ogni trade chiuso è registrato in `trades.jsonl` con: time, ora, simbolo, motore,
entry/exit, qty, PnL netto, regime, RSI. Il comando Telegram `/stats` calcola:
- Win rate, profit factor, avg win/loss, R medio realizzato
- Breakdown per **motore**, **simbolo**, **ora del giorno**, **regime**

È lo strumento che ha rivelato la falla del breakout in RANGING → decisione v4.5.

---

## 📱 Comandi Telegram

| Comando | Funzione |
|---------|----------|
| `/balance` | Saldo USDT + PnL giornaliero/settimanale |
| `/positions` | Posizioni aperte |
| `/pnl` | PnL dettagliato (oggi, settimana, MR) |
| `/stats` | Statistiche complete (win rate, breakdown) |
| `/status` | Stato bot, Volatility Guard, pausa, cooldown |
| `/risk` | Esposizione e limiti di rischio |
| `/log` | Ultime 20 righe del log |
| `/pause` `/resume` | Sospendi/riprendi nuovi ingressi |
| `/stop` | Ferma il bot |
| `/help` | Lista comandi |

Sicurezza: il bot esegue comandi SOLO dalla chat autorizzata (`TELEGRAM_CHAT_ID`).

---

## 🚀 Procedura di deploy (standard)

```bash
cd ~/crypto_bot
BASE="https://raw.githubusercontent.com/rostiomar83-byte/eoaprinting/claude/crypto-bot-progress-jxxhty/crypto_bot"
wget -q "$BASE/main.py" -O main.py        # + altri file modificati (config.py, stats.py, ...)
pkill -f "watchdog.sh"; pkill -f "main.py"; sleep 3
nohup bash watchdog.sh >/dev/null 2>&1 &
sleep 15 && pgrep -af "main.py|watchdog" && grep "AVVIATO" ~/crypto_bot/bot.log | tail -1
```

**Regola d'oro:** dopo il deploy verifica sempre **1 solo watchdog + 1 solo main.py**.
Processi doppi = ordini duplicati sullo stesso conto = problema reale.

---

## 🔐 Sicurezza

- Chiave API Kraken: **niente prelievi**, **IP whitelist** 136.114.165.253/32
- `.gitignore` protegge: `.env`, `*.key`, `*.pem`, file di stato, log, `__pycache__`
- `.env.example` come template (nessun valore reale committato)
- Telegram autenticato per chat_id

---

## 📜 Storia versioni

| Ver | Cosa |
|-----|------|
| v4.1-4.3 | Edizione professionale: fee accounting, ATR 1h, R:R 1:3.3, partial TP, Volatility Guard, sizing adattivo, 5 simboli |
| **v4.4** | Mean Reversion → **ordini reali** su Kraken (era virtuale). Cache 4H EMA (anti rate-limit). Comandi /log /pause /resume /risk. Stats engine + journaling /stats |
| **v4.5** | **Breakout solo in TRENDING_UP** (decisione data-driven dai /stats: breakout 0% WR in RANGING, MR 83%) |
| **v4.6** | **Anti posizione/monete fantasma**: BUY registra solo con ID ordine valido; SELL MR chiude lo stato solo se la vendita ha successo (altrimenti riprova) |
| **v4.7** | **MR gate doppio**: BUY_MR solo in RANGING + BTC TRENDING_DOWN = blocco totale MR. Risolve il WR MR crollato a 42% (SOL 0%, ETH 33%) durante discesa BTC. Eliminato il ramo TRENDING_DOWN nell'entrata MR (era catching falling knives). |

---

## 🧠 Decisioni chiave e razionale

- **Fee come nemico n.1**: con 0.52% round-trip, gli scalp su 5m non battono le
  commissioni. → sizing su ATR 1h (movimenti ~0.8-1.5% che coprono le fee).
- **MR reale, non virtuale**: in mercato laterale il Mean Reversion è il motore
  che rende → attivato con ordini veri (v4.4).
- **Separazione regime↔strategia** (v4.5): i dati reali hanno mostrato che i
  breakout perdono in RANGING (rotture finte = whipsaw). Ogni motore lavora solo
  dove ha edge. Reversibile via flag `BREAKOUT_ONLY_TRENDING_UP`.
- **MR ≠ buy any dip** (v4.7): il Mean Reversion ha senso solo quando il mercato
  oscilla attorno a un equilibrio (RANGING). Se BTC scende, ogni rimbalzo locale è
  un'illusione — il vero trend è down. I dati (MR WR 83% → 42% in 3 giorni di
  BTC in calo) hanno confermato: il motivo delle perdite non era la strategia MR in
  sé, ma il contesto macro sbagliato in cui veniva usata.
- **Decidere coi dati, non con l'intuizione**: niente cambi di strategia su 1 trade;
  agire quando c'è tesi forte + dati coerenti + azione conservativa.

---

## ⚠️ Lezioni apprese

1. **Una sola fonte di verità.** Far girare due assistenti/copie diverse del codice
   genera analisi che sembrano giuste ma riferiscono variabili inesistenti
   (es. `config.TESTNET`, `risk_15m`, clone `eoaprinting` vecchio con AVAX).
   Prima si verifica sui file veri, poi si agisce.
2. **Processi doppi = ordini duplicati.** Sempre 1 watchdog + 1 main.py.
3. **Fuso orario:** i log usano l'ora locale del VM (CEST, UTC+2); i filtri orari
   lavorano in UTC. Un "NO-HOURS" alle 08:55 locali = 06:55 UTC, corretto.
4. **Il contesto macro batte la strategia locale.** MR può avere WR 83% in
   condizioni normali e crollare a 42% in pochi giorni se BTC scende. Il regime
   locale (RANGING su SOL) non è sufficiente: bisogna guardare il quadro globale
   (BTC TRENDING_DOWN = stop MR su tutto). Lezione appresa dalla perdita -$0.74.

---

## 🔭 Prossimi passi (da fare coi dati in mano)

1. **Checkpoint /stats a ~20-30 trade post-v4.7**: verificare che il gate doppio
   (RANGING only + BTC no-down) riporti MR sopra WR 65%+. Se BTC torna laterale
   il bot riprende a fare BUY_MR normalmente.
2. **Verificare che v4.5 abbia risanato i breakout**: dopo 10+ trade TRENDING_UP,
   controllare se MultiTF/TRIX hanno WR accettabile. Se no → disattivare del tutto.
3. **Limit order maker per MR**: paghi 0.16% invece di 0.26% (fee -38%). Da fare
   con cautela (gestione fill/timeout/cancel) DOPO aver misurato col journaling se
   le fee sono davvero il problema. Lo stats engine misura il problema che i limit
   order dovrebbero risolvere.
4. **Se BTC resta TRENDING_DOWN a lungo**: il bot starà fermo su MR. È corretto —
   meglio non tradare che perdere. Riaprirà quando il mercato lo permette.
