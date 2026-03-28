# Renci 仁慈

**An AI-powered live agent that helps Manhattan Chinatown's mom-and-pop shops build their digital presence — through email, SMS, voice, and photo.**

> *"Focus on the user and all else will follow."* — Renci exists because Chinatown's business owners work 12-hour days. They don't have time to learn website builders. But they all have a phone.

[![Live Demo](https://img.shields.io/badge/Live-renci--web-red?style=for-the-badge)](https://renci-web-408375733910.us-central1.run.app)
[![API](https://img.shields.io/badge/API-renci--api-blue?style=for-the-badge)](https://renci-api-408375733910.us-central1.run.app/health)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://console.cloud.google.com/run?project=renci-491614)

---

## Team

| Role | Name | Contact |
|------|------|---------|
| **Lead** | David White Wolf | cdw8481@nyu.edu |
| **Team** | Blue Fire | |

---

## The Problem

```
-47%    Chinatown businesses lost since 2000
 73%    Have no website, no Google listing, no social media
  0     Affordable tools that speak their language
```

Manhattan's Chinatown is losing its small businesses. The ones that remain are invisible online — no website, no social media, no digital footprint. These owners speak Cantonese, Mandarin, and English. They don't have time or tech literacy to build a Squarespace site. But every single one of them has an email and a phone.

**Renci meets them where they are.**

---

## What Renci Does

Renci is a **live AI agent** — not a chatbot. Business owners message `mkarurosun@gmail.com` and Renci takes action:

```
OWNER emails: "Hi"

RENCI: Welcome to Renci! I help small businesses build their
       online presence for free.
       What is the name of your business?
       你的店叫什么名字？

OWNER: Wong's Bakery 黄记饼家

    ... 5 messages later ...

RENCI: You're all set! Your website is live:
       renci.app/wongs-bakery

       Text me anytime to update it!
       随时发短信给我来更新！
```

### Key Capabilities

| Capability | How It Works |
|-----------|-------------|
| **See** | Send a photo of your menu — Gemini Vision extracts items and prices |
| **Hear** | Message anytime in English or Chinese — Renci understands both |
| **Speak** | Bilingual responses (EN/ZH) with culturally-aware communication |
| **Act** | Updates your website, hours, contact info, and social media links in real-time |
| **Inform** | Access PPP loan data for your neighborhood — see how businesses like yours were supported |

### The Owner Experience

The business owner can **chime in anytime** with the live agent. There's no scheduling, no appointments, no wait times. Email Renci at 6 AM before opening or at 11 PM after closing — the agent responds immediately and executes the request.

**The purpose is to put business owners at ease.** They don't need to understand technology. They just need to tell Renci what they want in their own language, and it gets done.

```
OWNER: Update hours Mon-Sat 7am-6pm
RENCI: Hours updated! ✓

OWNER: 加个菜品：叉烧包 $2.50
RENCI: 菜单已更新！Added: 叉烧包 $2.50 ✓

OWNER: How much PPP funding did bakeries near me get?
RENCI: In zip 10013: 3 bakeries received PPP loans totaling
       $60,300. Average: $20,100. All 3 loans forgiven (100%).
```

---

## Demo

> **[Live Landing Page](https://renci-web-408375733910.us-central1.run.app)** — Interactive SMS demo, PPP data visualization, architecture diagram

<!-- Replace with actual demo gif URL -->
![Demo GIF](https://renci-web-408375733910.us-central1.run.app/demo.gif)

### Try It Now

Email `mkarurosun@gmail.com` with the message **"Hi"** — the live agent will walk you through registration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUSINESS OWNER                           │
│                   (Email / SMS / MMS Photo)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     COMMUNICATION LAYER                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Gmail IMAP   │  │ Twilio SMS   │  │ Webhook API           │  │
│  │ (Receiver)   │  │ (Receiver)   │  │ POST /webhooks/email  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         └─────────────────┼──────────────────────┘              │
│                           ▼                                      │
│                    ┌──────────────┐                              │
│                    │  SMS Router  │                              │
│                    └──────┬───────┘                              │
└───────────────────────────┼─────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│   REGISTRATION       │  │         GEMINI AGENT ENGINE           │
│   (6-Step Flow)      │  │                                       │
│                      │  │  Model: Gemini 2.5 Flash              │
│  1. Business Name    │  │  SDK:   Google GenAI                  │
│  2. Business Type    │  │  Mode:  Tool-Use (Function Calling)   │
│  3. Address          │  │                                       │
│  4. Confirm Address  │  │  ┌─────────────────────────────────┐  │
│  5. Email            │  │  │         9 CUSTOM TOOLS           │  │
│  6. → Website Live!  │  │  │                                  │  │
│                      │  │  │  Business:                       │  │
│  Bilingual prompts   │  │  │  ├─ update_business_hours        │  │
│  at every step       │  │  │  ├─ update_contact_info          │  │
│                      │  │  │  ├─ update_business_description  │  │
└──────────┬───────────┘  │  │  ├─ show_status                  │  │
           │              │  │  └─ show_help                    │  │
           │              │  │                                  │  │
           │              │  │  Civic Data (PPP Loans):         │  │
           │              │  │  ├─ lookup_ppp_data              │  │
           │              │  │  ├─ compare_ppp_by_industry      │  │
           │              │  │  └─ check_ppp_forgiveness        │  │
           │              │  │                                  │  │
           │              │  │  Multimodal:                     │  │
           │              │  │  └─ extract_menu_from_photo      │  │
           │              │  └─────────────────────────────────┘  │
           │              └──────────────┬───────────────────────┘
           │                             │
           ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  Firestore     │  │  Cloud Storage   │  │  PPP Loan CSV    │  │
│  │  (Businesses,  │  │  (Photos,        │  │  (SBA FOIA Data  │  │
│  │   Owners,      │  │   Assets)        │  │   filtered for   │  │
│  │   Sessions)    │  │                  │  │   10002, 10013)  │  │
│  └────────┬───────┘  └────────┬────────┘  └──────────────────┘  │
└───────────┼───────────────────┼─────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SvelteKit on Cloud Run                                  │    │
│  │                                                          │    │
│  │  /                    → Landing page (demo + PPP viz)    │    │
│  │  /wongs-bakery        → Generated business website       │    │
│  │  /dashboard           → Admin panel (future)             │    │
│  │                                                          │    │
│  │  Templates: Default, Restaurant, Bakery, Salon, Retail   │    │
│  │  Fonts: Inter + Noto Sans SC/TC (CJK support)           │    │
│  │  i18n: English, Simplified Chinese, Traditional Chinese  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI Model** | Gemini 2.5 Flash | Multimodal (text + vision), bilingual, fast tool-use |
| **AI SDK** | Google GenAI SDK | Direct Gemini API with automatic function calling |
| **Backend** | Python + FastAPI | Async, lightweight, Cloud Run native |
| **Frontend** | SvelteKit + Tailwind | SSR for SEO, reactive UI, small bundle |
| **Database** | Cloud Firestore | Serverless, document model fits business profiles |
| **Storage** | Cloud Storage | Photos and generated assets |
| **SMS** | Twilio + Gmail IMAP/SMTP | Dual channel — SMS and email as live agent |
| **Hosting** | Google Cloud Run (x2) | Scales to zero, auto-scaling, pay-per-use |
| **CI/CD** | Cloud Build | Source-based deploys from Dockerfile |
| **Dataset** | SBA PPP FOIA Data | Filtered for Chinatown zips 10002, 10013 |

### Agent Tool Architecture

```
Owner Message
     │
     ▼
┌─────────────┐
│  Language    │──→ Detects EN vs ZH using lead-character heuristic
│  Detector    │    (first substantive character determines language)
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌────────────────────┐
│  Gemini     │────→│  Tool Definitions  │
│  2.5 Flash  │     │  (9 functions with │
│             │←────│   typed signatures │
│  System     │     │   + docstrings)    │
│  Prompt     │     └────────────────────┘
│  (bilingual)│
└──────┬──────┘
       │
       ▼
  Tool Result → Formatted Response → Email/SMS Reply
```

---

## NYC Civic Dataset: PPP Loans

Renci integrates **SBA Paycheck Protection Program** loan data, filtered for Manhattan Chinatown (zip codes 10002 and 10013).

| Metric | Value |
|--------|-------|
| Businesses in dataset | 30 |
| Total PPP loans | $1.5M |
| Forgiveness rate | 97% |
| Jobs supported | 224 |
| Top industry | Full-Service Restaurants (8 loans, $841K) |

**Source:** [SBA PPP FOIA Data](https://data.sba.gov/dataset/ppp-foia)

Business owners can ask Renci about PPP data for their zip code and industry — making civic financial data accessible through simple conversation, not spreadsheets.

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 22+
- Google Cloud account with project created
- [Gemini API key](https://aistudio.google.com/apikey)
- Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled

### 1. Clone the Repository

```bash
git clone https://github.com/wolfwdavid/renci.git
cd renci
```

### 2. Configure Environment

```bash
cp .env.example apps/api/.env
```

Edit `apps/api/.env` with your credentials:

```env
GOOGLE_API_KEY=your_gemini_api_key
RENCI_EMAIL=your_gmail@gmail.com
RENCI_EMAIL_APP_PASSWORD=your_16_char_app_password
GCP_PROJECT_ID=your_project_id
```

### 3. Install & Run API

```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

### 4. Install & Run Web

```bash
cd apps/web
npm install
npm run dev
```

Visit: `http://localhost:5173`

### 5. Run Tests

```bash
cd apps/api
python -m pytest tests/ -v
```

Expected: **40 tests passing**

### 6. Deploy to Google Cloud Run

```bash
# Authenticate
gcloud auth login --project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com

# Deploy API
cd apps/api
gcloud run deploy renci-api --source . --region us-central1 --allow-unauthenticated --port 8080

# Deploy Web
cd apps/web
gcloud run deploy renci-web --source . --region us-central1 --allow-unauthenticated
```

---

## Project Structure

```
renci/
├── apps/
│   ├── api/                    # Python FastAPI backend
│   │   ├── agent/              # Gemini agent engine
│   │   │   ├── core.py         # Agent dispatcher (GenAI SDK)
│   │   │   ├── tools.py        # 9 tool functions
│   │   │   ├── actions/        # Business logic
│   │   │   │   ├── registration.py  # 6-step SMS flow
│   │   │   │   ├── profile.py       # Firestore updates
│   │   │   │   ├── ppp_data.py      # PPP dataset queries
│   │   │   │   └── photo.py         # Gemini Vision analysis
│   │   │   └── prompts/        # Bilingual system prompts
│   │   ├── email_channel/      # Gmail IMAP/SMTP handler
│   │   ├── sms/                # Twilio SMS handler
│   │   ├── db/                 # Firestore client
│   │   ├── language/           # CJK detection
│   │   ├── data/               # PPP loan dataset (CSV)
│   │   └── tests/              # 40 tests
│   │
│   └── web/                    # SvelteKit frontend
│       └── src/
│           ├── routes/
│           │   ├── +page.svelte        # Landing page + demo
│           │   └── [slug]/             # Dynamic business sites
│           └── lib/
│               ├── templates/          # Business site templates
│               └── i18n/               # EN + ZH-Hans + ZH-Hant
│
├── infra/                      # Terraform + Cloud Build
└── tasks/                      # Progress tracking
```

---

## Build for Everyone

Renci is named after the Chinese concept of **仁慈** (renci) — benevolence, kindness, compassion.

Chinatown's mom-and-pop shops have survived decades of change — immigration waves, economic downturns, a pandemic, rising rents. What they haven't survived is digital invisibility. A bakery that's been on Mott Street since 1985 doesn't show up when someone Googles "bakery near me."

Renci changes that. One message at a time.

---

**NYC Build With AI Hackathon 2026** | Deadline: 2:15 PM

*Built with Gemini 2.5 Flash on Google Cloud*
