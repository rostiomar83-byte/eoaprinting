# 📚 KNOWLEDGE — CryptoBot Omar

> Fonte unica di verità del progetto. Se un'analisi o un'altra chat parla di
> codice che non corrisponde a questo documento, **verifica sui file veri prima
> di agire**. La verità è una sola: il repo GitHub `claude/crypto-bot-progress-jxxhty`
> + il VM che gira da quel repo.

Ultimo aggiornamento: **v4.8** — 2026-07-03

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

**3 bot sul VM (non toccare gli altri due!):**
| Bot | Cartella | Stato |
|-----|----------|-------|
| **CryptoBot Omar** (questo) | `~/crypto_bot/` | Attivo, v4.8 |
| massabot | `/home/Utente/massabot` | Lasciare invariato |
| ortobot | `/home/Utente/ortobot` | Lasciare invariato |

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
RSI + tocco banda Bollinger inferiore + Fast RSI(7) + candela di recupero. **Opera SOLO in RANGING** (da v4.7).
**Bloccato anche se BTC è TRENDING_DOWN** (blocco globale aggiunto in v4.7).
Da v4.4 piazza **ordini reali** (prima era virtuale/paper).
Le uscite SELL_MR su posizioni già aperte funzionano in qualsiasi regime.
**Filtro candle recovery (v4.8):** non si compra in caduta libera — la candela corrente
deve chiudere verde e sopra la chiusura precedente (prima reazione confermata).

---

## 📐 Parametri chiave (config.py)

```
SYMBOLS = BTC, ETH, SOL, LINK        # v4.8: XRP rimosso (storico negativo)
TRADE_AMOUNT_TRENDING_UP = 20        # v4.8: ridotto da 40 (breakout non ancora provato)
TRADE_AMOUNT_RANGING     = 15        # v4.8: ridotto da 25
MAX_OPEN_POSITIONS = 2               # max posizioni MultiTF/TRIX simultanee
MAX_EXPOSURE_PCT   = 0.45            # v4.8: ridotto da 70% — protezione capitale prima
MAX_DAILY_LOSS_USDT  = 5             # v4.8: ridotto da 30 (su $210 era troppo permissivo)
MAX_WEEKLY_LOSS_USDT = 12            # v4.8: ridotto da 60
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
ADX_THRESHOLD = 25                   # soglia ADX per classificare trend vs ranging
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

## 📡 Report automatici Telegram

- **Heartbeat ore 8 e 14**: balance + daily PnL + posizioni aperte
- **Report giornaliero ore 20 (v4.8)**: riepilogo completo della giornata
  (PnL totale, trade chiusi, win rate, breakdown per motore)
  Funzione: `daily_report()` in `stats.py`

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

**IMPORTANTE — `~/crypto_bot` NON è un repo git.** Il `git pull` non funziona sul VM.
I file si aggiornano SOLO con wget (vedi sopra). Il repo git esiste solo in locale
(ambiente Claude) e su GitHub. Sul VM arrivano i file già compilati via wget.

**Comando di verifica deploy:**
```bash
grep "v4\." ~/crypto_bot/main.py | head -2
grep "is_ranging\|RANGING only" ~/crypto_bot/strategy_meanrev.py | head -2
pgrep -af "main.py|watchdog"
tail -5 ~/crypto_bot/bot.log
```

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
| **v4.8** | **ADX regime fix** (critico): ADX > soglia tornava RANGING invece di TRENDING → ora se ADX alto, sempre TRENDING (mai RANGING con ADX 33-40). **Candle recovery MR**: non si compra in caduta libera (close>open E close>prev_close). **Limiti rischio conservativi**: daily $30→$5, weekly $60→$12, exposure 70%→45%. **Sizing ridotto**: TRENDING_UP $40→$20, RANGING $25→$15. **XRP rimosso** (storico negativo). **Report giornaliero ore 20** via Telegram (daily_report()). RSI MR più selettivo: MR_RSI_BUY 35→28, RSI_FAST_OVERSOLD 32→28. |

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
5. **Il VM non è un repo git.** `git pull` sul VM non funziona — i file vengono
   scaricati via wget. Dopo ogni modifica al codice, usare sempre il blocco wget
   della procedura di deploy. Il `git log` funziona solo nell'ambiente Claude locale.
6. **Verifica sempre DOPO il deploy.** Un deploy senza verifica non è un deploy.
   Comando minimo: `grep "vX.Y" ~/crypto_bot/main.py | head -1` per confermare
   la versione corretta girata.

---

## 💼 Reddito freelance parallelo

Il bot da solo non arriva a €300-500/mese con $210 di capitale. La strategia
parallela è vendere la competenza di costruire bot su Fiverr/Upwork.

**Cosa è stato creato:**
- Repo GitHub pubblico: `rostiomar83-byte/crypto-price-alert-bot`
  (bot di demo funzionante — CoinGecko API, /add /list /del, persistenza, multi-thread)
- Gig Fiverr pubblicato: categoria **Trading Bots Development**
  Pacchetti: €60 (Starter) / €170 (Full) / €400 (Pro + Deploy)
- Gig Telegram/bot generico: €25 / €75 / €180
- Template Upwork + Reddit r/forhire pronti in `portfolio-demos/OUTREACH_TEMPLATES.md`

**Regole d'oro Fiverr:**
- Mai promettere profitti su bot di trading — vendi la costruzione, non i guadagni
- Prima riga della proposta SEMPRE personalizzata sul loro progetto
- Link GitHub in ogni proposta (distingue dal 90% degli altri)
- Primo cliente anche a prezzo ribassato → recensione 5★ → poi alza prezzi
- Messaggi con link esterni = scam al 100% (segnala e blocca)

**File di riferimento:**
- `portfolio-demos/FIVERR_GIG_TRADING.md` — kit completo gig trading bot
- `portfolio-demos/FIVERR_GIG.md` — kit gig Telegram/automazione generico
- `portfolio-demos/OUTREACH_TEMPLATES.md` — proposte Upwork, Reddit, pricing

---

## 📊 Snapshot PnL storico

| Data | Trade | WR | PnL | Note |
|------|-------|----|-----|------|
| ~2026-06-25 | 6 | 66.7% | +$0.51 MR | Prima snapshot MR reale (v4.4) |
| ~2026-06-27 | 9 | 55.6% | -$1.74 BUY_5M | Breakout in RANGING → v4.5 gate |
| 2026-06-30 | 15 | 33.3% | -$2.48 | BTC TRENDING_DOWN, MR catching knives |
| 2026-07-02 | 16 | 31.2% | -$2.53 | Baseline pre-v4.7 (ultimo prima del fix) |
| 2026-07-03 | — | — | — | v4.8 deploy: ADX fix + candle recovery + limiti conservativi |

**Baseline v4.8 (da usare come confronto al prossimo /stats):**
- MR: -$0.78, 13 trade, WR 38%
- BUY_5M: -$1.74, 3 trade, WR 0% — CONGELATO (nessun nuovo trade da v4.5)
- SOL: 0% WR (-$1.22), ETH: 33% WR (-$1.07)
- Ora peggiore: 02:00 UTC (-$1.58) — già risolta da time filter
- Regime RANGING: -$1.48 (13 trade) — MR apriva anche con BTC down → v4.7

---

## 🚫 Strade valutate e scartate (con perché)

| Strada | Perché scartata ora |
|--------|-------------------|
| **Dropshipping automatico** | Temu/Shein hanno distrutto i margini. Meta Ads costi triplicati. Richiede €300-1000 budget ads non disponibile. Da rivalutare con €500+ liberi. |
| **CFD / XTrend Lite / app "Start from $10"** | Broker guadagna sullo spread, leva = rischio perdere più del capitale, nessun controllo sul codice. Opposto di quello che stiamo costruendo. |
| **Sniper Pro Scanner (Andrei Lefter)** | Indicatore TradingView a pagamento che fa quello che il bot già fa automaticamente su 5 asset H24. Trading manuale richiede tempo che il bot elimina. |
| **DeFi / LP / Curve / bribes** | Gas fee mangiano tutto sotto $500 di capitale. Complessità smart-contract alta. |
| **Funding-rate arbitrage** | Richiede exchange con perp (Binance/Bybit). Con $210 i margini non coprono i costi di trasferimento. Da rivalutare a $1.000+. |
| **Airdrop farming** | Tempo pieno, rendimento non calcolabile, gas burn. |
| **ETH liquid staking** | Solo 2-2.7% annuo. Con $210 totali non vale la frammentazione del capitale. Rivalutare quando capitale cresce. |

---

## 📋 Modifiche da fare a breve (backlog prioritizzato)

### Priorità 1 — Donchian Breakout 1H
Upgrade naturale del MultiTF. Usa i massimi/minimi delle ultime 20 candele 1H come
livelli di breakout. Meno trade, meno fee drag, stessa architettura ATR per SL/TP.
Filtra molti falsi segnali del 5m. Da fare DOPO il checkpoint /stats post-v4.8.

### Priorità 2 — VWAP Pullback 15m
Entra in trend durante i rientri verso il VWAP + RSI 40-50. Complementare a MR
(MR compra oversold estremi, VWAP Pullback compra dip normalizzati in trend).
Opera solo in TRENDING_UP, integra bene con l'architettura esistente.

### Priorità 3 — Crypto Rotation settimanale
Ogni domenica sera: ranking dei 4 asset (BTC/ETH/SOL/LINK) per momentum 7-day.
Sovrappeso l'asset più forte, sottopeso il più debole. Più complesso (richiede
cron job settimanale o logica calendario). Da fare dopo 1 e 2.

### Da verificare
- **Fee Kraken luglio 2026**: possibile cambio fee a taker 0.80% (da 0.26%) in Tier 1.
  Se confermato → aggiornare `FEE_RATE = 0.0026` in config.py + ricalibrare MIN_TP1_NET_PCT.
  Verifica il 9 luglio 2026 sul pannello Kraken.

---

## 🔭 Prossimi passi (da fare coi dati in mano)

1. **Checkpoint /stats a ~20-30 trade post-v4.8**: verificare che ADX fix + candle
   recovery portino MR sopra WR 65%+. Se BTC torna laterale il bot riprende BUY_MR.
2. **Verificare fee Kraken (9 luglio 2026)**: se cambiano le fee taker aggiornare
   FEE_RATE in config.py.
3. **Implementare Donchian 1H** (priorità 1 del backlog) dopo il checkpoint /stats.
4. **Verificare che v4.5 abbia risanato i breakout**: dopo 10+ trade TRENDING_UP,
   controllare se MultiTF/TRIX hanno WR accettabile. Se no → disattivare del tutto.
5. **Se BTC resta TRENDING_DOWN a lungo**: il bot starà fermo su MR. È corretto —
   meglio non tradare che perdere. Riaprirà quando il mercato lo permette.
6. **Freelance**: 5 proposte Upwork/giorno + Reddit r/forhire ogni giorno. Primo
   cliente anche a prezzo ribassato → recensione → poi alza. Le recensioni
   sbloccano il traffico organico su Fiverr.
