# 📚 KNOWLEDGE — CryptoBot Omar

> Fonte unica di verità del progetto. Se un'analisi o un'altra chat parla di
> codice che non corrisponde a questo documento, **verifica sui file veri prima
> di agire**. La verità è una sola: il repo GitHub `claude/crypto-bot-progress-jxxhty`
> + il VM che gira da quel repo.

Ultimo aggiornamento: **v4.13** — 2026-08-04

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
| **CryptoBot Omar** (questo) | `~/crypto_bot/` | Attivo, v4.13 |
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

### 3. Mean Reversion — **DISABILITATO da v4.12**
RSI + tocco banda Bollinger inferiore + Fast RSI(7) + candela di recupero. **Opera SOLO in RANGING** (da v4.7).
**Bloccato anche se BTC è TRENDING_DOWN** (blocco globale aggiunto in v4.7).
Da v4.4 piazza **ordini reali** (prima era virtuale/paper).
Le uscite SELL_MR su posizioni già aperte funzionano in qualsiasi regime.
**Filtro candle recovery (v4.8):** non si compra in caduta libera — la candela corrente
deve chiudere verde e sopra la chiusura precedente (prima reazione confermata).
**⛔ v4.12: DISABILITATO** — 56 trade confermano RANGING WR 36%, -$2.49 totali.
Reversibile: `MR_ENABLED = True` in `config.py`.

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
MIN_CAPITAL_USD = 160                # v4.10: hard stop — sotto questa equity il bot si mette in pausa
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
10. **Limiti persistenti**: daily/weekly loss sopravvivono ai riavvii (`risk_state.json` — salvato ad ogni trade, ricaricato all'avvio).
11. **Anti-fantasma** (v4.6): stato locale sincronizzato col conto Kraken reale. BUY registra SOLO se `order.get("id")` esiste. SELL aggiorna stato SOLO se la vendita è confermata, altrimenti riprova.
12. **Thread safety** (v4.9): `threading.Lock` su `positions` — il thread Telegram e il main loop non corrono in race condition su letture/scritture del dict posizioni.
13. **Log rotation** (v4.9): `RotatingFileHandler` 500KB × 3 file — il log non cresce a dismisura sui riavvii lunghi.
14. **Capital Guard** (v4.10/v4.11): se equity < $160, il bot si mette in pausa automatica con alert Telegram. Le posizioni aperte restano gestite dai loro stop. **Auto-resume (v4.11)**: il bot riprende automaticamente quando equity risale ≥ $160 (flag `_capital_guard_active` distingue questa pausa da un `/pause` manuale). Riprende manualmente con `/resume` o aggiunta di capitale.

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
| **v4.9** | **Robustezza**: `RotatingFileHandler` (500KB×3 file — il log non cresce più per sempre). `threading.Lock` su `positions` (protegge accessi cross-thread tra main loop e Telegram handlers). Nessun impatto funzionale — solo hardening. |
| **v4.10** | **Capital Guard**: hard stop automatico a $160 di equity. Se il saldo scende sotto la soglia: bot in pausa automatica + alert Telegram con istruzioni. Le posizioni aperte restano gestite dai loro SL/TP. Riprende con `/resume` o aggiunta di capitale. Aggiunto `MIN_CAPITAL_USD = 160` in `config.py`. |
| **v4.11** | **3 bug fix**: (1) `send_message()` chunking automatico a 4000 char (Telegram cap 4096 → /stats /log daily report non vengono più troncati). (2) Capital Guard auto-resume quando equity risale sopra soglia (flag `_capital_guard_active` distingue da `/pause` manuale). (3) `place_sell()` legge `positions` dentro `position_lock` con shallow copy (elimina race condition tra main loop e thread Telegram). |
| **v4.12** | **MR disabilitato**: 56 trade dimostrano RANGING sistematicamente perdente (WR 36%, -$2.49). Flag `MR_ENABLED = False` in config.py — reversibile. Le posizioni MR già aperte vengono comunque gestite da SL/TP/TIMEOUT. |
| **v4.13** | **Fix R:R strutturale** (root cause dei -$2.73 totali): (1) ADX ≥ 20 su BUY_5M in `strategy_multiTF.py` — entra solo in trend con forza reale (TRIX aveva 100% WR con ADX, BUY_5M senza ADX aveva WR 52% e perdeva). (2) Partial TP rimosso da `main.py` — le posizioni corrono a TP pieno (5×ATR) o trailing SL. R:R teorico 1:3.3, breakeven WR = 23% (da 59% con partial TP). |

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
- **MR disabilitato (v4.12)**: dopo 56 trade, RANGING è una trappola sistematica
  (WR 36%, -$2.49). Bot opera solo in TRENDING_UP. Reversibile: `MR_ENABLED = True`.
- **ADX come gate universale (v4.13)**: TRIX aveva 100% WR perché richiede ADX > 20.
  BUY_5M senza ADX entrava in trend deboli → R:R 1:0.7. Con ADX ≥ 20 su tutti i
  motori, si entra solo quando il trend ha forza reale. Regola: nessun motore breakout
  senza conferma ADX.
- **Partial TP rimosso (v4.13)**: il partial TP vendeva 50% a 2×ATR e spostava SL a
  breakeven. In trend deboli (pre-ADX filter) questo creava R:R 1:0.7. Senza partial TP
  + con ADX filter: R:R 1:3.3 puro (win = 5×ATR, loss = 1.5×ATR). Breakeven WR scende
  da 59% a 23% — molto più gestibile con WR atteso 55-65%.
- **Scalare SOLO dopo strategia positiva**: aumentare gli importi su strategia perdente
  amplifica le perdite linearmente. Prima conferma dati (15-20 trade post-v4.13),
  poi scala da $20 a $30-40 per trade.
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
7. **SELL_MR uccide il R:R.** Il SELL_MR (uscita RSI-based) chiude le posizioni
   MR prima del TP, catturando +$0.14 di media mentre il SL colpisce per -$0.20.
   Con WR 34% e R:R 1:0.7 il sistema perde matematicamente. Soluzione: MR disabilitato.
8. **ADX è il filtro più importante.** TRIX (ADX > 20) = 100% WR su 4 trade.
   BUY_5M (no ADX) = 52% WR, -$2.22 su 31 trade. La differenza è tutta nel filtro
   di forza trend. Senza ADX si entra in "trend" che sono in realtà rimbalzi nel RANGING.
9. **Non scalare prima che la strategia sia positiva.** Raddoppiare importi su
   strategia perdente raddoppia le perdite. Sequenza corretta: fix → 15-20 trade →
   conferma dati → poi scala.

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
| **2026-07-22** | **56** | **50.0%** | **-$1.62** | Snapshot post-v4.11. Vedi breakdown qui sotto. |
| **2026-08-04** | **64** | **46.9%** | **-$2.73** | Post-v4.12. 8 nuovi BUY_5M (WR ~25%) — R:R 1:0.7 confermato problema. Equity ~$194, balance libero $173.98. v4.13 deployato oggi. |

**Snapshot 2026-07-22 — 56 trade (28W/28L):**
| Motore | Trade | WR | PnL | PF |
|--------|-------|----|-----|----|
| TRIX | 4 | 100% | +$1.39 | ∞ |
| BUY_5M | 23 | 61% | -$1.11 | 0.59 |
| MR | 29 | 34% | -$1.90 | 0.35 |

| Regime | Trade | WR | PnL |
|--------|-------|----|-----|
| TRENDING_UP | 25 | 72% | +$1.17 |
| RANGING | 28 | 36% | -$2.49 |

| Simbolo | Trade | WR | PnL |
|---------|-------|----|-----|
| LINK | 11 | 55% | +$0.17 |
| XRP | 4 | 50% | -$0.04 |
| SOL | 12 | 50% | -$0.33 |
| BTC | 17 | 41% | -$0.42 |
| ETH | 12 | 58% | -$0.99 |

**R medio realizzato: 1:0.7** (target 1:3.3) — il SELL_MR chiude troppo presto le wins.
**Conclusione dati:** TRENDING_UP funziona (72% WR, +$1.17). MR affossa tutto (-$1.90).
Senza MR il bot avrebbe fatto: +$1.39 (TRIX) - $1.11 (BUY_5M) = **+$0.28 netto**.
→ Decisione pendente: **disabilitare MR (v4.12)**.

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

## 🚨 Falsi allarmi — Bug già risolti (per AI esterne)

Questa sezione esiste per evitare che un'AI esterna che legge il file segnali
come "bug aperti" delle vulnerabilità che sono già state corrette.

| Bug citato | Stato | Dove è risolto |
|-----------|-------|----------------|
| "Ordini senza guard su fallimento API → posizione fantasma" | ✅ **RISOLTO in v4.6** | `main.py` — `place_buy()` e blocco MR BUY: `if not (order and order.get("id")): abort`. Registro solo se ID confermato. |
| "weekly_loss non persistito → si resetta al riavvio" | ✅ **RISOLTO** | `risk_manager.py` — `_save()` su `risk_state.json` ad ogni `record_pnl()`. `_load()` ricarica all'avvio. |
| "btc_regime calcolato solo all'avvio e mai aggiornato" | ✅ **NON È MAI STATO UN BUG** | `main.py` riga ~507: `btc_regime = get_regime(btc_df)` è dentro il `while _running:` loop → ricalcolato ogni 60 secondi. |
| "Race condition su positions dict" | ✅ **RISOLTO in v4.9** | `threading.Lock` aggiunto su tutte le letture/scritture cross-thread di `positions`. |
| "Log cresce senza limiti" | ✅ **RISOLTO in v4.9** | `RotatingFileHandler(500KB × 3)` sostituisce `FileHandler`. |

**Regola:** se un'AI segnala bug su questo bot, verifica SEMPRE sul codice reale
prima di agire. La fonte di verità è il repo, non l'analisi di una chat esterna.

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

1. **✅ FATTO — v4.12: MR disabilitato** (2026-07-22, 56 trade).
   Flag `MR_ENABLED = False`. Bot opera solo in TRENDING_UP.
2. **✅ FATTO — v4.13: ADX filter + Partial TP rimosso** (2026-08-04, 64 trade).
   ADX ≥ 20 su BUY_5M. Partial TP eliminato → R:R teorico 1:3.3.
3. **Checkpoint /stats post-v4.13** (obiettivo: ~15-20 nuovi trade).
   Target: WR TRENDING_UP >65%, R medio ≥ 1:2, PnL netto positivo.
   Se positivo → scala `TRADE_AMOUNT_TRENDING_UP` da $20 a $30-40.
   Se negativo → diagnosi TRIX vs BUY_5M separatamente.
4. **Verificare fee Kraken** (possibile cambio taker 0.26%→0.80% in Tier 1).
   Se confermato: aggiornare `FEE_RATE` in config.py + ricalibrare `MIN_TP1_NET_PCT`.
5. **Implementare Donchian 1H** (backlog P1) dopo il checkpoint /stats post-v4.13.
6. **Se mercato resta RANGING a lungo**: bot sarà idle. È corretto — meglio non
   tradare che perdere come in RANGING storico (-$2.49 su 28 trade).
7. **Freelance**: 5 proposte Upwork/giorno + Reddit r/forhire ogni giorno. Primo
   cliente anche a prezzo ribassato → recensione → poi alza.
