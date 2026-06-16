# StayMatch AI Service — Full Project Documentation

## Overview

**StayMatch AI Service** is a bilingual (Arabic/English) conversational AI chatbot for an Egyptian housing platform. Users interact in natural language (Egyptian Arabic or English) to search for apartments, rooms, and shared housing. The bot understands intent, extracts entities (location, price, amenities), conducts smart clarification dialogues, queries a property database, and returns formatted results.

---

## Tech Stack

| Technology | Role |
|---|---|
| Python 3.11 + FastAPI | REST API server |
| SQL Server (pyodbc/FreeTDS) | Property database (Properties, Rooms, Amenities) |
| PostgreSQL (Neon) | Chat database (Conversations, Messages, Preferences, Analytics) |
| ChromaDB + intfloat/multilingual-e5-small | Vector-based FAQ search (RAG) |
| Groq LLaMA 3.1 8B (via LangChain) | LLM fallback for entity extraction |
| SQLAlchemy | Database ORM |
| Docker / Railway / Render | Deployment |

---

## Architecture Diagram

```
┌─────────────┐     POST /chat      ┌────────────────────┐
│  .NET App   │ ──────────────────▶  │   FastAPI Server   │
│  (Frontend) │                      │   (app/main.py)    │
└─────────────┘                      └────────┬───────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  SearchService   │ (Orchestrator)
                                    └────────┬─────────┘
                            ┌────────────────┼────────────────┐
                            │                │                │
                            ▼                ▼                ▼
                   ┌────────────┐   ┌──────────────┐   ┌────────────┐
                   │ NLP Pipeline│   │ RAG/FAQ      │   │ ChatService│
                   │ (15 stages)│   │ (ChromaDB)   │   │ (smalltalk)│
                   └─────┬──────┘   └──────────────┘   └────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │ ConversationFlow │ (Clarification / Slot-Filling)
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  SearchExecutor  │
               └────────┬─────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ┌───────────────┐      ┌───────────────┐
    │ SQL Server    │      │ PostgreSQL    │
    │ (Properties)  │      │ (Chat/Prefs)  │
    └───────────────┘      └───────────────┘
```

---

## Directory Structure

```
app/
├── api/              # FastAPI route definitions
│   └── routes.py     # POST /chat, GET /debug/db-status
├── core/             # Core modules
│   ├── config.py     # Settings (env vars, DB URLs)
│   ├── memory_store.py  # In-memory session store + DB sync
│   ├── session_context.py  # SessionContext model (state per user)
│   └── security.py   # Rate limiting + input sanitization
├── database/         # Database layer
│   ├── connection.py       # SQL Server engine
│   ├── chatbot_connection.py  # PostgreSQL engine
│   ├── chatbot_schema.sql     # Chat DB schema
│   ├── migrations/            # SQL migration scripts
│   └── repositories/          # 7 repository classes (data access)
├── models/           # Pydantic models
│   ├── chat_models.py     # ChatRequest (user_id, message)
│   ├── response_models.py # ChatResponse (reply, suggestions, results)
│   └── search_models.py   # SearchFilters (all extracted filters)
├── nlp/              # NLP Pipeline
│   ├── nlp_pipeline.py    # Main pipeline (15 stages)
│   ├── rule_engine.py     # Rule-based intent + entity extraction
│   ├── text_normalizer.py # Arabic text normalization
│   └── token_maps/        # 7 tokenization files (room, property, price, facility, sharing, quality, misc)
├── services/         # Business logic (10 services)
│   ├── search_service.py       # Main orchestrator
│   ├── search_executor.py      # DB query execution + pagination
│   ├── conversation_flow.py    # Clarification logic + slot filling
│   ├── chat_service.py         # Greeting/thanks/bye responses
│   ├── rag_service.py          # FAQ orchestrator (ChromaDB + fuzzy)
│   ├── knowledge_service.py    # Fuzzy FAQ matching
│   ├── location_service.py     # Egyptian location detection
│   ├── suggestion_generator.py # QuickReply suggestions
│   ├── recommendation_client.py # Recommendation scores + interactions
│   └── llm_price_classifier.py # LLM price intent fallback
├── extractors/       # Entity extractors
│   ├── price_extractor.py    # Rule-based + LLM price extraction
│   ├── followup_extractor.py # Follow-up intent detection
│   └── query_extractor.py    # Full LLM extraction (Groq LLaMA)
├── formatters/       # Response formatting
│   └── response_formatter.py # Converts DB rows → chat text + cards
├── rag/              # RAG system
│   ├── vector_store.py  # ChromaDB init + query
│   └── faq_loader.py    # Loads knowledge_base.json → documents
├── data/             # Static data
│   ├── knowledge_base.json  # ~65 FAQ Q&A pairs (bilingual)
│   └── locations.json       # Egypt governorates + cities mapping
├── utils/            # Utilities
│   ├── bilingual_responses.py  # Response templates (ar/en)
│   ├── language_detector.py    # Detect Arabic vs English
│   ├── location_mapping.py     # Governorate/city name mapping
│   ├── logger.py               # Debug logging with section headers
│   ├── price_parser.py         # Number/range extraction from Arabic text
│   ├── sql_builder.py          # Dynamic WHERE clause builder
│   └── text_normalizer.py      # Arabic character normalization
├── prompts/          # LLM prompts
│   └── extraction_prompt.py   # System prompt for Groq LLaMA
└── validators/       # Filter validation
    └── filter_validator.py    # Validates/fixes extracted filters
```

---

## Request Flow (Step by Step)

### Step 1: API Endpoint
```
POST /chat
Body: { "user_id": "12345", "message": "عايز شقة في القاهرة" }
```

### Step 2: Session Management
- `user_id` is used as `session_id` (one conversation per user)
- `MemoryStore.get_context()` loads/creates session:
  - Check in-memory cache (max 1000 sessions)
  - If not found → reconstruct from PostgreSQL
  - If brand new → create fresh session + DB record
- First message: loads user's saved preferences from `user_preferences` table

### Step 3: NLP Pipeline (15 Stages)

| # | Stage | What it does |
|---|-------|-------------|
| 1 | Normalize | Arabic normalization (أ/إ/آ→ا, ة→ه, collapse tripled chars) |
| 2 | Tokenize | Split words + merge bigrams using 7 token maps |
| 3 | Intent | Score intents: property_search, room_search, show_more, go_back, small_talk, faq |
| 4 | Location | Exact match → phonetic → fuzzy (Egyptian governorates + cities) |
| 5 | Price | Rule-based: range/budget/max/min; Arabic digits + number words |
| 6 | Amenities | wifi, تكييف, بلكونة, حمام خاص (handles negation: "مش عايز") |
| 7 | Tenant/Gender | Student/worker, male/female |
| 8 | Housing Type | Priority: shared > room > apartment |
| 9 | Sort | أرخص → price_low, أغلى → price_high |
| 10 | Slot Reply | yes/no/any answers to pending clarification questions |
| 11 | Entity Promotion | If intent=invalid but entities exist → promote to clarification |
| 12 | LLM Fallback | If confidence < 65% → call Groq LLaMA 3.1 for extraction |
| 13 | Merge | Inherit unspecified fields from last_search |
| 14 | Validate | Fix price ranges, validate enum values |
| 15 | Enforce | housing_type ↔ search_type consistency |

### Step 4: Intent Routing

| Intent | Action |
|--------|--------|
| `property_search` / `room_search` | Proceed to search flow |
| `show_more` | Paginate forward (next 5 results) |
| `go_back` | Return to previous search |
| `small_talk` | Greeting/thanks/bye response |
| `faq` | ChromaDB semantic search + fuzzy fallback |
| `invalid` | Try FAQ, else fallback message |

### Step 5: Clarification (Slot Filling)
If required info is missing:
- No search_type → "عايز تدور على شقة ولا غرفة ولا مشترك؟"
- No location → "عايز تدور في منطقة إيه؟"
- No price (early turns) → "عندك budget معين؟"

### Step 6: Search Execution
- `SearchExecutor` selects `PropertyRepository` or `RoomRepository`
- Builds dynamic SQL WHERE clause (location, price, amenities, type, tenant)
- Pagination: OFFSET/FETCH or Cursor-based
- Attaches recommendation scores if available
- `ResponseFormatter` converts rows → bilingual text + property cards

### Step 7: Persistence (Fire-and-Forget)
After response is sent:
- Messages saved to `messages` table
- Session metadata (context) saved as JSON in `conversations`
- User preferences persisted to `user_preferences`
- Analytics updated (message count, search count)

---

## Databases

### SQL Server (Property Database)
| Table | Purpose |
|-------|---------|
| Properties | Apartments/full units (name, location, rent, rooms, size) |
| Rooms | Individual rooms (price, capacity, bathroom type, amenities) |
| PropertyAmenities | WiFi, AC, TV, washer, parking, etc. |
| AllowedTenants | Families, students, workers, gender, pets |

### PostgreSQL - Neon (Chat Database)
| Table | Purpose |
|-------|---------|
| conversations | Session tracking (session_id UNIQUE, user_id, metadata JSON) |
| messages | Chat messages (conversation_id FK, role, content) |
| user_preferences | Saved user preferences (budget, location, amenities) |
| search_history | Search log (type, location, price, results count) |
| session_analytics | Metrics (total messages, searches, no-results count) |
| property_recommendations | Recommendation scores per user+property |
| room_recommendations | Recommendation scores per user+room |
| user_interactions | User click/view/dwell tracking |

---

## RAG (FAQ System)

**Purpose:** Answer general questions about the platform without searching the property DB.

**How it works:**
1. On startup: loads 65 FAQ documents from `knowledge_base.json`
2. Indexes them in ChromaDB using `intfloat/multilingual-e5-small` embeddings
3. On query: converts user question to embedding → cosine similarity search
4. Returns answer if distance ≤ 0.6 (short queries) or ≤ 0.5 (long queries)
5. Fallback: `KnowledgeService` does fuzzy keyword matching

**FAQ Categories:**
- Platform info (what is StayMatch, pricing, AI)
- Search help (how to search, filter, Arabic support)
- Pricing & payment (rent, deposits, utilities)
- Safety (verification, fraud prevention)
- Account (registration, profile, saved searches)

---

## Recommendation System

- **Shared DB pattern:** Both chatbot and recommendation service use the same PostgreSQL
- **Reads:** `property_recommendations` and `room_recommendations` tables
- **Writes:** User interactions (clicks, views, dwell time) to `user_interactions`
- **Sync:** Triggers preferences sync to recommendation service (fire-and-forget)
- **Effect:** Results are re-ranked by recommendation score when available

---

## Session & Memory Management

```
┌──────────────────────────────────────────────┐
│              MemoryStore                       │
│  ┌────────────────────────────────────┐      │
│  │  In-Memory Cache (dict)            │      │
│  │  Key: user_id → SessionContext     │      │
│  │  Max: 1000 sessions (LRU eviction) │      │
│  └────────────────────────────────────┘      │
│                    ↕ sync                     │
│  ┌────────────────────────────────────┐      │
│  │  PostgreSQL (Neon)                 │      │
│  │  conversations.metadata (JSON)     │      │
│  │  messages table                    │      │
│  └────────────────────────────────────┘      │
└──────────────────────────────────────────────┘
```

**SessionContext contains:**
- `conversation_history` (last 15 messages)
- `last_search` (SearchFilters)
- `user_preferences` (budget, location, amenities)
- `pending_slot` (current clarification question)
- `current_offset`, `page_size` (pagination state)
- `seen_property_ids`, `seen_room_ids` (avoid duplicates)
- `search_history` (last 5 searches for go_back)

---

## Key Features

| Feature | Description |
|---------|-------------|
| Bilingual | Full Arabic + English support with auto-detection |
| Egyptian Arabic | Understands عامية مصرية (slang, typos, phonetic variations) |
| Smart Clarification | Asks follow-up questions when info is missing |
| Pagination | "ورينى تاني" / "show more" for next results |
| Go Back | "ارجع" / "go back" to previous search |
| Typo Tolerance | Fuzzy matching for locations and keywords |
| RAG FAQ | Semantic search for platform questions |
| Recommendations | AI-based property ranking per user |
| Session Persistence | Survives server restarts (DB-backed) |
| Preference Learning | Remembers user preferences across sessions |
| Fire-and-Forget | Background DB writes don't slow responses |

---

## Deployment

| Platform | Config |
|----------|--------|
| Docker | Python 3.11-slim + FreeTDS + uvicorn |
| Railway | `railway.toml` → Dockerfile builder |
| Render | `render.yaml` → Python web service |

**Required Environment Variables:**
- `GROQ_API_KEY` — LLM API key
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — SQL Server
- `DATABASE_URL` — PostgreSQL (Neon) connection string
- `RECOMMENDATION_SERVICE_URL` — Recommendation service endpoint

---

## API Reference

### POST /chat
**Request:**
```json
{
  "user_id": "12345",
  "message": "عايز شقة مفروشة في القاهرة تحت 5000"
}
```

**Response:**
```json
{
  "reply": "🏠 لقيت 8 شقق مفروشة في القاهرة تحت ٥٠٠٠ جنيه:\n\n1️⃣ شقة في المعادي...",
  "response_type": "search_results",
  "results": [...],
  "suggestions": ["ورينى تاني", "أرخص سعر", "غرفة بدل شقة"],
  "total_count": 8,
  "filters": { "governorate": "Cairo", "max_price": 5000, ... }
}
```

### GET /debug/db-status
**Response:**
```json
{
  "property_db": "connected",
  "chatbot_db": "connected",
  "property_engine": "mssql",
  "chatbot_engine": "postgresql"
}
```
