# AI Personal Assistant 🤖

A production-grade, modular AI Personal Assistant built with **FastAPI**, **Python 3.13**, and **Clean Architecture**. Integrates with **Telegram**, **Google Calendar**, **OpenRouter LLM**, and supports long-term memory, RAG, tool calling, and multi-user capabilities.

> 📚 **Documentation:** [📘 System Overview & Diagrams](SYSTEM_OVERVIEW.md) · [🏗️ Architecture Deep Dive](ARCHITECTURE.md) · [🚀 Deployment Guide](DEPLOYMENT.md)


## 🖼️ Visual Overview

| System Overview | AI Personal Assistant |
|:---:|:---:|
| ![System Overview](docs/images/system-overview.jpg) | ![AI Personal Assistant](docs/images/ai-personal-assistant.jpg) |


---

## 📋 Project at a Glance (For Recruiters)

**AI Personal Assistant** is a production-ready AI chatbot that acts as a personal assistant on Telegram. Users talk to it in plain natural language, and it can:

- 🗨️ **Hold intelligent conversations** powered by Large Language Models (OpenRouter)
- 🧠 **Remember every user** — persistent chat history and preferences in PostgreSQL
- 📅 **Manage Google Calendar** — "Schedule a meeting tomorrow at 3pm" → real event created via OAuth 2.0
- 📄 **Answer questions about uploaded documents** using RAG (Retrieval-Augmented Generation) with vector search
- ⏰ **Run background jobs** — reminders and document processing via Celery

> **In one sentence:** An AI-powered personal assistant on Telegram that understands natural language, remembers its users, and takes real-world actions like managing Google Calendar events — built as a scalable, production-grade backend.

### Engineering Highlights

| Area               | What was built                                                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Architecture**   | Clean Architecture with strict layers (API → Services → Repositories → Models), Dependency Injection, Repository Pattern, SOLID                                                |
| **AI Engineering** | LLM tool calling (function calling) with a custom extensible tool registry, RAG pipeline (embeddings → Qdrant vector search → context-aware answers), multi-step task planning |
| **Integrations**   | Telegram Bot API (webhook + polling), Google OAuth 2.0, Google Calendar API, OpenRouter LLM API, Qdrant vector DB                                                              |
| **Performance**    | 100% async Python (asyncio) — many users can chat concurrently; Redis caching                                                                                                  |
| **Deployment**     | Full Docker Compose stack (FastAPI, Celery, PostgreSQL, Redis, Qdrant, Nginx) with HTTPS webhooks; plus a zero-dependency SQLite dev mode                                      |
| **Code Quality**   | Type hints everywhere, Pydantic v2 validation, SQLAlchemy 2 async ORM, Alembic migrations, Ruff + strict mypy                                                                  |

### Bullet points (achievements style)

- Built a **production-grade AI assistant** on Telegram serving multiple users concurrently using **Python, FastAPI, and 100% async I/O**
- Designed a **Clean Architecture** backend (API → Services → Repositories → Models) with **Dependency Injection** and the **Repository Pattern**, keeping business logic testable and framework-independent
- Implemented **LLM function calling (tool use)** with a custom extensible tool registry — the AI creates, lists, and deletes **Google Calendar** events via **OAuth 2.0** through a seamless web-based login flow
- Developed a **RAG pipeline** for document understanding: upload → embeddings → **Qdrant** vector search → context-aware answers
- Persisted long-term memory (users, chats, messages, preferences) in **PostgreSQL** with **SQLAlchemy 2 async ORM** and **Alembic** migrations
- Containerized the full stack with **Docker Compose** (FastAPI, Celery, PostgreSQL, Redis, Qdrant, Nginx) and secure **HTTPS Telegram webhooks**, plus a zero-dependency SQLite dev mode for fast local development
- Enforced code quality with **type hints, Pydantic v2 validation, Ruff linting, and strict mypy**

### Skills / Keywords Demonstrated

`Python` · `FastAPI` · `AsyncIO` · `LLM Integration (OpenRouter)` · `Function/Tool Calling` · `RAG` · `Embeddings` · `Vector DB (Qdrant)` · `PostgreSQL` · `SQLAlchemy 2` · `Alembic` · `Redis` · `Celery` · `Docker` · `Docker Compose` · `Nginx` · `REST API` · `OAuth 2.0` · `Google Calendar API` · `Telegram Bot API` · `Clean Architecture` · `SOLID` · `Repository Pattern` · `Dependency Injection` · `Pydantic v2` · `Webhooks`

---

## 🔄 How One Message Works

From the moment a user hits **Send** in Telegram to the bot's reply:

![How One Message Works](docs/images/how-one-message-works.jpg)

<details>
<summary>Step-by-step breakdown</summary>

1. **Telegram** delivers the update to the FastAPI app (webhook in production, polling in dev)
2. **TelegramService** parses the message and loads/creates the user and chat (PostgreSQL)
3. **ConversationService** builds the prompt: system instructions + user preferences + recent history + RAG context
4. **LLM Client** calls OpenRouter; if the model requests a tool, the **Tool Registry** executes it (e.g. Google Calendar) and loops back
5. The final answer is persisted as a message and sent back via the **Telegram Bot API**

</details>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Telegram Bot                          │
│                     @sanchaintun_bot                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ webhook / polling
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Application                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  API v1  │  │ Services │  │  Tools   │  │   LLM Client │ │
│  │  Routes  │──│  Layer   │──│  System  │──│  (OpenRouter)│ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
│                      │          │                             │
│                      ▼          ▼                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │Repositary│  │  Models  │  │  Vector  │                    │
│  │  Layer   │  │ SQLAlchm │  │  Qdrant  │                    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│       │              │             │                          │
└───────┼──────────────┼─────────────┼──────────────────────────┘
        │              │             │
        ▼              ▼             ▼
   ┌────────┐    ┌──────────┐   ┌────────┐
   │Postgres│    │  Redis   │   │ Qdrant │
   │   DB   │    │  Cache   │   │VectorDB│
   └────────┘    └──────────┘   └────────┘
```

## Tech Stack

| Layer               | Technology                                                  |
| ------------------- | ----------------------------------------------------------- |
| **Backend**         | FastAPI, Python 3.13, AsyncIO                               |
| **Database**        | PostgreSQL, SQLAlchemy 2, Alembic                           |
| **Cache**           | Redis                                                       |
| **Vector DB**       | Qdrant                                                      |
| **LLM Provider**    | OpenRouter API (default: `deepseek/deepseek-v4-flash-0731`) |
| **Bot**             | Telegram Bot API (polling / webhook)                        |
| **Background Jobs** | Celery + Redis                                              |
| **Deployment**      | Docker, Docker Compose, Nginx                               |
| **Architecture**    | Clean Architecture, SOLID, Repository Pattern, DI           |

## Features

- ✅ **Natural conversation** — LLM-powered via OpenRouter
- ✅ **Long-term memory** — Persistent chat history in PostgreSQL
- ✅ **Google Calendar** — OAuth2 web-based login, create/list/delete events
- ✅ **Tool calling** — Extensible tool system (calendar, email, system)
- ✅ **Task planning** — Multi-step task decomposition
- ✅ **File understanding (RAG)** — Qdrant vector search for document Q&A
- ✅ **Multi-user support** — Isolated per-user data and preferences
- ✅ **Telegram interaction** — Polling (dev) / webhook (production)
- 🔜 **Email integration** — Gmail API
- 🔜 **Voice assistant**
- 🔜 **Web dashboard**
- 🔜 **Mobile application**

---

## Quick Start (Development Mode)

### Prerequisites

- Python 3.10+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An OpenRouter API key (from [openrouter.ai](https://openrouter.ai))
- Google OAuth credentials (for Calendar integration)

### 1. Clone and setup

```bash
git clone <your-repo-url>
cd ai-personal-assistant

# (Optional but recommended) Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies (choose one)
pip install -r requirements.txt   # simple install
pip install -e .                  # editable install (developers)
```

### 2. Configure environment

Copy the template and fill in your own keys:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Minimum required values in `.env`:

```env
TELEGRAM_BOT_TOKEN="your_bot_token"
OPENROUTER_API_KEY="your_openrouter_key"
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
```

> ⚠️ **Never commit your real `.env`** — it is already listed in `.gitignore`.

### 3. Run (development mode)

```bash
python run_dev.py
```

This uses:

- **SQLite** (no PostgreSQL needed)
- **Telegram polling** (no webhook/ngrok needed)
- **Graceful fallback** for Redis/Qdrant

### 4. Open Telegram

Send `/start` to your bot on Telegram and start chatting!

---

## Production Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the full guide — Docker Compose on a VPS, systemd without Docker, HTTPS/Let's Encrypt setup, webhook registration, security checklist, and troubleshooting.

Quick start:

```bash
# 1. Copy the template and configure production values
cp .env.example .env
#    (set APP_DEBUG=false, WEBHOOK_URL=https://your-domain, strong secrets)

# 2. Build and start the full stack
docker-compose up --build -d
```

This starts:

- `assistant-app` — FastAPI + Uvicorn (auto-registers the Telegram webhook when `WEBHOOK_URL` is set)
- `assistant-celery` — Celery worker
- `assistant-celery-beat` — Celery beat scheduler
- `assistant-postgres` — PostgreSQL 16
- `assistant-redis` — Redis 7
- `assistant-qdrant` — Qdrant vector database
- `assistant-nginx` — Nginx reverse proxy (80/443)

### Webhook Setup

For production, set `WEBHOOK_URL` in `.env` (e.g. `https://bot.example.com`) and the app registers
`{WEBHOOK_URL}/api/v1/telegram/webhook` with Telegram on startup. HTTPS is required (Telegram only
supports webhook ports 443/80/88/8443). Leave `WEBHOOK_URL` empty to use polling instead.

---

## Project Structure

```
ai-personal-assistant/
├── app/
│   ├── api/v1/          # FastAPI route handlers
│   │   ├── auth.py      # Google OAuth callback
│   │   ├── chats.py     # Chat CRUD
│   │   ├── documents.py # Document upload + RAG
│   │   ├── llm.py       # LLM chat endpoint
│   │   ├── router.py    # Route aggregator
│   │   ├── telegram.py  # Telegram webhook endpoint
│   │   └── users.py     # User CRUD
│   ├── bot/             # Telegram bot client
│   ├── core/            # Config, DB, logging, Redis
│   ├── llm/             # OpenRouter LLM client
│   ├── models/          # SQLAlchemy ORM models
│   ├── repositories/    # Data access layer
│   ├── schemas/         # Pydantic v2 schemas
│   ├── services/        # Business logic layer
│   │   ├── calendar.py       # Calendar logic
│   │   ├── chat.py           # Chat + message logic
│   │   ├── conversation.py   # LLM conversation orchestration
│   │   ├── email.py          # Email logic
│   │   ├── embedding.py      # Text embeddings
│   │   ├── google_calendar.py # Google Calendar API + OAuth
│   │   ├── rag.py            # RAG pipeline
│   │   ├── task_planner.py   # Task decomposition
│   │   ├── telegram.py       # Telegram update handler
│   │   └── user.py           # User service
│   ├── tools/           # Tool calling system
│   │   ├── base.py      # Tool base class + preferences
│   │   ├── calendar_tools.py
│   │   ├── email_tools.py
│   │   ├── loader.py    # Tool registry
│   │   └── system_tools.py
│   ├── vector/          # Qdrant vector DB client
│   └── worker.py        # Celery app
├── alembic/             # Database migrations
├── nginx/               # Nginx config
├── docker-compose.yml   # Production stack
├── Dockerfile           # App container
├── run_dev.py           # Development runner
├── pyproject.toml       # Python dependencies
├── .env.example         # Environment variable template (copy to .env)
└── .gitignore           # Keeps secrets and local data out of version control
```

---

## Telegram Commands

| Command               | Description                               |
| --------------------- | ----------------------------------------- |
| `/start`              | Welcome message                           |
| `/help`               | Show available commands                   |
| `/connectcalendar`    | Connect Google Calendar (web-based OAuth) |
| `/disconnectcalendar` | Remove Google Calendar access             |

After connecting Google Calendar, you can also use natural language:

> "Create an event tomorrow at 3pm"
> "What's on my calendar?"
> "Schedule a meeting for Friday"

---

## Google OAuth Flow

The bot uses a **web-based OAuth flow** — like a real web app:

1. User sends `/connectcalendar`
2. Bot sends a unique authorization link
3. User clicks the link → signs in to Google → grants permission
4. Google redirects back to the server automatically
5. User sees a "Connected!" page ✅
6. Bot notifies the user on Telegram 🎉

The callback endpoint is:

```
GET http://localhost:8000/api/v1/auth/google/callback
```

---

## API Endpoints

| Method | Path                           | Description             |
| ------ | ------------------------------ | ----------------------- |
| GET    | `/api/v1/health`               | Health check            |
| POST   | `/api/v1/telegram/webhook`     | Telegram webhook        |
| GET    | `/api/v1/auth/google/callback` | Google OAuth callback   |
| POST   | `/api/v1/llm/chat`             | LLM chat completion     |
| POST   | `/api/v1/documents/upload`     | Upload document for RAG |
| POST   | `/api/v1/documents/query`      | Query documents         |
| GET    | `/api/v1/users/me`             | Get current user        |
| GET    | `/api/v1/chats`                | List user chats         |
| GET    | `/api/v1/chats/{id}/messages`  | List chat messages      |

---

## Configuration

All configuration lives in `.env` (copy from [.env.example](.env.example)). **Never commit the real `.env` file** — it contains your secrets. See the full variable reference with comments inside `.env.example`:

| Variable               | Description                | Default                                           |
| ---------------------- | -------------------------- | ------------------------------------------------- |
| `APP_NAME`             | Application name           | AI Personal Assistant                             |
| `APP_DEBUG`            | Debug mode                 | true                                              |
| `TELEGRAM_BOT_TOKEN`   | Telegram bot token         | —                                                 |
| `OPENROUTER_API_KEY`   | OpenRouter API key         | —                                                 |
| `LLM_MODEL`            | Default LLM model          | deepseek/deepseek-v4-flash-0731                   |
| `GOOGLE_CLIENT_ID`     | Google OAuth client ID     | —                                                 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | —                                                 |
| `GOOGLE_REDIRECT_URI`  | OAuth callback URL         | http://localhost:8000/api/v1/auth/google/callback |
| `DATABASE_URL`         | Database URL (auto in dev) | sqlite+aiosqlite:///./assistant.db                |

---

## Development

### Resetting the local database

Development mode uses a single SQLite file. Delete it to wipe all
users/chats/messages - it is recreated on the next start:

```bash
del assistant.db        # Windows
rm assistant.db         # Linux/macOS
```

(For Docker/PostgreSQL/Qdrant resets, see
[DEPLOYMENT.md](DEPLOYMENT.md) -> "Resetting / Clearing the Database".)

### Coding Standards

- **async/await** everywhere
- **Python type hints** on all functions
- **Pydantic v2** for all schemas
- **SQLAlchemy 2** async ORM
- **Dependency Injection** via constructor
- **Repository Pattern** for data access
- **Clean Architecture** — no business logic in routes

### Key Principles

- Business logic lives in the **Service Layer**, never in API routes
- Database access lives in the **Repository Layer**, never in services
- LLM calls go through the **LLM Client**, never directly from routes
- Infrastructure (DB, Redis, Qdrant) is injected, never imported directly

---

## What's Next?

- Email integration (Gmail API)
- Voice assistant
- Web dashboard
- Mobile application
- Background jobs and reminders
- Enhanced memory (semantic, episodic)

---

## License

MIT
