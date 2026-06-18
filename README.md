# EoA Printing — Sito vetrina

Sito statico HTML/CSS/JS per portfolio EoA Printing.

## Struttura

```
EoA_SITE/
├── index.html              ← home (single page con sezioni)
├── privacy.html            ← privacy policy (GDPR)
├── cookies.html            ← cookie policy
├── README.md               ← questo file
└── assets/
    ├── css/style.css       ← stylesheet completo
    ├── js/main.js          ← menu mobile + cookie banner
    └── img/
        ├── favicon.svg     ← icona tab browser
        └── (foto portfolio reali da aggiungere qui)
```

## Personalizzazione PRIMA di pubblicare

### 1. Sostituire numero WhatsApp (in index.html)

Cerca `393XXXXXXXXX` (4 occorrenze) e sostituisci con il tuo numero.
Formato: `+39 3XX XXX XXXX` → URL `393XXXXXXXXX`

```html
<a href="https://wa.me/393XXXXXXXXX">
```

Diventa per esempio:
```html
<a href="https://wa.me/393331234567">
```

### 2. Sostituire email

Cerca `info@eoaprinting.it` (4 occorrenze) e sostituisci con la tua email reale.

### 3. Sostituire Instagram

Cerca `instagram.com/eoaprinting` e sostituisci con tuo username.

### 4. Configurare form contatti (Formspree)

1. Vai su [formspree.io](https://formspree.io)
2. Registrati gratis (50 messaggi/mese)
3. Crea un "Form" → ti dà un ID tipo `f/abc123xyz`
4. In `index.html` cerca `YOUR_FORM_ID` e sostituisci con il tuo ID

```html
<form ... action="https://formspree.io/f/abc123xyz" method="POST">
```

### 5. Aggiungere foto portfolio

1. Metti le foto JPG/PNG in `assets/img/portfolio/` (crea cartella)
2. In `index.html` sostituisci i `<div class="portfolio__placeholder">` con `<img>`:

```html
<div class="portfolio__item">
    <img src="assets/img/portfolio/labubu_cover.jpg" alt="Cover Labubu" style="width:100%; aspect-ratio: 4/3; object-fit:cover;">
    <p>Cover Labubu trasparente con LED</p>
</div>
```

### 6. (Opzionale) Logo grafico

Metti il tuo logo PNG/SVG in `assets/img/logo.png` e modifica `.logo` in index.html:

```html
<a href="#home" class="logo">
    <img src="assets/img/logo.png" alt="EoA Printing" style="height:36px">
</a>
```

## Pubblicazione GRATIS su GitHub Pages

### Step 1: account GitHub
1. Vai su [github.com](https://github.com)
2. Registrati (gratis)

### Step 2: crea repository
1. Clicca "+" in alto a destra → "New repository"
2. **Repository name**: `EoAprinting` (o nome che vuoi)
3. **Public** (obbligatorio per GitHub Pages gratis)
4. **NON** aggiungere README/gitignore (già presenti)
5. "Create repository"

### Step 3: upload del sito
**Opzione A — via web** (più semplice):
1. Nella pagina del repo, clicca "uploading an existing file"
2. Trascina TUTTI i file e cartelle di `EoA_SITE/` (NON la cartella esterna, solo il contenuto)
3. Scroll giù → "Commit changes"

**Opzione B — via git** (se sai usarlo):
```bash
cd EoA_SITE
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TUO_USERNAME/EoAprinting.git
git push -u origin main
```

### Step 4: attiva GitHub Pages
1. Nel repo, vai su **Settings** (tab in alto)
2. Menu sinistro → **Pages**
3. Sotto "Source": seleziona **Deploy from a branch**
4. Branch: **main**, folder: **/ (root)**
5. **Save**
6. Aspetta 1-2 minuti, poi torna su Settings → Pages: vedrai l'URL pubblico tipo:
   `https://TUO_USERNAME.github.io/EoAprinting/`

### Step 5: collegare dominio personalizzato

#### Acquista dominio (€8-12/anno)
- [Aruba.it](https://aruba.it) → cerca `EoAprinting.it`
- Se libero → registra (€8-12)

#### Configura DNS
Nel pannello del provider del dominio (es. Aruba), aggiungi i record DNS:

| Tipo | Nome | Valore |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | TUO_USERNAME.github.io |

(IP ufficiali GitHub Pages: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)

#### Configura GitHub Pages con dominio
1. Crea file `CNAME` nella root del repo con dentro solo il nome dominio:
   ```
   eoaprinting.it
   ```
2. Settings → Pages → "Custom domain" → scrivi `eoaprinting.it` → Save
3. Aspetta propagazione DNS (10 min - 24h)
4. Quando vedi il pallino verde "DNS check successful" → spunta "Enforce HTTPS"

### Step 6: testa

Apri `https://eoaprinting.it` → deve apparire il sito.

## Modifiche future

Ogni modifica al sito:
1. Modifica i file in locale
2. Carica su GitHub (via web o git push)
3. GitHub Pages aggiorna in 1-2 minuti

## Costi totali

| Voce | Costo |
|---|---|
| Hosting GitHub Pages | **€0** |
| Dominio eoaprinting.it (1 anno) | ~**€8-12** |
| Form contatti Formspree (50 msg/mese) | **€0** |
| Email professionale @eoaprinting.it | Opzionale, €3-5/mese (Aruba o Google Workspace) |

**Totale primo anno: ~€10** (dominio).
Successivi: rinnovo dominio annuale.

## Aggiornamenti contenuti

Quando vuoi cambiare testo, prezzi, foto:
- **Modifica diretta**: apri il file `.html` con Notepad++ o VS Code, modifica, carica su GitHub
- **Foto**: aggiungi/sostituisci in `assets/img/portfolio/`

## Supporto

In caso di problemi, chiedimi:
- Email non funziona dal form → controlla formspree dashboard
- Dominio non risolve → verifica DNS con [whatsmydns.net](https://whatsmydns.net)
- Sito non si aggiorna → svuota cache browser (Ctrl+F5)
