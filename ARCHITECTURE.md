# AI Personal Assistant — Architecture Deep Dive

> **Version:** 0.5.0  
> **Architecture:** Clean Architecture + SOLID + Repository Pattern + Dependency Injection  
> **Backend:** FastAPI + Python 3.10+ asyncio  
> **Database:** PostgreSQL (SQLite in dev mode)  
> **LLM:** OpenRouter API (deepseek/deepseek-v4-flash-0731)  
> **Bot:** Telegram Bot API

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer-by-Layer Explanation](#2-layer-by-layer-explanation)
3. [File-by-File Breakdown](#3-file-by-file-breakdown)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Design Decisions](#5-design-decisions)
6. [Key Patterns](#6-key-patterns)
7. [How to Extend](#7-how-to-extend)

---

## 1. Architecture Overview

### The Big Picture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                           │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Telegram Bot     │  │  REST API    │  │  Future: Web UI   │  │
│  │  @sanchaintun_bot │  │  /api/v1/*   │  │  Future: Mobile   │  │
│  └────────┬─────────┘  └──────┬───────┘  └────────────────────┘  │
└───────────┼───────────────────┼──────────────────────────────────┘
            │                   │
            ▼                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER (API)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Routes (app/api/v1/)                              │  │
│  │  - telegram.py   - webhook endpoint                       │  │
│  │  - auth.py       - Google OAuth callback                   │  │
│  │  - llm.py        - LLM chat endpoint                       │  │
│  │  - users.py      - User CRUD                               │  │
│  │  - chats.py      - Chat CRUD                               │  │
│  │  - documents.py  - Document upload + RAG query             │  │
│  │  - router.py     - Aggregates all routes                   │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER (Services)                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/services/                                              │  │
│  │  - telegram.py      - Orchestrates Telegram update flow    │  │
│  │  - conversation.py  - LLM conversation + tool calling      │  │
│  │  - chat.py          - Chat/message operations              │  │
│  │  - user.py          - User operations + preferences        │  │
│  │  - google_calendar.py - Google Calendar API + OAuth        │  │
│  │  - calendar.py      - Calendar logic abstraction           │  │
│  │  - email.py         - Email logic                          │  │
│  │  - embedding.py     - Text embedding generation            │  │
│  │  - rag.py           - RAG pipeline (retrieve + format)     │  │
│  │  - task_planner.py  - Multi-step task decomposition        │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/tools/                                                │  │
│  │  - base.py          - Tool abstract class + registry       │  │
│  │  - calendar_tools.py- Calendar tools (create, list, delete)│  │
│  │  - email_tools.py   - Email tools                          │  │
│  │  - system_tools.py  - System/info tools                    │  │
│  │  - loader.py        - Auto-registers all tools on startup  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER (Repositories)               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/repositories/                                         │  │
│  │  - base.py     - Generic CRUD (create, get, update, delete)│  │
│  │  - user.py     - User-specific queries                     │  │
│  │  - chat.py     - Chat-specific queries                     │  │
│  │  - message.py  - Message-specific queries                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/models/                                               │  │
│  │  - base.py      - Declarative Base (UUID PK, timestamps)   │  │
│  │  - user.py      - User ORM model                           │  │
│  │  - chat.py      - Chat ORM model                           │  │
│  │  - message.py   - Message ORM model                        │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                           │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  PostgreSQL  │  │  Redis   │  │  Qdrant  │  │  OpenRouter │ │
│  │  (SQLAlchemy)│  │  Cache   │  │  Vector  │  │  LLM API    │ │
│  └──────────────┘  └──────────┘  └──────────┘  └─────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/core/                                                 │  │
│  │  - config.py     - All settings from .env                  │  │
│  │  - database.py   - SQLAlchemy engine + session factory     │  │
│  │  - redis.py      - Redis connection manager                │  │
│  │  - logging.py    - Centralized logging config              │  │
│  │  - dependencies.py - DI container for services             │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/llm/                                                  │  │
│  │  - client.py    - OpenRouter HTTP client                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/vector/                                               │  │
│  │  - client.py    - Qdrant vector DB client                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  app/bot/                                                  │  │
│  │  - client.py    - Telegram Bot API HTTP client             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Core Architectural Principle

**Clean Architecture** with strict dependency rules:

```
API Routes → Services → Repositories → Database
     ↓            ↓            ↓
     └─── Schemas ──── Models ───┘
```

- **API Routes** (presentation) only call **Services** (business logic)
- **Services** only call **Repositories** (data access) and **Clients** (infrastructure)
- **Repositories** only access the database via **Models**
- **No layer** reaches across — Services never import Routes, Repositories never import Services

---

## 2. Layer-by-Layer Explanation

### Layer 1: Presentation (API Routes)

**Location:** `app/api/v1/`

**Purpose:** Handle HTTP requests, parse parameters, validate input with Pydantic schemas, call services, return responses.

**Rules:**

- NO business logic
- NO database access
- NO LLM calls
- Only parse, validate, delegate, and respond

**Files:**

| File           | Purpose                                                      |
| -------------- | ------------------------------------------------------------ |
| `router.py`    | Aggregates all sub-routers, defines health check             |
| `telegram.py`  | Single endpoint: `POST /webhook` — receives Telegram updates |
| `auth.py`      | `GET /auth/google/callback` — handles Google OAuth redirect  |
| `llm.py`       | `POST /llm/chat` — sends chat message to LLM                 |
| `users.py`     | CRUD for user management                                     |
| `chats.py`     | CRUD for chat history                                        |
| `documents.py` | Upload and query documents for RAG                           |

### Layer 2: Business Logic (Services)

**Location:** `app/services/`

**Purpose:** All business rules, orchestration, and decision-making live here.

**Rules:**

- Can call repositories and external clients
- Cannot import from API routes
- Cannot access database directly (only through repositories)
- Each service has a single responsibility

**Key Services:**

| Service                 | Responsibility                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| `TelegramService`       | Orchestrates Telegram update processing (user registration, chat creation, LLM conversation, response) |
| `ConversationService`   | Builds LLM prompts, manages message history, executes tool calls, saves responses                      |
| `ChatService`           | Chat and message CRUD operations                                                                       |
| `UserService`           | User registration, preferences management                                                              |
| `GoogleCalendarService` | OAuth flow, calendar API operations (create, list, delete events)                                      |
| `RAGService`            | Document retrieval, context formatting, embedding management                                           |

### Layer 3: Tool System

**Location:** `app/tools/`

**Purpose:** Provides callable functions that the LLM can invoke. Each tool defines its own schema (name, description, parameters) and execution logic.

**Flow:**

1. LLM decides it needs to perform an action
2. LLM responds with a `tool_calls` array
3. `ConversationService` calls `registry.execute(tool_name, arguments)`
4. The tool executes and returns a result string
5. The result is fed back to the LLM for the final response

**Files:**

| File                | Purpose                                                                     |
| ------------------- | --------------------------------------------------------------------------- |
| `base.py`           | `BaseTool` abstract class, `ToolRegistry`, in-memory user preferences cache |
| `calendar_tools.py` | Calendar tools: `create_event`, `list_events`, `delete_event`               |
| `email_tools.py`    | Email tools (future)                                                        |
| `system_tools.py`   | System tools: `get_current_time`, `get_user_info`                           |
| `loader.py`         | Auto-discovers and registers all tools on startup                           |

### Layer 4: Data Access (Repositories)

**Location:** `app/repositories/`

**Purpose:** Abstracts database access behind a clean interface. Every database query goes through a repository.

**Benefits:**

- Swap database implementation without changing business logic
- Easy to mock in tests
- Centralized query logic (no raw SQL scattered across services)

**Files:**

| File         | Purpose                                                                      |
| ------------ | ---------------------------------------------------------------------------- |
| `base.py`    | Generic `BaseRepository` with `create`, `get`, `get_all`, `update`, `delete` |
| `user.py`    | `UserRepository` — find by Telegram ID, update preferences                   |
| `chat.py`    | `ChatRepository` — find by user, get or create DM                            |
| `message.py` | `MessageRepository` — create, get history, get by ID                         |

### Layer 5: Models (ORM)

**Location:** `app/models/`

**Purpose:** SQLAlchemy ORM models that map to database tables. Defines the schema structure.

**Files:**

| File         | Purpose                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------ |
| `base.py`    | `DeclarativeBase` — all models inherit from this. Provides UUID primary key + `created_at`/`updated_at` timestamps |
| `user.py`    | `User` model — Telegram user data + preferences JSON                                                               |
| `chat.py`    | `Chat` model — conversation sessions per user                                                                      |
| `message.py` | `Message` model — individual messages with role, content, metadata                                                 |

### Layer 6: Schemas (Validation)

**Location:** `app/schemas/`

**Purpose:** Pydantic v2 models for API request/response validation and data transfer.

**Files:**

| File          | Purpose                                               |
| ------------- | ----------------------------------------------------- |
| `user.py`     | `UserCreate`, `UserResponse`                          |
| `chat.py`     | `ChatCreate`, `ChatUpdate`, `ChatResponse`            |
| `message.py`  | `MessageCreate`, `MessageResponse`                    |
| `llm.py`      | `ChatRequest`, `ChatResponse` for LLM endpoint        |
| `document.py` | `DocumentUpload`, `DocumentQuery`, `DocumentResponse` |

### Layer 7: Infrastructure

**Location:** `app/core/`, `app/llm/`, `app/vector/`, `app/bot/`

**Purpose:** External system integrations and shared infrastructure.

**Files:**

| File                   | Purpose                                                                   |
| ---------------------- | ------------------------------------------------------------------------- |
| `core/config.py`       | All environment variables loaded via Pydantic Settings                    |
| `core/database.py`     | SQLAlchemy async engine + session factory, supports PostgreSQL and SQLite |
| `core/redis.py`        | Redis async connection manager                                            |
| `core/logging.py`      | Centralized logging with debug/info levels                                |
| `core/dependencies.py` | DI container providing DB sessions and Redis                              |
| `llm/client.py`        | `LLMClient` — OpenRouter API calls with streaming support                 |
| `vector/client.py`     | `VectorClient` — Qdrant client for vector search (graceful fallback)      |
| `bot/client.py`        | `TelegramBotClient` — sends messages, typing indicators, manages webhooks |

---

## 3. File-by-File Breakdown

### Root Files

| File                 | Purpose                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------- |
| `run_dev.py`         | **Development runner.** Sets SQLite, polling mode, and starts the bot. No Docker needed. |
| `pyproject.toml`     | Python project metadata and dependencies                                                 |
| `Dockerfile`         | Container image for production                                                           |
| `docker-compose.yml` | Full production stack (app, celery, postgres, redis, qdrant, nginx)                      |
| `.env`               | All environment variables (tokens, keys, config)                                         |
| `alembic.ini`        | Database migration configuration                                                         |
| `README.md`          | Project overview and quick start                                                         |
| `ARCHITECTURE.md`    | This file — deep architecture documentation                                              |

### `app/main.py`

**The application entry point.**

- Creates a FastAPI instance via `create_app()` factory pattern
- Configures CORS middleware
- Registers all API v1 routes
- Manages startup/shutdown lifespan (init DB, tools, close connections)

Why factory pattern? It allows tests to create isolated app instances.

### `app/api/v1/router.py`

**Route aggregator.** All sub-routers are registered here:

- `/api/v1/health` — Health check
- `/api/v1/telegram/*` — Telegram webhook
- `/api/v1/auth/*` — Google OAuth
- `/api/v1/llm/*` — LLM chat
- `/api/v1/users/*` — User management
- `/api/v1/chats/*` — Chat management
- `/api/v1/documents/*` — Document upload + RAG

### `app/api/v1/telegram.py`

**Single endpoint:** `POST /webhook`

Receives Telegram updates, delegates to `TelegramService`. In production, Telegram sends updates here. In dev mode (`run_dev.py`), the polling loop bypasses this endpoint and calls `TelegramService` directly.

### `app/api/v1/auth.py`

**Single endpoint:** `GET /auth/google/callback`

Handles Google's OAuth redirect after user authorization. Contains:

- `_pending_oauth` — in-memory map of `state -> telegram_chat_id`
- `store_pending_oauth()` — called by `TelegramService` when generating an auth URL
- `google_callback()` — exchanges code for tokens, stores in user preferences, notifies user on Telegram
- `SUCCESS_HTML` / `ERROR_HTML` — styled HTML pages shown to the user after authorization

### `app/api/v1/llm.py`

**Single endpoint:** `POST /llm/chat`

Accepts `chat_id` and `message`, triggers `ConversationService.generate_response()`, returns the AI response. Used by future web dashboard.

### `app/services/telegram.py`

**The most important service.** `TelegramService` handles every incoming Telegram message:

1. **Parse update** — Extract message, user, chat data
2. **Register/update user** — via `UserService`
3. **Load preferences** — Google Calendar tokens from DB into in-memory cache
4. **Get or create DM chat** — via `ChatService`
5. **Handle commands** — `/start`, `/help`, `/connectcalendar`, `/disconnectcalendar`
6. **Handle OAuth code** — If message starts with "4/" (Google OOB code), exchange for tokens
7. **Save user message** — via `ChatService.add_message()`
8. **Send typing indicator** — via `bot_client.send_typing()`
9. **Generate AI response** — via `ConversationService.generate_response()`
10. **Send AI response** — via `bot_client.send_message()`

### `app/services/conversation.py`

**The LLM orchestration service.** `ConversationService` manages the full conversation loop:

1. **Load chat history** — Last 50 messages from database
2. **Build system prompt** — Includes current date + optional RAG context
3. **Search RAG** — Get relevant document chunks for the user's query
4. **Call LLM** — Send messages + tool specs to OpenRouter
5. **Handle tool calls** — If LLM requests tools, execute them and feed results back
6. **Repeat** — Up to 5 iterations to handle multi-step tool calls
7. **Save AI response** — Store response in database with metadata (model, tokens, tool calls)
8. **Return response** — Text to send back to user

### `app/services/google_calendar.py`

**Google Calendar integration.** Contains:

- `_get_flow()` — Creates OAuth2 flow with web redirect URI
- `get_auth_url(state)` — Generates Google authorization URL with unique state parameter
- `exchange_code(code, state)` — Exchanges authorization code for tokens
- `_get_credentials(token_data)` — Builds Credentials object from stored tokens, auto-refreshes if expired
- `_get_service(token_data)` — Builds Google Calendar API service
- `create_event()` — Creates event on user's primary calendar
- `list_events()` — Lists upcoming events
- `delete_event()` — Deletes an event

### `app/services/user.py`

**User management service.** `UserService` handles:

- `register_or_update()` — Create or update user from Telegram data
- `get_by_telegram_id()` — Find user by Telegram ID
- `get_preferences()` — Get user's preferences JSON
- `update_preferences()` — Update specific fields in preferences

### `app/services/chat.py`

**Chat management service.** `ChatService` handles:

- `get_or_create_dm()` — Find or create a direct message chat
- `add_message()` — Add a message to a chat
- `get_chat_history()` — Get messages for LLM context
- `archive_chat()` — Soft-delete a chat

### `app/services/rag.py`

**Retrieval-Augmented Generation service.** `RAGService` handles:

- `search_context()` — Find relevant documents for a query
- `format_context()` — Format retrieved documents into context string
- `add_document()` — Process and store a document
- Generates embeddings via `EmbeddingService`

### `app/services/embedding.py`

**Text embedding service.** Generates vector embeddings for text. Used by RAG to convert documents and queries into vectors for similarity search.

### `app/services/calendar.py`

**Calendar logic abstraction.** Wraps `GoogleCalendarService` for use by the tool system. Provides a consistent interface whether using Google Calendar or local storage.

### `app/services/email.py`

**Email service.** Prepares for Gmail API integration. Currently a placeholder/service layer.

### `app/services/task_planner.py`

**Task decomposition service.** Breaks complex user requests into multi-step plans. For example, "Plan a trip to Tokyo" gets broken into flights, hotels, itinerary, etc.

### `app/tools/base.py`

**Tool system foundation.** Contains:

- `BaseTool` — Abstract class. Every tool must implement `name`, `description`, `parameters` (JSON Schema), and `execute()`
- `ToolRegistry` — Global registry that stores all tools, generates OpenAI-compatible specs, and executes tool calls
- `_user_preferences` — In-memory cache of user preferences (includes Google Calendar tokens)
- `get_user_preferences()` / `update_user_preferences()` — Helper functions

### `app/tools/calendar_tools.py`

**Calendar tools for the LLM.** Three tools:

- `create_event` — Creates a calendar event with title, start, end, description
- `list_events` — Lists upcoming events
- `delete_event` — Deletes an event by ID

Each tool reads `user_id` from arguments, looks up the user's Google Calendar tokens from `get_user_preferences()`, and calls the appropriate Google Calendar API function.

### `app/tools/system_tools.py`

**System tools for the LLM.** Two tools:

- `get_current_time` — Returns current date and time
- `get_user_info` — Returns user's display name and preferences

### `app/tools/loader.py`

**Tool auto-loader.** On startup, imports all tool modules, instantiates each tool, and registers it with the global `ToolRegistry`.

### `app/repositories/base.py`

**Generic CRUD repository.** `BaseRepository` provides:

- `create(**kwargs)` — Insert a new record
- `get(id)` — Get by primary key
- `get_all(skip, limit)` — Paginated list
- `update(id, **kwargs)` — Update by primary key
- `delete(id)` — Delete by primary key

All domain repositories inherit from this.

### `app/repositories/user.py`

**User-specific queries.** `UserRepository` adds:

- `get_by_telegram_id()` — Find user by Telegram chat ID

### `app/repositories/chat.py`

**Chat-specific queries.** `ChatRepository` adds:

- `get_by_user()` — Get all chats for a user
- `get_or_create_dm()` — Find or create a DM chat for a user+Telegram chat

### `app/repositories/message.py`

**Message-specific queries.** `MessageRepository` adds:

- `get_chat_history()` — Get messages for a chat ordered by creation time (for LLM context)

### `app/models/base.py`

**Declarative base.** All models inherit from `Base` which provides:

- `id` — UUID primary key (auto-generated)
- `created_at` — Auto-set timestamp
- `updated_at` — Auto-updated timestamp

### `app/models/user.py`

**User model.** Fields:

- `telegram_id` — Unique Telegram user ID
- `username`, `first_name`, `last_name`, `language_code` — Telegram profile data
- `is_active`, `is_bot` — Status flags
- `last_interaction_at` — When the user last messaged the bot
- `preferences` — JSON field for storing Google Calendar tokens, settings, etc.

### `app/models/chat.py`

**Chat model.** Fields:

- `user_id` — Foreign key to User
- `title` — Optional chat title
- `telegram_chat_id` — Telegram's chat ID
- `status` — `active` or `archived`
- `metadata_json` — JSON field for additional data

### `app/models/message.py`

**Message model.** Fields:

- `chat_id` — Foreign key to Chat
- `user_id` — Foreign key to User
- `role` — `user`, `assistant`, `system`, or `tool`
- `content` — Message text content
- `telegram_message_id` — Telegram's message ID
- `metadata_json` — JSON field for LLM metadata (model, tokens, tool calls, RAG usage)

### `app/llm/client.py`

**OpenRouter HTTP client.** `LLMClient`:

- `chat_completion()` — Send messages + optional tool specs, receive response
- `chat_completion_stream()` — Stream tokens one by one
- Uses `httpx.AsyncClient` with 60s timeout
- Sends `HTTP-Referer` and `X-Title` headers for OpenRouter ranking

### `app/vector/client.py`

**Qdrant vector database client.** `VectorClient`:

- `upsert_document()` — Store document embedding + payload
- `search_similar()` — Find similar documents by vector
- `delete_document()` — Remove document
- **Graceful fallback** — If Qdrant is not available (dev mode), logs a warning and skips operations

### `app/bot/client.py`

**Telegram Bot API client.** `TelegramBotClient`:

- `send_message()` — Send text message with optional Markdown
- `send_typing()` — Show "typing..." indicator
- `set_webhook()` / `delete_webhook()` / `get_webhook_info()` — Webhook management

### `app/core/config.py`

**Application settings.** Uses Pydantic Settings to load from `.env`:

- Core: `APP_NAME`, `APP_DEBUG`, `SECRET_KEY`
- Telegram: `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_URL`
- OpenRouter: `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_MAX_TOKENS`, `LLM_TEMPERATURE`
- Database: `POSTGRES_*` with computed `DATABASE_URL` property
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- Qdrant: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`
- Google OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- Server: `HOST`, `PORT`

### `app/core/database.py`

**Database engine and session management.**

- Creates async SQLAlchemy engine (supports `asyncpg` for PostgreSQL, `aiosqlite` for SQLite)
- `async_session_factory` — Creates sessions
- `get_session()` — Async generator providing sessions with auto-commit/rollback
- `init_db()` — Creates all tables (dev mode)
- `close_db()` — Disposes engine

### `app/core/redis.py`

**Redis connection manager.**

- `get_redis()` — Singleton Redis client
- `close_redis()` — Close connection pool
- Used for caching, Celery broker, and session storage

### `app/core/logging.py`

**Logging configuration.**

- `setup_logging()` — Configures root logger with colored format
- Suppresses noisy third-party loggers (httpx, httpcore, asyncio)
- Exports `logger` for use across all modules

### `app/core/dependencies.py`

**Dependency injection container.** `Dependencies` class:

- `get_db()` — Provides database session
- `get_redis()` — Provides Redis client
- Singleton `deps` instance used throughout the app

### `app/worker.py`

**Celery application.** Defines background tasks:

- `send_reminder()` — Send scheduled reminders
- `process_document()` — Async document processing (offloads heavy work)
- `cleanup_expired_data()` — Housekeeping tasks

### `run_dev.py`

**Development runner.** The only file you need to run in development:

1. Sets `DATABASE_URL` to SQLite
2. Sets `APP_DEBUG` and `USE_POLLING`
3. Disables Redis/Qdrant (graceful fallback)
4. Initializes database and tools
5. Starts polling loop (calls Telegram API `getUpdates`)
6. For each update, creates a session and calls `TelegramService.handle_update()`

---

## 4. Data Flow Diagrams

### Flow 1: User sends a message to the bot

```
User
  │
  │  "Create an event tomorrow at 3pm"
  ▼
Telegram Bot API
  │
  │  Polling (dev) or Webhook (prod)
  ▼
run_dev.py (polling loop)  ─or─  POST /api/v1/telegram/webhook
  │
  ▼
TelegramService.handle_update(update)
  │
  ├── 1. UserService.register_or_update()  →  UserRepository  →  Database
  │
  ├── 2. Load preferences from DB → in-memory cache
  │
  ├── 3. ChatService.get_or_create_dm()  →  ChatRepository  →  Database
  │
  ├── 4. ChatService.add_message()  →  MessageRepository  →  Database
  │
  ├── 5. bot_client.send_typing()  →  Telegram API
  │
  └── 6. ConversationService.generate_response()
        │
        ├── Load chat history (last 50 messages)
        │
        ├── Search RAG context (if relevant)
        │
        ├── Build messages array + tool specs
        │
        ├── LLMClient.chat_completion(messages, tools)
        │     │
        │     ▼
        │   OpenRouter API  →  deepseek/deepseek-v4-flash-0731
        │     │
        │     ◄── Response with tool_calls
        │
        ├── ToolRegistry.execute("create_event", {...})
        │     │
        │     ├── calendar_tools.py: get user's Google Calendar tokens
        │     ├── GoogleCalendarService.create_event()
        │     │     │
        │     │     ▼
        │     │   Google Calendar API
        │     │
        │     └── Return result string
        │
        ├── LLMClient.chat_completion() (final response)
        │
        └── MessageRepository.create()  →  Database
              │
              └── Final AI response text
  │
  ▼
bot_client.send_message()  →  Telegram API  →  User sees "Event created! ✅"
```

### Flow 2: Google Calendar OAuth

```
User sends /connectcalendar
  │
  ▼
TelegramService
  │
  ├── Generate random state token
  ├── store_pending_oauth(state, telegram_chat_id)
  ├── google_calendar.get_auth_url(state=state)
  └── Send link to user
        │
        ▼
User clicks link → Opens browser → Google sign-in page
  │
  ├── User signs in
  ├── Grants calendar permission
  └── Google redirects to GET /api/v1/auth/google/callback?code=...&state=...
        │
        ▼
app/api/v1/auth.py: google_callback()
  │
  ├── Look up telegram_chat_id from _pending_oauth[state]
  ├── google_calendar.exchange_code(code, state)
  │     │
  │     ▼
  │   Google OAuth API → Returns tokens
  │
  ├── UserService.update_preferences() → Store tokens in DB
  ├── update_user_preferences() → Update in-memory cache
  ├── bot_client.send_message() → "Connected! ✅"
  └── Return SUCCESS_HTML page to browser
```

### Flow 3: Tool Calling Loop

```
LLM Response with tool_calls
  │
  ▼
ConversationService (loop up to 5 iterations)
  │
  ├── Append assistant message with tool_calls to messages
  │
  ├── For each tool_call:
  │     ├── Parse tool name + arguments
  │     ├── Inject user_id from chat context
  │     └── registry.execute(name, arguments)
  │           │
  │           ▼
  │         Tool returns result string
  │
  ├── Append tool result to messages
  │
  └── Call LLM again with updated messages
        │
        ├── If more tool_calls → repeat
        └── If no tool_calls → final response
```

---

## 5. Design Decisions

### Why Clean Architecture?

**Problem:** Most AI assistants start as a single `main.py` with everything mixed together. This works for a demo but fails when you need to add features, change databases, or support multiple interfaces.

**Solution:** Clean Architecture enforces strict layer separation. You can:

- Swap PostgreSQL for SQLite (already done — `run_dev.py` sets `DATABASE_URL`)
- Add a web dashboard without touching Telegram code
- Change LLM providers by modifying only `LLMClient`
- Test business logic without database or network

### Why Repository Pattern?

**Problem:** Direct database access in services makes it impossible to:

- Unit test without a real database
- Change database technology
- Audit query patterns

**Solution:** All database access goes through repositories. If you need to switch from SQLAlchemy to another ORM, you only change the repositories — services remain untouched.

### Why Service Layer?

**Problem:** Putting business logic in API routes leads to:

- Fat controllers that are hard to test
- Duplicated logic when multiple endpoints need the same operation
- Tight coupling between HTTP and business logic

**Solution:** A dedicated service layer contains all business rules. API routes are thin — they parse requests, validate, call services, and return responses.

### Why In-Memory User Preferences Cache?

**Problem:** Google Calendar tokens are needed by tools (which are stateless functions). Looking up tokens from the database on every tool call adds latency.

**Solution:** Load tokens into an in-memory dict (`_user_preferences`) when the user sends a message. Tools access this cache instantly. The cache is repopulated on every message, so it's always fresh.

### Why Graceful Fallback for Infrastructure?

**Problem:** Developers shouldn't need to run Redis, Qdrant, and PostgreSQL just to test a conversation feature.

**Solution:** All infrastructure clients check if their host is configured. If not, they log a warning and skip operations. This means:

- `run_dev.py` works with zero infrastructure
- Production Docker Compose has everything enabled
- No code changes needed between dev and prod

### Why Web-Based OAuth Instead of Code Pasting?

**Problem:** The original flow required users to copy-paste a code from Google. This is confusing and breaks the user experience.

**Solution:** Web-based OAuth with a redirect URI. The user clicks a link, authorizes in the browser, and Google redirects back to our server. The callback endpoint exchanges the code, stores tokens, and notifies the user on Telegram. No code copying needed.

---

## 6. Key Patterns

### Dependency Injection

```python
class TelegramService:
    def __init__(self, session: AsyncSession) -> None:
        self._user_service = UserService(session)
        self._chat_service = ChatService(session)
        self._conversation_service = ConversationService(session)
```

Services receive their dependencies through the constructor, not by importing them. This makes testing easy — you can inject mock sessions and services.

### Singleton Clients

```python
# app/bot/client.py
bot_client = TelegramBotClient()

# app/llm/client.py
llm_client = LLMClient()

# app/vector/client.py
vector_client = VectorClient()
```

Infrastructure clients are singletons. They're created once and shared across the application. This ensures:

- One connection pool per service
- Consistent configuration
- Easy lifecycle management (startup/shutdown)

### Async Everywhere

```python
async def handle_update(self, update: dict) -> dict:
    user = await self._user_service.register_or_update(user_data)
    chat = await self._chat_service.get_or_create_dm(...)
    ai_content = await self._conversation_service.generate_response(...)
    await bot_client.send_message(...)
```

All I/O operations are async. This allows the server to handle multiple users concurrently without blocking.

### Type Hints Everywhere

```python
async def create_event(
    token_data: dict,
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> dict:
```

Every function has type hints. This provides:

- IDE autocompletion and error detection
- Self-documenting code
- Easier refactoring

### Abstract Base Class for Tools

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict: ...

    @abstractmethod
    async def execute(self, **kwargs) -> str: ...
```

Every tool implements the same interface. The registry doesn't care what a tool does internally — it just calls `execute()` and returns the result. Adding a new tool means creating a new class that extends `BaseTool` and registers it.

---

## 7. How to Extend

### Add a New Tool

1. Create `app/tools/my_tool.py`
2. Extend `BaseTool`:

   ```python
   class MyTool(BaseTool):
       name = "my_tool"
       description = "Does something useful"
       parameters = {
           "type": "object",
           "properties": {
               "param1": {"type": "string", "description": "A parameter"},
           },
           "required": ["param1"],
       }

       async def execute(self, **kwargs) -> str:
           param1 = kwargs.get("param1", "")
           return f"Did something with {param1}"
   ```

3. Register it in `app/tools/loader.py`:
   ```python
   from app.tools.my_tool import MyTool
   registry.register(MyTool())
   ```
4. That's it! The LLM will discover and use the tool automatically.

### Add a New API Endpoint

1. Create `app/api/v1/my_feature.py`:

   ```python
   from fastapi import APIRouter
   router = APIRouter(prefix="/my-feature", tags=["my-feature"])

   @router.get("/")
   async def my_endpoint():
       return {"hello": "world"}
   ```

2. Register in `app/api/v1/router.py`:
   ```python
   from app.api.v1.my_feature import router as my_feature_router
   router.include_router(my_feature_router)
   ```

### Add a New Database Model

1. Create `app/models/my_model.py`:

   ```python
   from app.models.base import Base
   from sqlalchemy.orm import Mapped, mapped_column

   class MyModel(Base):
       __tablename__ = "my_models"
       name: Mapped[str] = mapped_column(nullable=False)
   ```

2. Create `app/repositories/my_model.py`:

   ```python
   from app.repositories.base import BaseRepository
   from app.models.my_model import MyModel

   class MyModelRepository(BaseRepository[MyModel]):
       def __init__(self, session):
           super().__init__(session, MyModel)
   ```

3. Create `app/schemas/my_model.py` — Pydantic schemas
4. Create `app/services/my_model.py` — Business logic using the repository
5. Create API endpoints that use the service

### Add a New Infrastructure Client

1. Create `app/some_service/client.py`
2. Use singleton pattern (create once, share globally)
3. Implement graceful fallback for dev mode
4. Add config to `app/core/config.py`
5. Add startup/shutdown to `app/main.py` lifespan

---

## Summary

This project follows **Clean Architecture** with strict separation of concerns:

| Layer              | What it does                   | What it knows         |
| ------------------ | ------------------------------ | --------------------- |
| **API Routes**     | Handle HTTP requests/responses | Services only         |
| **Services**       | Business logic, orchestration  | Repositories, Clients |
| **Tools**          | Callable functions for LLM     | Services, Preferences |
| **Repositories**   | Database access                | Models only           |
| **Models**         | Table structure                | Database schema       |
| **Schemas**        | Input/output validation        | Pydantic rules        |
| **Infrastructure** | External integrations          | Config settings       |

The design ensures that the system can grow from a Telegram bot to a full web/mobile application with multiple AI capabilities without major refactoring. Each component is independently testable, replaceable, and maintainable.
