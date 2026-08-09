<br/>

<div align="center">
  <br/>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/TRINETRA-v1.0.0-8b5cf6?style=for-the-badge&logo=appveyor&labelColor=0b0f1a">
    <img src="https://img.shields.io/badge/TRINETRA-v1.0.0-8b5cf6?style=for-the-badge&logo=appveyor&labelColor=0b0f1a" alt="TRINETRA">
  </picture>
  <br/>
  <h3>India-Focused OSINT Intelligence Dashboard</h3>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"/>
    <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React 18"/>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
    <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript 5.6"/>
    <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
    <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
    <img src="https://img.shields.io/badge/Leaflet-1.9-199900?style=flat-square&logo=leaflet&logoColor=white" alt="Leaflet 1.9"/>
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"/>
    <img src="https://img.shields.io/badge/bcrypt-enabled-8A2BE2?style=flat-square" alt="bcrypt"/>
    <img src="https://img.shields.io/badge/tests-passing-22c55e?style=flat-square" alt="Tests Passing"/>
  </p>
  <br/>
</div>

> **Search any domain, IP, email, phone, or name — get 360° threat intelligence in seconds.**
>
> TRINETRA is an all-in-one OSINT platform built for India. It combines **15 parallel OSINT plugins**, a **live threat feed** powered by real malicious IP data, **automated watch monitoring**, an **interactive threat map dashboard**, an **AI chatbot assistant**, and a **Cashfree-powered credits & payments system** (flat 10 credits per search) — all wrapped in a modern, dark-themed web interface.

<br/>

<p align="center">
  <b>🐳 Docker Ready</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>🔍 OSINT Search</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>🗺️ Live Threat Map</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>📡 Real-Time Feed</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>👁️ Watch Monitoring</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>📊 Professional Reports</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>🧠 Relationship Graphs</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>🔐 User Registration</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>💳 Credits & Payments</b>&nbsp;&nbsp;·&nbsp;&nbsp;
  <b>🤖 AI Assistant</b>
</p>

<br/>

---

## 📋 Table of Contents

- [🚀 Quick Start (Docker)](#-quick-start-docker)
- [🔑 Environment Setup — API Keys & Credentials](#-environment-setup--api-keys--credentials)
- [🛠️ Manual Installation (No Docker)](#️-manual-installation-no-docker)
- [🎯 What TRINETRA Does](#-what-trinetra-does)
- [🏗️ Architecture & Workflow](#️-architecture--workflow)
- [🔍 OSINT Search — How It Works](#-osint-search--how-it-works)
- [📡 Live Threat Feed](#-live-threat-feed)
- [👁️ Watch Monitoring](#️-watch-monitoring)
- [🤖 AI Chatbot Assistant](#-ai-chatbot-assistant)
- [🗺️ Interactive Map](#️-interactive-map)
- [🔐 Authentication & User System](#-authentication--user-system)
- [💳 Credits & Payments](#-credits--payments)
- [📡 Real Data Sources](#-real-data-sources)
- [✨ Features](#-features)
- [📡 API Reference](#-api-reference)
- [🗂️ Project Structure](#️-project-structure)
- [⚙️ Configuration Reference](#️-configuration-reference)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

<br/>

---

## 🚀 Quick Start (Docker)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 24+)
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/INDRA.git
cd INDRA

# Copy and customize environment variables
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD

# Start all services
docker compose -p indra2 up -d --build
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:3000](http://localhost:3000) | React dashboard — register & start searching |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | FastAPI REST API |
| **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger documentation |
| **PostgreSQL** | `localhost:5432` | Main database (auth uses dedicated SQLite) |
| **Redis** | `localhost:6380` | Cache & TaskIQ broker |

### First-Time Steps

1. Open [http://localhost:3000](http://localhost:3000)
2. Click **Register** and create an account (first user becomes admin)
3. If payments are configured, you'll land on the **payment page** — new accounts start with **0 credits**, so pick a plan and pay via Cashfree (sandbox test card: `4111 1111 1111 1111`)
4. Start searching domains, IPs, emails, phones, or names — **every search costs a flat 10 credits**

### Useful Docker Commands

```bash
# View container logs
docker compose -p indra2 logs -f backend    # Backend logs
docker compose -p indra2 logs -f frontend   # Frontend logs

# Restart a service
docker compose -p indra2 restart backend

# Rebuild after code changes
docker compose -p indra2 build backend

# Stop everything
docker compose -p indra2 down

# Stop and delete volumes (wipes database)
docker compose -p indra2 down -v
```

<br/>

---

<br/>

---

## 🔑 Environment Setup — API Keys & Credentials

Everything below lives in **one file: `.env`** at the project root. You only create it once, and both Docker and manual (VS Code) mode read from it.

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

Open the new `.env` file in VS Code. It's fully commented — every variable explains itself — but here's the plain-language version of what to fill in.

### Step 2 — The one thing you MUST set

```env
POSTGRES_PASSWORD=CHANGE_ME_TO_A_STRONG_PASSWORD
```

This is the only required value. **Everything else below is optional** — the app runs and every core feature (search, watches, threat feed, map) works with zero additional keys. The 4 credential groups below just switch on extra functionality.

### Step 3 — Optional credentials (fill in only what you want to enable)

| # | Credential | Unlocks | Where to Get It |
|---|---|---|---|
| 1 | `GEMINI_API_KEY` | The AI Chatbot + AI-generated `.docx` reports | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — free |
| 2 | `TELEGRAM_BOT_TOKEN` | The Telegram OSINT bot | Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` |
| 3 | `CASHFREE_APP_ID` + `CASHFREE_SECRET_KEY` | Credit purchases / billing (leave empty = every search is free & unlimited) | [cashfree.com/developers](https://cashfree.com/developers) — sign up, use **sandbox** keys for testing |
| 4 | `SMTP_HOST` + `SMTP_USERNAME` + `SMTP_PASSWORD` | Actually emailing signup verification codes (leave empty = OTP codes print to the backend console/terminal instead — fully usable for local testing) | See Gmail example below, or any SMTP provider |

**If you leave all 4 groups empty:** the app still runs completely — AI chat shows a "not configured" message, Telegram bot doesn't start, every search is free (no credit gate), and OTP codes appear directly in your terminal log instead of an inbox. This is the fastest way to get the app running to check it works, before wiring up real credentials.

#### 1. Gemini (AI Chatbot)

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-latest
```

#### 2. Telegram Bot (optional OSINT bot)

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_OSINT_API_URL=
TELEGRAM_OSINT_API_KEY=
```

#### 3. Cashfree (Payments / Credits)

```env
CASHFREE_APP_ID=your_app_id
CASHFREE_SECRET_KEY=your_secret_key
CASHFREE_ENV=sandbox
CASHFREE_WEBHOOK_URL=http://localhost:8000/api/payment/webhook
```

Use **sandbox** credentials and `CASHFREE_ENV=sandbox` for testing — sandbox test card: `4111 1111 1111 1111`, any future expiry, CVV `123`.

#### 4. SMTP (Email delivery for signup verification codes)

Works with Gmail, SendGrid, Mailgun, Amazon SES, Zoho, Outlook — any standard SMTP provider. Gmail example:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=youraddress@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_FROM_EMAIL=youraddress@gmail.com
SMTP_FROM_NAME=TRINETRA
```

> Gmail requires an **App Password**, not your normal login password. Enable 2-Step Verification on the Google account, then generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

Until this is filled in, registering an account still works end-to-end — the verification code is printed in the backend's console output (`docker compose -p indra2 logs -f backend`, or directly in the VS Code terminal in manual mode) instead of being emailed.

### Step 4 — Run the project (pick one)

**Option A — Docker (recommended, one command):**
```bash
docker compose -p indra2 up -d --build
```
See [🚀 Quick Start (Docker)](#-quick-start-docker) above for the full walkthrough.

**Option B — Manual, inside VS Code:** see [🛠️ Manual Installation](#️-manual-installation-no-docker) directly below — it walks through opening two integrated terminals (one for backend, one for frontend) with the exact commands to paste.

<br/>

---

## 🛠️ Manual Installation (No Docker)

Use this if you don't have Docker, or want to run everything directly inside VS Code for development.

### Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite (included with Python) or PostgreSQL 15 (optional)
- Make sure you've already created `.env` — see [🔑 Environment Setup](#-environment-setup--api-keys--credentials) above

### Open the project in VS Code

```bash
cd INDRA
code .
```

You'll run the backend and frontend as **two separate processes**, so open **two integrated terminals** side by side: `` Ctrl+` `` (backslash key, below Esc) to open one terminal, then click the **split terminal** icon (or `` Ctrl+Shift+5 ``) to open a second one next to it.

### Terminal 1 — Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server (Vite dev proxy targets localhost:8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Leave this terminal running — it's your live backend log (this is also where OTP verification codes will print if `SMTP_HOST` isn't set). The database (`trinetra.db`) and the auth tables are created automatically on first startup. The first user to register becomes an admin.

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npx vite --host 0.0.0.0 --port 3000
```

Leave this running too. Then open **http://localhost:3000** in your browser — register a new account and start searching.

### Terminal 3 (Optional) — TaskIQ Worker

By default in manual mode `REDIS_URL` is empty, so watch re-checks run **inline** inside the backend process automatically — you don't need this third terminal for Watch Monitoring to work. Only run it if you've deliberately set `REDIS_URL` in `.env`:

```bash
cd backend
source venv/bin/activate
taskiq worker app.tasks.broker:broker app.tasks.watch_tasks
```

> **Note on ports:** The backend always runs on port **8000** — the Vite dev server proxies `/api` and `/ws` to `localhost:8000`, so manual mode must use **8000** too. All API examples in this README use port **8000**.

<br/>

---

## 🎯 What TRINETRA Does

### The Problem

Investigating a single domain typically means juggling **multiple separate tools**:

| Task | Tool | Time |
|------|------|------|
| WHOIS lookup | Separate website | ~2 min |
| DNS records | Another site | ~2 min |
| Port scan | nmap / Shodan | ~5 min |
| SSL check | Yet another tool | ~1 min |
| Subdomain discovery | crt.sh | ~2 min |
| Data breach check | Have I Been Pwned | ~1 min |
| CVE lookup | NVD | ~2 min |
| Tech fingerprint | Wappalyzer | ~1 min |
| Geo-location | ip-api.com | ~1 min |

**Total: 15–30 minutes** of context switching between tabs.

### TRINETRA's Solution

```
┌─────────────────────────────────────────────────────────┐
│              One Search. 15 Plugins.                      │
│              Results in 10–15 seconds.                    │
└─────────────────────────────────────────────────────────┘
```

**Five independent systems running simultaneously:**

1. **🔍 On-Demand OSINT Search** — Run 15 parallel plugins against any target
2. **📡 Live Threat Feed** — Background loop fetching real malicious IPs and cyber news
3. **👁️ Watch Monitoring** — Automated re-scanning with change detection alerts
4. **🗺️ Interactive Threat Map** — Real-time India-focused attack visualization
5. **🤖 AI Chatbot Assistant** — In-app SOC-analyst helper that explains findings and generates downloadable Word reports

<br/>

---

## 🏗️ Architecture & Workflow

### Container Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Docker Compose (indra2)              │
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐  │
│  │ Frontend │  │ Backend  │  │ Worker   │  │ DB   │  │
│  │ :3000→80 │  │ :8000    │  │ (TaskIQ) │  │:5432 │  │
│  │  React   │  │ FastAPI  │  │  Async   │  │ PG15 │  │
│  │  Nginx   │  │ Uvicorn  │  │  Tasks   │  │      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘  │
│       └─────────────┴─────────────┴────────────┘      │
│                         │                             │
│                    ┌────▼─────┐                       │
│                    │  Redis   │                       │
│                    │  :6380   │                       │
│                    │  Cache   │                       │
│                    └──────────┘                       │
└──────────────────────────────────────────────────────┘
```

### Application Flow

```
                    ┌──────────────────────────────────────────┐
                    │   User's Browser (port 3000)              │
                    │   React 18 + TypeScript + Vite            │
                    │   Leaflet Map + Cytoscape Graphs          │
                    └──────────────┬──────────┬─────────────────┘
                                  HTTP       WebSocket
                                    │            │
                    ┌───────────────▼────────────▼─────────────┐
                    │         FastAPI Backend                   │
                    │         (port 8000)                       │
                    │                                          │
                    │  ┌──────────┐  ┌────────────────────┐    │
                    │  │ REST API │  │ WebSocket Streaming│    │
                    │  │ /search  │  │ /ws/search         │    │
                    │  │ /auth/*  │  │ /ws/threats        │    │
                    │  │ /watch   │  └────────────────────┘    │
                    │  │ /plugins │                            │
                    │  └────┬─────┘                            │
                    │        │                                 │
                    │  ┌────▼─────────────────────────────┐    │
                    │  │    Plugin Orchestrator            │    │
                    │  │   ┌──────────┐ ┌──────────┐      │    │
                    │  │   │ 15 OSINT │ │ Watch    │      │    │
                    │  │   │ Plugins  │ │ Scheduler│      │    │
                    │  │   └──────────┘ └──────────┘      │    │
                    │  └──────────────────────────────────┘    │
                    │                                          │
                    │  ┌──────────────────────┐  ┌──────────┐ │
                    │  │ Threat Feed Service  │  │ TaskIQ   │ │
                    │  │ (background loop)    │  │ Worker   │ │
                    │  └──────────────────────┘  └──────────┘ │
                    │                                          │
                    │  ┌──────────────────┐                    │
                    │  │ Telegram Bot     │                    │
                    │  │ (optional)       │                    │
                    │  └──────────────────┘                    │
                    └──────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript + Vite | Dashboard UI, map, reports, graphs, live feed, watch panel |
| **Mapping** | Leaflet + react-leaflet | India threat map with animated attack vectors |
| **Graphs** | Cytoscape + cytoscape-dagre | Relationship visualization from scan results |
| **Backend** | FastAPI + Python 3.11 | REST API + WebSocket server |
| **Database** | PostgreSQL 15 (Docker) / SQLite (manual) | Main data storage |
| **Auth DB** | SQLite (dedicated `trinetra_auth.db`) | User accounts, sessions — independent of main DB |
| **Cache** | Redis 7 (Docker) | TaskIQ broker, caching |
| **Worker** | TaskIQ | Background watch task execution |
| **Data** | httpx + feedparser | External API calls + RSS parsing |
| **AI Chatbot** | Google Gemini API | In-app SOC assistant + report generation |
| **Report Export** | python-docx | Markdown → Word (.docx) report conversion |
| **Payments** | Cashfree PG | Credit packs via Cashfree checkout (sandbox/production) |
| **Bot** | python-telegram-bot | Telegram OSINT leak search (optional) |

<br/>

---

## 🔍 OSINT Search — How It Works

### Workflow

```
Target Query → Input Sanitizer → Auto-Detect Type → 15 Parallel Plugins → Stream Results
                      │                    │
                Control chars,        domain / IP /
                injection checks      email / phone / name
```

### Step-by-Step

1. **Input Sanitization** — Validated against maximum length (253 chars), no control characters, null bytes, or shell metacharacters
2. **Auto-Detect Type** — Regex matching for IP, email, domain, phone; falls back to "name"
3. **Plugin Registry** — Auto-discovers all `OSINTPlugin` subclasses at startup (no manual registration needed)
4. **Plugin Orchestration** — Fires matching plugins concurrently via `asyncio.gather` with configurable timeout
5. **WebSocket Streaming** — Results stream back in real-time via WebSocket as each plugin completes

### The 15 OSINT Plugins

| # | Plugin ID | Name | Category | What It Finds | Input Types |
|---|-----------|------|----------|---------------|-------------|
| 1 | `domain-record` | Domain Record | Infrastructure | WHOIS registration, registrar info, creation/expiry dates | domain |
| 2 | `name-servers` | Name Servers | Infrastructure | DNS records: A, AAAA, MX, NS, CNAME, TXT, SOA | domain |
| 3 | `port-scanner` | Port Scanner | Infrastructure | Open TCP ports (24 common ports), service identification | domain, ip |
| 4 | `ssl-health` | SSL Health | Infrastructure | Certificate validity, cipher suites, protocol support, grade | domain |
| 5 | `subdomain-finder` | Subdomain Finder | Infrastructure | Subdomains via crt.sh, HackerTarget API, DNS brute-force (185+ prefixes) | domain |
| 6 | `geo-locator` | Geo Locator | Infrastructure | Server location, country, city, ISP, ASN, coordinates | domain, ip |
| 7 | `http-headers` | HTTP Headers | Infrastructure | Security headers (HSTS, CSP, XFO, etc.), server info, cookies | domain |
| 8 | `tech-fingerprint` | Tech Fingerprint | Infrastructure | Web server, frameworks, CMS, Cloudflare detection | domain |
| 9 | `cve-alerts` | CVE Alerts | Threat Intel | Known vulnerabilities from NVD API matching target | domain, ip |
| 10 | `data-leaks` | Data Leaks | Threat Intel | Breach data from XposedOrNot, LeakCheck, LeakIX + curated breach DB (70+ India-specific breaches) | domain, email, username |
| 11 | `document-vault` | Document Vault | Threat Intel | Exposed documents, .env, .git/config, backup files on common paths | domain |
| 12 | `osint-leak` | OSINT Leak | Threat Intel | Deep breach search via Leakosint API (email, phone, name, IP, username) | email, phone, username, name, ip |
| 13 | `deep-search` | Deep Search | Advanced | Google dorking queries for sensitive files, admin panels, backups | domain, name |
| 14 | `live-feed` | Live Feed | Advanced | Real-time cyber news from RSS feeds (The Hacker News) | domain, ip, name |
| 15 | `surface-scan` | Surface Scan | Advanced | Aggregated risk score, attack surface analysis, key port scanning | domain, ip |

### Performance

| Metric | Value |
|--------|-------|
| **Full scan (all matching plugins)** | 10–15 seconds |
| **Plugins run per search** | Up to 15 (depending on target type) |
| **API rate limit (search)** | 10 req/min per IP |
| **Plugin timeout** | 30 seconds (configurable) |

<br/>

---

## 📡 Live Threat Feed

### Background Services

#### 1. RealThreatService (Malicious IP Fetcher)

- **Interval**: Every 10 minutes
- **Sources**: Three free threat intelligence feeds in parallel
  - **ThreatFox** (Abuse.ch) — Malware IOCs
  - **Feodo Tracker** — C2 server IPs (Dridex, Emotet, QakBot)
  - **IPsum** — Blacklisted IPs with detection scores
- **Processing**: Parse IPs, geo-locate via ip-api.com, build attack vectors, cache results
- **Health monitoring**: Each source is tracked with status, last fetch time, and error count

#### 2. RealNewsService (RSS News Fetcher)

- **Interval**: Every 5 minutes
- **Sources**: The Hacker News, BleepingComputer, KrebsOnSecurity, The Record
- **Deduplication**: Up to 2,000 seen URLs tracked
- **Rolling buffer**: Max 200 headlines kept in memory

#### 3. ThreatFeedService (Broadcast Loop)

- **Interval**: Every 8–12 seconds per event
- **On connect**: Sends initial state with 20 recent vectors + 10 recent news headlines + city data
- **Subscriber model**: Each WebSocket connection gets a dedicated `asyncio.Queue`

### Data Transparency

| Data Point | Real? | Source |
|-----------|-------|--------|
| Source IP | ✅ Real | ThreatFox, Feodo, IPsum feeds |
| Geo-location | ✅ Real | ip-api.com |
| Attack Type | ✅ Real | Feed metadata keywords |
| Malware Family | ✅ Real | Feodo (Dridex, Emotet, QakBot) / ThreatFox |
| Severity | ✅ Real | IPsum blacklist score / source credibility |
| Target City | ⚠️ Statistical | NCRB 2022 crime-weighted distribution |

<br/>

---

## 👁️ Watch Monitoring

Create watches to automatically re-scan targets at configurable intervals and get alerts when data changes.

### Key Features

- **Configurable Intervals**: 60 seconds to 7 days
- **Plugin Selection**: Choose exactly which plugins run per watch
- **Smart Change Detection**: Compares `gui_data` JSON across scans — generates human-readable diffs
- **Alert History**: Full timeline of changes per watch target
- **Pause/Resume**: Toggle watches on/off without deleting them
- **Data Source Tracking**: View health status of all threat feeds

### Retry Logic

On SQLite lock contention, watch tasks retry up to 3 times with exponential backoff (1s, 2s, 4s). Non-lock errors raise immediately.

<br/>

---

## 🤖 AI Chatbot Assistant

A floating in-app assistant (powered by Google Gemini) that acts as a SOC-analyst helper — it explains dashboard features, answers questions about a scan in progress, and can turn live scan data into a formatted investigation report.

### How It Works

1. Click the chat bubble in the bottom-right corner to open the assistant
2. While a scan is active, the current target's findings are automatically passed to the assistant as context
3. Ask questions directly, or click **Generate Report** to produce a structured SOC report
4. Any report-length reply shows a **Download as Word (.docx)** button underneath it

### Word (.docx) Report Export

- Markdown from the chatbot (headings, bullets, nested lists, tables, bold, inline code) is converted into real Word formatting
- Each export includes a cover page with the TRINETRA title, target, report date, and classification-style footer
- Powered by `python-docx` on the backend (`POST /api/report/docx`)

<br/>

---

## 🗺️ Interactive Map

### Map Architecture

```
IndiaMap (React Component)
├── MapContainer (Leaflet)
│   ├── TileLayer (CartoDB dark basemap)
│   ├── MapController (programmatic center/zoom)
│   ├── AnimatedAttackOverlay (SVG lines + traveling dots)
│   ├── CrimeHeatmap (GeoJSON state boundaries + NCRB)
│   ├── CityMarkers (10 major Indian cities, NCRB-risk)
│   └── DestinationPins (aggregated attack targets)
├── AttackCounter (live badge: critical/medium count)
├── AttackInfoPanel (severity bars, origin intel, table)
├── VectorDetailModal (full IP intel + report actions)
├── DataSourcesPanel (feed health status)
├── Map Controls (show/hide attacks, crime, data sources)
└── Legend (threat levels, data source colors)
```

### Animation System

Attack vectors are rendered as an **SVG overlay** using Leaflet's `L.svgOverlay`:

- **Dashed lines** from origin country coordinates to Indian city coordinates
- **Traveling dots** moving along the line with easing (ease-in-out quadratic)
- **Glow filter** (SVG `feGaussianBlur`) for visual emphasis
- **10 FPS throttle** to optimize performance
- **Pauses animation when tab is hidden** (visibility API)
- **Shallow comparison** on vector IDs to avoid unnecessary SVG rebuilds

### City Risk Markers

10 major Indian cities plotted with NCRB 2022 cyber crime statistics:

- **Color-coded circles**: Safe (green), Medium (yellow), Critical (red)
- **Pulsing animation** for critical destinations
- **Radius proportional** to risk level (7/10/14px)

<br/>

---

## 🔐 Authentication & User System

TRINETRA uses a **username/password registration system** with mandatory email verification and session tokens backed by a dedicated SQLite database.

### Registration Flow (Email OTP Verification)

Accounts are **not** created immediately on registration — the flow is 3 steps:

1. **`POST /api/auth/register`** — user submits username, email, password. The backend validates the email (format + disposable-domain blocklist + a live DNS MX-record check to reject fake/non-existent domains), hashes the password, and emails a 6-digit OTP code. **No account exists yet at this point.**
2. **`POST /api/auth/register/verify-otp`** — user submits the code. On success, the real account is created and a session token is returned (auto-login) — the first account ever created on an installation becomes admin.
3. **`POST /api/auth/register/resend-otp`** — if the code expires or doesn't arrive, request a new one (rate-limited, see below).

If SMTP isn't configured in `.env`, the OTP is printed to the backend console/terminal instead of emailed, so registration still works end-to-end for local development.

### Security Features

| Feature | Status | Details |
|---------|--------|---------|
| **Password Hashing** | ✅ bcrypt | GPU-resistant |
| **Email Verification** | ✅ Mandatory OTP | 6-digit code, 10-minute expiry, 5 wrong-attempt limit |
| **Disposable Email Blocking** | ✅ Enabled | Blocklist of known throwaway-email domains (mailinator, guerrillamail, etc.) |
| **Email Deliverability Check** | ✅ DNS MX lookup | Rejects domains that structurally cannot receive mail |
| **OTP Spam Protection** | ✅ Rate-limited | 60s resend cooldown + max 5 sends per email per hour |
| **Session Storage** | ✅ Database-backed | Survives server restarts |
| **Account Lockout** | ✅ 5 failed attempts | 15-minute lockout window |
| **Password Strength** | ✅ Enforced | 8+ chars, uppercase, lowercase, digit, special char |
| **Password History** | ✅ Last 5 passwords | Prevents reuse of recent passwords, checked both per-account and platform-wide |
| **Generic Error Messages** | ✅ Enabled | Prevents username/email enumeration |
| **Rate Limiting** | ✅ Per-IP sliding window | 10/min search, tighter limits specifically on register/OTP endpoints (see below), 60/min general |
| **Input Validation** | ✅ Strict regex | Rejects control chars, shell metacharacters |

### API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/auth/status` | Check if auth is enabled, registration is open, and payments are configured | ❌ Public |
| `POST` | `/api/auth/register` | Start registration — validates input, emails a 6-digit OTP `{username, email, password}` | ❌ Public |
| `POST` | `/api/auth/register/verify-otp` | Confirm the OTP and create the account (auto-login) `{email, otp}` | ❌ Public |
| `POST` | `/api/auth/register/resend-otp` | Resend a verification code `{email}` | ❌ Public |
| `POST` | `/api/auth/login` | Log in with credentials `{username, password}` | ❌ Public |
| `POST` | `/api/auth/verify` | Check if a session token is still valid `{token}` | ❌ Public |
| `POST` | `/api/auth/logout` | Invalidate the current session token | ✅ Required |
| `POST` | `/api/auth/change-password` | Change password `{current_password, new_password}` | ✅ Required |

### Authentication Methods

Once logged in, all protected API endpoints require the session token via:

```
X-API-Key: <your_session_token>
# or
Authorization: Bearer <your_session_token>
# or (WebSocket only)
?api_key=<your_session_token>  (as query parameter)
```

<br/>

---

## 💳 Credits & Payments

TRINETRA uses a **flat credit system** to recover infrastructure costs and monetize the platform. Every OSINT search costs exactly **10 credits** — regardless of how many plugins match the target.

### Billing Rules

| Rule | Value |
|------|-------|
| **Cost per search** | Flat **10 credits** (any target type, any plugin mix) |
| **New account** | Starts with **0 credits** — must purchase a plan before searching |
| **Deduction timing** | Deducted **before** the scan runs |
| **Refund** | Full 10 credits refunded **only if the entire scan fails or returns zero successful results** |
| **Partial failures** | Still charged full 10 credits |
| **Payment gateway** | [Cashfree](https://cashfree.com/) (sandbox for testing, production for live) |

### Credit Packs

| Plan | Price | Credits | ≈ Searches |
|------|-------|---------|------------|
| **Starter** | ₹99 | 10 | 1 |
| **Pro** | ₹499 | 100 | 10 |
| **Elite** | ₹1,499 | 500 | 50 |

### Payment Flow

1. User picks a plan on the **Payment Page** → frontend calls `POST /api/payment/create-order`
2. Backend creates a Cashfree order and returns a `payment_session_id`
3. Cashfree checkout opens (`_self` redirect); after payment, Cashfree redirects back with `?order_id=`
4. Frontend verifies via `POST /api/payment/verify` (fast polling) → credits are added idempotently
5. A signature-verified **webhook** (`POST /api/payment/webhook`) confirms server-side as well
6. Credits appear in the **credits badge** (top bar) and the dashboard unlocks

> **Sandbox testing:** With `CASHFREE_ENV=sandbox`, use card `4111 1111 1111 1111`, any future expiry (e.g. `12/25`), CVV `123`, and any name.
>
> **Webhook in local dev:** `localhost` webhook URLs can't be reached by Cashfree's servers, so the frontend's `/verify` polling is the credit-adding path in dev. Set `CASHFREE_WEBHOOK_URL` to a publicly reachable URL for production.

### Credits Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/payment/plans` | List available credit packs | ❌ Public |
| `POST` | `/api/payment/create-order` | Create a Cashfree order `{plan_id}` | ✅ Required |
| `POST` | `/api/payment/verify` | Verify an order + credit the account `{order_id}` | ✅ Required |
| `GET` | `/api/payment/credits` | Get the current credit balance | ✅ Required |
| `GET` | `/api/payment/history` | Payment history | ✅ Required |
| `POST` | `/api/payment/webhook` | Cashfree webhook (signature-verified) | ❌ Public |

### Search Credit Billing

Both the REST (`POST/GET /api/search`) and WebSocket (`/ws/search`) search paths deduct **10 credits** upfront and refund the full amount only when the scan returns zero successful results (or crashes/disconnects). When payments are enabled, a `credits_summary` message with `credits_used`, `credits_refunded`, and `credits_remaining` is sent after each WebSocket scan.

<br/>

---

## 📡 Real Data Sources

All data in TRINETRA is **real** — no simulated or placeholder data. See the table below for transparency on which data is real vs. statistically modeled.

### Threat Intelligence Feeds

| Source | Type | Data Provided | Key Required? |
|--------|------|---------------|---------------|
| [Abuse.ch ThreatFox](https://threatfox.abuse.ch/) | Malware IOCs | Malicious IPs, malware families, attack types | ❌ Free |
| [Feodo Tracker](https://feodotracker.abuse.ch/) | C2 Tracker | C2 server IPs, botnet malware (Dridex, Emotet, QakBot) | ❌ Free |
| [IPsum](https://github.com/stamparm/ipsum) | IP Blacklist | Blacklisted IPs with detection scores (1-7) | ❌ Free |
| [ip-api.com](https://ip-api.com/) | Geo-location | Country, city, lat/lon, ISP, org | ❌ Free (45 req/min) |

### OSINT Plugins Data Sources

| Plugin | Source(s) | Key Required? |
|--------|-----------|---------------|
| Domain Record | WHOIS servers (direct TCP on port 43) | ❌ Free |
| Name Servers | dnspython (direct DNS resolution) | ❌ Free |
| Port Scanner | Built-in async TCP scanner (24 common ports) | ❌ Free |
| SSL Health | OpenSSL via socket (certificate chain, cipher, protocols) | ❌ Free |
| Subdomain Finder | crt.sh + HackerTarget API + DNS brute-force (185+ prefixes) | ❌ Free |
| Geo Locator | ip-api.com | ❌ Free |
| HTTP Headers | httpx (security headers analysis) | ❌ Free |
| Tech Fingerprint | httpx (server header, x-powered-by, cookie analysis) | ❌ Free |
| CVE Alerts | NVD API v2.0 | ❌ Free |
| Data Leaks | XposedOrNot + LeakCheck + LeakIX + curated breach DB (70+ India-specific) | ❌ Free |
| Document Vault | httpx (12 common sensitive paths checked) | ❌ Free |
| OSINT Leak | leakosintapi.com | 🔑 API Key |
| Deep Search | Google dork query generation | ❌ Free |
| Live Feed | RSS (The Hacker News) via feedparser | ❌ Free |
| Surface Scan | Built-in async port scanner + risk analyzer | ❌ Free |

### RSS News Feeds

| Feed | Topic | Icon |
|------|-------|------|
| [The Hacker News](https://thehackernews.com/) | General cybersecurity | 📰 |
| [BleepingComputer](https://www.bleepingcomputer.com/) | Tech news + malware | 💻 |
| [KrebsOnSecurity](https://krebsonsecurity.com/) | In-depth security reporting | 🔒 |
| [The Record](https://therecord.media/) | Cyber crime + policy | 📝 |

### India-Specific Data

- **NCRB 2022** — Official cyber crime statistics for 23 Indian states/UTs
- **70+ curated India-specific data breaches** (Aadhaar, IRCTC, BigBasket, CoWIN, Truecaller, Jio, Paytm, etc.)
- **India GeoJSON** — State boundaries for all states/UTs
- **City targeting** — 10 major Indian cities with NCRB-weighted attack distribution

<br/>

---

## ✨ Features

### 🔍 OSINT Search (15 Plugins)

| Category | Plugins | What They Find |
|----------|---------|----------------|
| **Infrastructure** | WHOIS, DNS Lookup, Port Scanner, SSL Health, Subdomain Finder, Geo Locator, HTTP Headers, Tech Fingerprint | Registrar info, A/MX/NS records, open ports, certificate validity, subdomains, geo-location, security headers, tech stack |
| **Threat Intel** | CVE Alerts, Data Leaks, Document Vault, OSINT Leak | Known vulnerabilities (NVD), breach data (LeakIX, XposedOrNot, LeakCheck, curated DB), exposed documents, deep leak search |
| **Advanced** | Deep Search, Live Feed, Surface Scan | Google dork queries, risk scoring, real-time cyber news |

### 🗺️ Interactive India Threat Map

- Animated attack vectors with traveling dots from 25+ origin countries
- City risk markers based on NCRB 2022 cyber crime statistics
- Crime heatmap overlay with hover tooltips
- Threat intelligence panel with severity distribution (bars + numerical)
- Origin Intelligence Summary — country-level grouping of attack sources
- Vector detail modal with full IP intelligence and data source annotations
- Connection status bar showing live/real-time badge
- Data Sources Health Panel — live status of ThreatFox, Feodo, IPsum, and ip-api.com
- 10 FPS optimized animation (pauses when tab is hidden)
- SVG glow filter effects for critical threats
- Data source legend (color-coded by feed)

### 📡 Real-Time Threat Feed

- Live events timeline — filterable by All, Attacks, Events, or News
- Attack vector cards color-coded by severity with real malware family names
- Cyber news from 4 RSS feeds with source attribution
- Vector detail modal with full IP intelligence
- Stats dashboard: Critical count, Medium count, Total Vectors, Total Events
- Connection status indicator with auto-reconnect (exponential backoff)
- Empty states with contextual messages

### 📊 Report & Graph Views

- **Report View** — Three modes: GUI (structured table), Terminal (raw output), Split (both)
- **Full Report** — Executive summary, threat landscape, watches & alerts, intelligence events
- **Relationship Graph** — Dynamic Cytoscape visualization with color-coded nodes (target, IP, DNS, geo, port, CVE, email, domain)
- **Export** — Save graphs to PNG, copy to clipboard, or export chatbot reports as Word (.docx)

### 🤖 AI Chatbot Assistant

- Google Gemini-powered in-app SOC analyst assistant
- Context-aware — automatically sees the current scan's findings
- One-click **Generate Report** for a structured investigation summary
- **Download as Word (.docx)** — formatted, cover-paged report ready to share
- System instruction restricts to OSINT domain knowledge

### 👁️ Watch & Monitoring

- Automated re-scanning from 60 seconds to 7 days
- Smart change detection with human-readable diffs
- Alert history with full timeline
- Plugin-level control per watch
- Pause/resume without data loss
- Retry logic with exponential backoff for DB lock contention

### 🔐 User Authentication

- Dedicated React Sign Up / Login UI with real-time validation (lucide-react icons)
- Username/password registration and login
- First user becomes admin
- Session tokens stored in localStorage with backend verification on reload
- All API endpoints require authentication
- Dedicated SQLite auth database (works with both SQLite and PostgreSQL modes)
- bcrypt password hashing with 12 rounds
- Account lockout after 5 failed login attempts
- Password history prevents reuse of last 5 passwords
- Password change endpoint

### 🐳 Docker Deployment

- Fully containerized: PostgreSQL 15, Redis 7, FastAPI, React/Nginx
- Docker Compose with health checks and dependency ordering (depends_on with conditions)
- Dev mode with hot-reload via bind mounts (docker-compose.override.yml)
- TaskIQ worker for background watch tasks
- Non-root container security (all services run as unprivileged users)
- Resource limits (CPU/memory) for all containers
- Security options: `no-new-privileges`, `cap_drop: ALL`, read-only root FS where possible

### 🛡️ India-Specific Intelligence

- NCRB 2022 cyber crime data for 23 states/UTs
- 70+ curated India-specific data breaches
- India GeoJSON map with state boundaries
- CERT-In incident reporting
- Indian second-level TLD support (.ac.in, .edu.in, .gov.in, .co.in, etc.)
- Indian city coordinate data with NCRB-weighted risk distribution

### 💻 User Interface & UX

- Dark-themed design with CSS custom properties
- Animated landing page with feature showcase
- Command palette (Cmd/Ctrl+K) for quick navigation
- Toast notifications (auto-dismiss after 3.5s, max 5 visible)
- Shimmer skeleton loading states
- Scan progress indicator with live plugin completion count
- Sidebar with plugin status and categorization
- Empty and error states for every view
- Data source health monitoring panel
- Auto-detect search type (domain/IP/email/phone/name)

<br/>

---

## 📡 API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/auth/status` | Check auth status, registration open, payments configured | ❌ Public |
| `POST` | `/api/auth/register` | Start registration — emails a 6-digit OTP `{username, email, password}` | ❌ Public |
| `POST` | `/api/auth/register/verify-otp` | Confirm OTP → creates account + session token `{email, otp}` | ❌ Public |
| `POST` | `/api/auth/register/resend-otp` | Resend the verification code `{email}` | ❌ Public |
| `POST` | `/api/auth/login` | Log in `{username, password}` → session token | ❌ Public |
| `POST` | `/api/auth/verify` | Verify session token `{token}` | ❌ Public |
| `POST` | `/api/auth/logout` | Invalidate session token | ✅ Required |
| `POST` | `/api/auth/change-password` | Change password `{current_password, new_password}` | ✅ Required |

### OSINT Search Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `POST` | `/api/search` | Run OSINT scan on a target | 10/min |
| `GET` | `/api/search/{target}` | GET variant of search | 10/min |
| `GET` | `/api/detect?target=` | Auto-detect target type | 60/min |
| `GET` | `/api/plugins` | List all 15 OSINT plugins | 60/min |
| `GET` | `/api/target-intel?target=` | Fetch web intelligence (DuckDuckGo + news) | 60/min |

### Payment & Credits Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/payment/plans` | List available credit packs | ❌ Public |
| `POST` | `/api/payment/create-order` | Create a Cashfree order `{plan_id}` | ✅ Required |
| `POST` | `/api/payment/verify` | Verify an order + credit the account `{order_id}` | ✅ Required |
| `GET` | `/api/payment/credits` | Get the current credit balance | ✅ Required |
| `GET` | `/api/payment/history` | Payment history | ✅ Required |
| `POST` | `/api/payment/webhook` | Cashfree webhook (signature-verified) | ❌ Public |

### Chatbot & Report Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/chat` | Send a message to the AI assistant `{message, history, context}` | ✅ Required |
| `POST` | `/api/report/docx` | Convert a markdown report into a Word `.docx` file `{target, markdown}` | ✅ Required |

### Watch Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watches` | List all watches |
| `POST` | `/api/watches` | Create a watch |
| `GET` | `/api/watches/{id}` | Get watch details |
| `DELETE` | `/api/watches/{id}` | Delete a watch |
| `POST` | `/api/watches/{id}/toggle` | Pause/resume a watch |
| `GET` | `/api/watches/alerts` | Recent alerts (configurable limit) |
| `GET` | `/api/watches/{id}/alerts` | Alerts for a specific watch |

### Data Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/crime-data` | NCRB 2022 cyber crime data | ❌ Public |
| `GET` | `/api/health/sources` | Data source health status | ❌ Public |
| `GET` | `/health` | Backend health + plugin counts | ❌ Public |
| `GET` | `/` | Root endpoint with API overview | ❌ Public |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/search` | Streaming OSINT search results |
| `/ws/threats` | Live threat feed for map |

### WebSocket Protocols

#### `/ws/search` Protocol

```
Client → Server:  {"target": "example.com", "type": "domain"}
Server → Client:  {"type": "start", "total": N, "plugins": [...]}
Server → Client:  {"type": "result", "result": {...}, "completed": X, "total": N}  × N times
Server → Client:  {"type": "complete", "total": N, "completed": N}
Server → Client:  {"type": "credits_summary", "credits_used": 10, "credits_refunded": M, "credits_remaining": R}  (when payments enabled)
```

#### `/ws/threats` Protocol

```
Server → Client:  {"type": "initial_state", "events": [...], "cities": [...], "timestamp": "..."}
Server → Client:  {"type": "attack_vector", "id": "...", "from": "China", ...}
Server → Client:  {"type": "news_event", "id": "...", "text": "...", ...}
Client → Server:  {"action": "pause"} | {"action": "resume"} | {"action": "stop"}
```

### API Examples

> **Note:** All examples use port **8000** — both Docker and manual mode (the Vite dev proxy targets `localhost:8000`).

**Register a user (starts OTP verification):**
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "SecurePass123!"}'
```

**Verify the OTP (creates the account + logs in):**
```bash
curl -X POST http://localhost:8000/api/auth/register/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "otp": "123456"}'
```
*(Check the backend terminal/logs for the code if `SMTP_HOST` isn't configured — it prints there instead of being emailed.)*

**Login (after the account is verified):**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SecurePass123!"}'
```

**Run a search (with auth token):**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_session_token>" \
  -d '{"target": "example.com"}'
```

**List plugins:**
```bash
curl -H "X-API-Key: <token>" http://localhost:8000/api/plugins
```

**Change password:**
```bash
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <token>" \
  -d '{"current_password": "oldpass", "new_password": "NewSecurePass123!"}'
```

<br/>

---

## 🗂️ Project Structure

```
trinetra/
├── backend/
│   ├── app/
│   │   ├── api/                        # REST + WebSocket routes
│   │   │   ├── routes.py               # Auth (login/register), search, detect, plugins, target-intel
│   │   │   ├── websocket_routes.py     # /ws/search streaming scan results
│   │   │   ├── threat_routes.py        # /ws/threats live feed for map
│   │   │   ├── watch_routes.py         # Watch CRUD + alert endpoints
│   │   │   ├── chat_routes.py          # AI chatbot (/api/chat)
│   │   │   ├── report_routes.py        # Word (.docx) report export (/api/report/docx)
│   │   │   ├── payment_routes.py       # Cashfree payment + credits endpoints
│   │   │   └── data_routes.py          # NCRB crime data, source health
│   │   ├── core/                       # App core modules
│   │   │   ├── config.py               # Settings via pydantic-settings + .env
│   │   │   ├── detector.py             # Auto-detect target type (domain/IP/email/phone/name)
│   │   │   ├── sanitizer.py            # Input validation & sanitization
│   │   │   ├── rate_limiter.py         # In-memory sliding window rate limiter
│   │   │   ├── email_otp.py            # Signup OTP: pending-signup storage, disposable/MX email checks
│   │   │   └── api_key_auth.py         # User auth (register, login, tokens, credits, dedicated SQLite DB)
│   │   ├── templates/                  # Jinja2 HTML email templates (otp, welcome, account_verified, forgot_password)
│   │   ├── data/
│   │   │   └── ncrb_crime_data.py      # NCRB 2022 cyber crime statistics (23 states)
│   │   ├── models/
│   │   │   └── schemas.py              # Pydantic request/response models
│   │   ├── plugins/                    # 15 OSINT plugins (auto-discovered)
│   │   │   ├── base.py                 # Abstract base class (OSINTPlugin) + PluginResult
│   │   │   ├── registry.py             # Auto-discovery plugin registry (singleton)
│   │   │   ├── infrastructure/         # 8 plugins
│   │   │   │   ├── domain_record.py    # WHOIS registration lookup
│   │   │   │   ├── name_servers.py     # DNS record resolution (A, MX, NS, TXT, etc.)
│   │   │   │   ├── port_scanner.py     # TCP port scanner (24 ports)
│   │   │   │   ├── ssl_health.py       # SSL certificate validation
│   │   │   │   ├── subdomain_finder.py # Subdomain discovery (crt.sh, HackerTarget, DNS brute-force)
│   │   │   │   ├── geo_locator.py      # IP geo-location (ip-api.com)
│   │   │   │   ├── http_headers.py     # HTTP security headers analysis
│   │   │   │   └── tech_fingerprint.py # Web server/framework detection
│   │   │   ├── threat/                 # 4 plugins
│   │   │   │   ├── cve_alerts.py       # NVD vulnerability lookup
│   │   │   │   ├── data_leaks.py       # Breach database search (3 APIs + curated DB)
│   │   │   │   ├── document_vault.py   # Exposed document scanner
│   │   │   │   └── osint_leak.py       # Deep breach search via Leakosint API
│   │   │   └── advanced/               # 3 plugins
│   │   │       ├── deep_search.py      # Google dork query generation
│   │   │       ├── live_feed.py        # RSS news feed
│   │   │       └── surface_scan.py     # Risk score + attack surface analysis
│   │   ├── services/
│   │   │   ├── orchestrator.py         # Plugin orchestrator (parallel execution)
│   │   │   ├── threat_feed.py          # Live threat feed broadcaster
│   │   │   ├── real_threat_service.py  # Real malicious IP fetcher (ThreatFox, Feodo, IPsum)
│   │   │   ├── real_news_service.py    # Real RSS news fetcher (4 feeds)
│   │   │   ├── watch_service.py        # Watch CRUD + alert service
│   │   │   ├── chat_service.py         # Gemini AI chatbot service
│   │   │   ├── docx_report_service.py  # Markdown → Word (.docx) report generator
│   │   │   ├── email_service.py        # SMTP transport + Jinja2 template rendering (OTP emails)
│   │   │   ├── payment_service.py      # Cashfree orders, verification, webhooks, flat pricing
│   │   │   ├── database.py             # Async SQLAlchemy (SQLite/PostgreSQL, dual SQL sets)
│   │   │   └── telegram_bot.py         # Telegram OSINT bot (optional)
│   │   ├── tasks/
│   │   │   ├── broker.py               # TaskIQ broker (Redis-backed or in-memory)
│   │   │   ├── scheduler.py            # Watch scheduler (60s polling loop)
│   │   │   └── watch_tasks.py          # Watch scan + change detection + alert creation
│   │   └── main.py                     # FastAPI app factory + lifespan
│   ├── tests/
│   │   ├── conftest.py                 # Test fixtures (in-memory SQLite DB)
│   │   ├── test_api_key_auth.py        # Auth unit tests (bcrypt, sessions, lockout)
│   │   ├── test_data_leaks.py          # Data leak plugin tests (mocked APIs)
│   │   ├── test_plugins.py             # Plugin system tests (base, registry, orchestrator)
│   │   ├── test_watch_alerts.py        # Alert detection/parsing tests
│   │   ├── test_watch_retry.py         # Watch retry logic tests
│   │   ├── test_watch_routes.py        # Watch API route tests
│   │   └── test_watch_service.py       # Watch service tests
│   ├── Dockerfile                      # Multi-stage Python 3.11 build
│   ├── init.sql                        # PostgreSQL initial schema
│   └── requirements.txt                # Python dependencies (16 packages)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage/              # React Sign Up / Login UI with real-time validation
│   │   │   ├── LandingPage/            # Pre-search landing/welcome screen
│   │   │   ├── PaymentPage/            # Plan selection + Cashfree checkout + success state
│   │   │   ├── CreditsBadge/           # Top-bar credit balance badge + buy button
│   │   │   ├── ChatBot/                # AI chatbot assistant + Word (.docx) report export
│   │   │   ├── Map/IndiaMap.tsx        # Interactive India threat map (Leaflet)
│   │   │   ├── LiveFeed/               # Real-time threat feed page
│   │   │   ├── SearchBar/              # Auto-detect search input bar
│   │   │   ├── CommandPalette/         # Cmd/Ctrl+K quick command palette
│   │   │   ├── ReportView/             # Plugin detail report (GUI/Terminal/Split modes)
│   │   │   ├── FullReportView/         # Full system intelligence report
│   │   │   ├── GraphView/              # Cytoscape relationship graph visualization
│   │   │   ├── VectorDetailModal/      # Attack vector detail modal
│   │   │   ├── WatchPanel/             # Watch CRUD management interface
│   │   │   ├── Sidebar/                # Plugin status sidebar
│   │   │   ├── DataSourcesPanel/       # Data source health panel
│   │   │   ├── DashboardStats/         # Stats bar (during/after scan)
│   │   │   ├── ScanProgress/           # Scan progress indicator
│   │   │   ├── EmptyState/             # No-results placeholder
│   │   │   ├── ErrorState/             # Error placeholder
│   │   │   ├── Skeleton/               # Shimmer loading skeleton
│   │   │   ├── ToastNotification/      # Toast notifications
│   │   │   └── Icons/                  # Shared icon set
│   │   ├── store/
│   │   │   ├── AppContext.tsx           # Global app state (search, results, toasts, tabs)
│   │   │   ├── AuthContext.tsx          # Auth state + login/register/logout
│   │   │   └── ThreatContext.tsx        # Live threat feed state (WebSocket)
│   │   ├── types/index.ts               # TypeScript type definitions
│   │   ├── utils/
│   │   │   ├── api.ts                   # REST API client with auth headers
│   │   │   ├── detectSearchType.ts      # Client-side type detection
│   │   │   ├── useWebSocket.ts          # WebSocket scan hook
│   │   │   ├── useThreatFeed.ts         # WebSocket threat feed hook (auto-reconnect)
│   │   │   ├── wsUtils.ts              # WebSocket URL builder
│   │   │   ├── pluginMapper.ts          # API response → frontend types
│   │   │   └── indiaStatesGeoJSON.ts    # India GeoJSON boundaries
│   │   ├── App.tsx                      # Root app component (landing, auth gate, dashboard)
│   │   ├── main.tsx                     # React entry point with context providers
│   │   └── styles.css                   # Complete dark-themed design system
│   ├── Dockerfile                       # Multi-stage Node → Nginx build
│   ├── nginx.conf                       # Nginx reverse proxy config
│   └── package.json
├── docker-compose.yml                   # Production compose (PostgreSQL, Redis, Backend, Worker, Frontend)
├── docker-compose.override.yml          # Dev overrides (hot-reload bind mounts)
├── .env.example                         # Environment variable template
└── README.md                            # This file
```

<br/>

---

## ⚙️ Configuration Reference

### Global Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `TRINETRA OSINT API` | Application display name |
| `DEBUG` | `false` | Enable debug mode |
| `DATABASE_URL` | `sqlite+aiosqlite:///./trinetra.db` | Database connection string |
| `AUTH_DB_PATH` | `trinetra_auth.db` | Path to dedicated SQLite auth database (auto-created) |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins |
| `FRONTEND_URL` | `http://localhost:3000` | Base URL used to build links inside emails (e.g. password reset) |
| `PLUGIN_TIMEOUT` | `30` | Per-plugin timeout in seconds |
| `HIBP_API_KEY` | `""` | Have I Been Pwned API key |
| `TELEGRAM_BOT_TOKEN` | `""` | Telegram Bot token |
| `TELEGRAM_OSINT_API_URL` | `""` | OSINT Leak API base URL |
| `TELEGRAM_OSINT_API_KEY` | `""` | API key for OSINT API |
| `GEMINI_API_KEY` | `""` | Google Gemini API key (enables AI chatbot & report generation) |
| `GEMINI_MODEL` | `gemini-flash-latest` | Gemini model used for chatbot replies |
| `SMTP_HOST` | `""` | SMTP server hostname (empty = OTP codes print to console instead of emailing) |
| `SMTP_PORT` | `587` | SMTP port — 587 for STARTTLS, 465 for implicit SSL |
| `SMTP_USERNAME` | `""` | SMTP auth username (usually your full email address) |
| `SMTP_PASSWORD` | `""` | SMTP auth password / app password / API key |
| `SMTP_USE_TLS` | `true` | Use STARTTLS (port 587) — set only one of TLS/SSL to true |
| `SMTP_USE_SSL` | `false` | Use implicit SSL (port 465) |
| `SMTP_FROM_EMAIL` | `""` | "From" address shown to recipients (defaults to `SMTP_USERNAME` if empty) |
| `SMTP_FROM_NAME` | `TRINETRA` | "From" display name on outgoing emails |
| `OTP_LENGTH` | `6` | Number of digits in the OTP code |
| `OTP_EXPIRY_MINUTES` | `10` | How long an OTP code stays valid |
| `OTP_MAX_ATTEMPTS` | `5` | Wrong-code attempts before the OTP is invalidated |
| `OTP_RESEND_COOLDOWN_SECONDS` | `60` | Minimum wait between resend requests |
| `OTP_MAX_REQUESTS_PER_HOUR` | `5` | Max OTP sends per email address per hour (anti-spam) |
| `BLOCK_DISPOSABLE_EMAILS` | `true` | Reject known throwaway-email domains (mailinator, guerrillamail, etc.) |
| `VERIFY_EMAIL_MX` | `true` | Reject domains with no valid mail server (DNS MX lookup) |
| `CASHFREE_APP_ID` | `""` | Cashfree app ID (empty = payments disabled, free mode) |
| `CASHFREE_SECRET_KEY` | `""` | Cashfree secret key (empty = payments disabled, free mode) |
| `CASHFREE_ENV` | `sandbox` | `sandbox` for testing, `production` for live payments |
| `CASHFREE_WEBHOOK_URL` | `http://localhost:8000/api/payment/webhook` | Public webhook URL Cashfree posts payment events to |
| `REDIS_URL` | `""` | Redis URL for TaskIQ broker (empty = inline execution) |
| `TRUST_PROXY_HEADERS` | `true` in `.env.example` (code default is `false`) | Set true only when behind a known reverse proxy (Docker mode ships this on since Nginx fronts the backend) |
| `CACHE_TTL_DEFAULT` | `3600` | Default cache TTL in seconds |
| `CACHE_TTL_LONG` | `86400` | Long cache TTL in seconds (24 hours) |

### Database Backend Selection

| URL Pattern | Backend | Best For |
|-------------|---------|----------|
| `sqlite+aiosqlite:///./trinetra.db` | SQLite | Development, single-user |
| `postgresql+asyncpg://user:pass@host:5432/db` | PostgreSQL | Docker, production, multi-user |

> **Note:** User authentication always uses a dedicated SQLite database (`trinetra_auth.db`) regardless of the main `DATABASE_URL` setting. This means auth works seamlessly in both SQLite and PostgreSQL modes.

<br/>

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_plugins.py -v

# Run with coverage
python -m pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests once
npm run test:run

# Run with coverage
npm run test:coverage
```

### Test Coverage

| Test File | What It Tests |
|-----------|---------------|
| `test_api_key_auth.py` | bcrypt hashing, DB sessions, account lockout, password validation |
| `test_data_leaks.py` | Data leak plugin with mocked APIs (XposedOrNot, LeakCheck, LeakIX) |
| `test_plugins.py` | PluginResult, OSINTPlugin base, Registry, Orchestrator, AutoDetect, Sanitizer |
| `test_watch_alerts.py` | Alert diff parsing, JSON field parsing, plugin ID parsing |
| `test_watch_retry.py` | Watch scan retry logic, DB lock handling, change detection |
| `test_watch_routes.py` | Watch API route CRUD operations |
| `test_watch_service.py` | Watch service create/list/get/delete/toggle operations |

<br/>

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

- **Report bugs** — Open an issue with reproduction steps
- **Suggest features** — Open an issue with your idea
- **Add plugins** — New OSINT plugins welcome! See the base class below
- **Improve the map** — Better visualizations, new overlays, performance optimizations
- **Add tests** — Increase coverage, especially integration and E2E tests

### How to Add a New Plugin

1. Create a new `.py` file in the appropriate category directory under `backend/app/plugins/`
2. Subclass `OSINTPlugin` and implement the `run()` method
3. Set `plugin_id`, `name`, `category`, `description`, `input_types`
4. The plugin is **auto-discovered** — no registration needed

```python
from app.plugins.base import OSINTPlugin, PluginResult

class MyNewPlugin(OSINTPlugin):
    plugin_id = "my-plugin"
    name = "My Plugin"
    category = "threat"  # infrastructure, threat, advanced
    description = "What this plugin finds"
    input_types = ["domain", "ip"]

    async def run(self, target: str) -> PluginResult:
        # Your OSINT logic here
        return PluginResult(
            plugin_id=self.plugin_id,
            plugin_name=self.name,
            category=self.category,
            target=target,
            gui_data={"key": "value"},
            terminal_data="key: value",
        )
```

### Development Workflow

```bash
# Clone the repo
git clone https://github.com/your-username/INDRA.git
cd INDRA

# Docker (recommended for development)
docker compose -p indra2 up -d          # Full stack with hot-reload
docker compose -p indra2 logs -f backend  # Watch backend logs

# Or manual (no Docker)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npx vite --host 0.0.0.0 --port 3000
```

### Coding Standards

- **Python**: Follow PEP 8, use type hints, write docstrings for all public functions
- **TypeScript**: Follow the existing patterns, use strict types, avoid `any`
- **Tests**: Write tests for new plugins and services, mock external APIs
- **Plugins**: Handle errors gracefully in `run_safe()` wrapper, provide both `gui_data` and `terminal_data`

<br/>

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

<br/>

---

<div align="center">
  <p>
    <b>Built with 🛡️ for India's cybersecurity community</b>
  </p>
  <p>
    <sub>TRINETRA — Open Source Intelligence for a safer digital India</sub>
  </p>
  <br/>
  <p>
    <a href="https://github.com/your-username/INDRA/issues">Report Bug</a> ·
    <a href="https://github.com/your-username/INDRA/issues">Request Feature</a> ·
    <a href="https://github.com/your-username/INDRA">GitHub</a>
  </p>
</div>
