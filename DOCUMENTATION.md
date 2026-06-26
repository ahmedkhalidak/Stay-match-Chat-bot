# StayMatch AI Service - Technical Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [NLP Architecture](#nlp-architecture)
5. [Database Schema](#database-schema)
6. [API Documentation](#api-documentation)
7. [Component Breakdown](#component-breakdown)
8. [Configuration](#configuration)
9. [Deployment](#deployment)
10. [Security](#security)
11. [Performance](#performance)
12. [Troubleshooting](#troubleshooting)

---

## Project Overview

### Purpose

StayMatch AI Service is a sophisticated backend service for the StayMatch housing platform. It provides an intelligent Arabic housing assistant that:

- Understands Egyptian Arabic housing requests using NLP
- Intelligently gathers missing information through conversation
- Searches for rooms, apartments, and shared accommodations
- Returns structured, frontend-ready responses
- Maintains conversation context across sessions
- Supports bilingual (Arabic/English) interactions

### Key Features

- **Multi-Language Support**: Native Egyptian Arabic with English keyword support
- **Hybrid NLP Engine**: Combines deterministic rule-based extraction with LLM fallback
- **Conversational AI**: Maintains context, asks clarifying questions, handles follow-ups
- **Smart Search**: Rooms, full apartments, shared apartments with advanced filtering
- **Location Intelligence**: Typo-tolerant matching across Egyptian governorates and cities
- **Structured Responses**: Clean JSON payloads with quick replies, result cards, pagination
- **PostgreSQL Integration**: Modern database layer with Neon PostgreSQL support
- **JWT Authentication**: Secure API access with token-based authentication
- **RAG FAQ System**: Retrieval-augmented generation for knowledge base queries

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Client                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/HTTPS
                              │ JWT Bearer Token
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Layer (routes.py)                   │  │
│  │  • POST /chat - Main conversation endpoint                 │  │
│  │  • GET /debug/db-status - Diagnostics                      │  │
│  │  • POST /admin/faq/reload - Admin operations               │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                         │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              SearchService (Orchestration)                │  │
│  │  • Message handling                                       │  │
│  │  • Intent routing                                         │  │
│  │  • Response coordination                                  │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                         │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                      │                                     │  │
│  ▼                      ▼                                     ▼  │
│ ┌──────────┐      ┌──────────┐                         ┌──────────┐│
│ │ NLPPipeline│     │Conversation│                        │Search    ││
│ │           │     │Flow        │                        │Executor  ││
│ └─────┬─────┘      └─────┬────┘                         └─────┬────┘│
│       │                 │                                      │    │
│       ▼                 ▼                                      ▼    │
│ ┌──────────┐      ┌──────────┐                         ┌──────────┐│
│ │Lexicon   │     │MemoryStore│                        │Repositories││
│ │Extractors│     │SessionCtx │                        │(Room/Prop)││
│ └──────────┘      └─────┬────┘                         └──────────┘│
│                        │                                         │
│                        ▼                                         │
│               ┌─────────────────┐                                │
│               │  PostgreSQL DB  │                                │
│               │  (Conversations)│                                │
│               └─────────────────┘                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              External Services                            │  │
│  │  • Groq API (LLM fallback)                                │  │
│  │  • Gemini API (FAQ answers)                              │  │
│  │  • Recommendation Service                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQL Server Database                          │
│              (Properties, Rooms, Listings)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
staymatch-ai-service/
├── app/
│   ├── api/                          # HTTP endpoints
│   │   └── routes.py                 # API route definitions
│   ├── core/                         # Core infrastructure
│   │   ├── config.py                 # Configuration management
│   │   ├── conversation_memory.py   # Conversation memory wrapper
│   │   ├── memory_store.py           # Session state management
│   │   ├── session_context.py        # Session context model
│   │   └── security.py               # JWT authentication
│   ├── database/                     # Database layer
│   │   ├── chatbot_connection.py     # PostgreSQL connection
│   │   ├── connection.py             # SQL Server connection
│   │   ├── chatbot_schema.sql        # PostgreSQL schema
│   │   └── repositories/             # Data access layer
│   │       ├── conversation_repository.py
│   │       ├── message_repository.py
│   │       ├── room_repository.py
│   │       ├── property_repository.py
│   │       ├── search_history_repository.py
│   │       ├── user_preferences_repository.py
│   │       └── session_analytics_repository.py
│   ├── data/                         # Static data
│   │   ├── knowledge_base.json        # FAQ knowledge base
│   │   └── locations.json            # Egyptian locations
│   ├── extractors/                   # NLP extractors
│   │   ├── price_extractor.py        # Price extraction
│   │   ├── followup_extractor.py     # Follow-up detection
│   │   └── query_extractor.py        # LLM-based extraction
│   ├── formatters/                   # Response formatting
│   │   └── response_formatter.py     # JSON response shaping
│   ├── models/                       # Data models
│   │   ├── chat_models.py            # Chat request/response models
│   │   ├── search_models.py          # Search filter models
│   │   └── response_models.py        # Response models
│   ├── nlp/                          # NLP pipeline
│   │   ├── nlp_pipeline.py           # Main NLP engine
│   │   ├── lexicon.py                # Arabic/English lexicons
│   │   ├── token_map.py              # Token mappings
│   │   └── parsed_message.py        # Parsed message model
│   ├── prompts/                      # LLM prompts
│   │   └── extraction_prompt.py      # Extraction prompts
│   ├── rag/                          # Retrieval-augmented generation
│   │   ├── vector_store.py           # ChromaDB vector store
│   │   └── faq_loader.py             # FAQ document loader
│   ├── services/                     # Business logic
│   │   ├── search_service.py         # Main search orchestration
│   │   ├── conversation_flow.py      # Dialogue state machine
│   │   ├── search_executor.py       # Search execution
│   │   ├── location_service.py      # Location matching
│   │   ├── faq_service.py            # FAQ answering
│   │   ├── gemini_faq_service.py     # Gemini FAQ integration
│   │   ├── chat_service.py           # Small talk handling
│   │   └── recommendation_client.py # Recommendation service
│   ├── utils/                        # Utilities
│   │   ├── text_normalizer.py        # Text normalization
│   │   ├── language_detector.py      # Language detection
│   │   ├── logger.py                 # Debug logging
│   │   └── bilingual_responses.py     # Bilingual responses
│   ├── validators/                   # Validation
│   │   └── filter_validator.py      # Filter validation
│   └── main.py                       # Application entry point
├── tests/                            # Test suite
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment template
├── Dockerfile                        # Container configuration
├── railway.toml                      # Railway deployment
├── render.yaml                       # Render deployment
└── README.md                         # User documentation
```

---

## Technology Stack

### Core Framework

- **Python**: 3.10+
- **FastAPI**: 0.115+ - Modern, fast web framework
- **Uvicorn**: 0.30.1+ - ASGI server
- **Pydantic**: 2.9.0+ - Data validation
- **Pydantic Settings**: 2.5.2+ - Configuration management

### Database & ORM

- **SQLAlchemy**: 2.0.35+ - SQL toolkit and ORM
- **psycopg2-binary**: 2.9.9+ - PostgreSQL adapter
- **pyodbc**: 5.3.0+ - SQL Server ODBC driver

### AI & Machine Learning

- **LangChain Core**: 1.0.0+ - LLM framework
- **LangChain Groq**: 1.0.0+ - Groq integration
- **Groq**: 0.37.0+ - Groq API client
- **Google Generative AI**: 0.8.0+ - Gemini API
- **Hugging Face Hub**: 0.16.4+ - Model hub
- **Sentence Transformers**: 2.2.0+ - Embedding models
- **ChromaDB**: 0.4.24+ - Vector database

### Authentication

- **PyJWT**: 2.8.0 - JWT token handling

### Configuration

- **python-dotenv**: 1.0.0+ - Environment variable management

### API Rate Limiting

- **slowapi**: 0.1.9+ - Rate limiting

### Databases

- **SQL Server**: Property and room listings
- **PostgreSQL (Neon)**: Chatbot conversations, messages, analytics

### External APIs

- **Groq API**: LLM fallback for complex queries
- **Gemini API**: FAQ answering with caching
- **Recommendation Service**: Property recommendations

---

## NLP Architecture

### Hybrid NLP Approach

The service uses a hybrid approach combining rule-based extraction with LLM fallback:

```
┌─────────────────────────────────────────────────────────┐
│                    User Message                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Text Normalization                          │
│  • Arabic normalization (أ→ا, ة→ه, etc.)               │
│  • Remove diacritics                                     │
│  • Remove extra whitespace                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Tokenization                                 │
│  • Word-level tokenization                               │
│  • Multi-word token recognition                          │
│  • Token mapping to canonical forms                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Rule-Based Extraction (Primary)                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ • Intent Detection (lexicon-based)              │    │
│  │ • Location Extraction (typo-tolerant)          │    │
│  │ • Price Extraction (pattern-based)              │    │
│  │ • Amenity Extraction (negation-aware)          │    │
│  │ • Housing Type Detection (priority-based)       │    │
│  │ • Tenant/Gender Detection                       │    │
│  │ • Sort Order Detection                          │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
              Confidence Score
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
   Confidence ≥ 0.65         Confidence < 0.65
        │                         │
        ▼                         ▼
┌───────────────┐      ┌───────────────────┐
│  Use Rules    │      │   LLM Fallback     │
│  (Fast)       │      │   (Groq API)       │
└───────────────┘      └─────────┬─────────┘
                                 │
                                 ▼
                        ┌───────────────────┐
                        │  Merge Results    │
                        │  with Rules       │
                        └─────────┬─────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │  Filter Validation│
                        │  & Consistency    │
                        └─────────┬─────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │  Search Filters   │
                        └───────────────────┘
```

### NLP Pipeline Components

#### 1. Text Normalization

**Location**: `app/utils/text_normalizer.py`

**Purpose**: Normalize Arabic text for consistent processing

**Operations**:
- Arabic letter normalization (أ→ا, ة→ه, etc.)
- Remove diacritics (fatha, kasra, damma, etc.)
- Remove extra whitespace
- Lowercase conversion for English

**Example**:
```python
Input: "عايز أوضة في المعادي"
Output: "عايز اوضة في المعادي"
```

#### 2. Tokenization

**Location**: `app/nlp/nlp_pipeline.py::_tokenize()`

**Purpose**: Split text into tokens with multi-word recognition

**Features**:
- Word-level tokenization
- Multi-word token recognition (e.g., "private room")
- Token mapping to canonical forms

**Example**:
```python
Input: "private room in maadi"
Tokens: ["private_room", "in", "maadi"]
```

#### 3. Intent Detection

**Location**: `app/nlp/nlp_pipeline.py::_detect_intent()`

**Purpose**: Determine user intent from message

**Supported Intents**:
- `room_search`: User wants to search for rooms
- `property_search`: User wants to search for properties/apartments
- `follow_up`: User is refining previous search
- `clarification`: User is answering a clarification question
- `show_more`: User wants more results
- `go_back`: User wants to return to previous search
- `small_talk`: Greeting, thanks, goodbye
- `faq`: User is asking a question
- `invalid`: Unable to determine intent

**Detection Method**: Lexicon-based keyword matching with confidence scoring

**Priority Rules**:
- FAQ intent boosted when action keywords present
- Room search prioritized over property search when room nouns present

#### 4. Location Extraction

**Location**: `app/nlp/nlp_pipeline.py::_extract_location()`

**Purpose**: Extract and normalize location information

**Features**:
- Typo-tolerant matching using fuzzy search
- Support for governorates and cities
- Location replacement detection ("بدل" pattern)
- Inheritance from previous search

**Location Data**: `app/data/locations.json`

**Coverage**: All Egyptian governorates and major cities

**Example**:
```python
Input: "في المعادي"
Output: {"type": "city", "en": "Maadi", "confidence": 0.9}

Input: "في الاسكندرية بدل المعادي"
Output: {"type": "city", "en": "Alexandria", "confidence": 0.9}
```

#### 5. Price Extraction

**Location**: `app/nlp/nlp_pipeline.py::_extract_price()`

**Purpose**: Extract price range from message

**Extractor**: `app/extractors/price_extractor.py`

**Patterns Supported**:
- "تحت 5000" → max_price: 5000
- "فوق 3000" → min_price: 3000
- "من 2000 لـ 5000" → min_price: 2000, max_price: 5000
- "5000" → exact price (treated as max)

**Example**:
```python
Input: "تحت 5000"
Output: {"min_price": null, "max_price": 5000}
```

#### 6. Amenity Extraction

**Location**: `app/nlp/nlp_pipeline.py::_extract_amenities()`

**Purpose**: Extract amenity preferences with negation handling

**Supported Amenities**:
- `wifi`: Internet availability
- `furnished`: Furniture status
- `air_conditioning`: AC availability
- `balcony`: Balcony presence
- `private_bathroom`: Private bathroom
- `kitchen`: Kitchen access
- `washer`: Washing machine
- `refrigerator`: Refrigerator

**Negation Handling**: Context-aware negation detection

**Example**:
```python
Input: "فيها واي فاي"
Output: {"wifi": true}

Input: "مش عايز واي فاي"
Output: {"wifi": false}
```

#### 7. Housing Type Detection

**Location**: `app/nlp/nlp_pipeline.py::_extract_housing_type()`

**Purpose**: Determine housing type with priority-based resolution

**Priority Order**: shared > room > apartment

**Housing Types**:
- `apartment`: Full apartment, private
- `room`: Private room in shared apartment
- `shared`: Shared apartment/roommate situation
- `any`: No preference

**Priority Rules**:
- Shared keywords override apartment keywords
- Room keywords override apartment keywords
- Prevents conflicting states

**Example**:
```python
Input: "شقة مشتركة"
Output: "shared" (not "apartment")

Input: "غرفة مشتركة"
Output: "shared" (not "room")
```

#### 8. Tenant & Gender Detection

**Location**: `app/nlp/nlp_pipeline.py::_extract_tenant_and_gender()`

**Purpose**: Extract tenant type and gender preferences

**Tenant Types**:
- `student`: Students only
- `worker`: Workers/employees only

**Genders**:
- `male`: Males only
- `female`: Females only

**Example**:
```python
Input: "للطلاب"
Output: {"tenant_type": "student"}

Input: "للبنات"
Output: {"gender": "female"}
```

#### 9. Sort Order Detection

**Location**: `app/nlp/nlp_pipeline.py::_extract_sort()`

**Purpose**: Extract sort preference

**Sort Options**:
- `price_low`: Sort by lowest price
- `price_high`: Sort by highest price
- `relevance`: Default relevance sorting

**Example**:
```python
Input: "ارخص"
Output: {"sort_by": "price_low"}
```

#### 10. LLM Fallback

**Location**: `app/nlp/nlp_pipeline.py::_llm_fallback()`

**Purpose**: Use LLM when rule-based confidence is low

**Trigger**: Overall confidence < 0.65

**LLM Service**: Groq API via LangChain

**Extractor**: `app/extractors/query_extractor.py`

**Fallback Strategy**:
- Only call LLM when rules insufficient
- Merge LLM results with rule-based results
- Prioritize rule-based extractions over LLM
- Boost confidence after LLM fallback

**Example**:
```python
Rule Confidence: 0.45
→ Call LLM Fallback
→ Merge Results
→ Final Confidence: 0.75
```

### Lexicon Structure

**Location**: `app/nlp/lexicon.py`

**Purpose**: Comprehensive Arabic/English keyword dictionaries

#### Intent Keywords

```python
INTENT_KEYWORDS = {
    "room_search": [
        "غرفه", "غرفة", "غرف", "اوضة", "اوضه",
        "room", "rooms", "bedroom", "studio",
        "سنجل", "single", "خاص", "private", "فردي",
    ],
    "property_search": [
        "شقه", "شقة", "شقق", "سكن",
        "apartment", "flat", "property", "house", "home",
        "villa", "منزل", "عقار", "وحده", "عماره", "مبني",
    ],
    # ... more intents
}
```

#### Housing Type Keywords

```python
HOUSING_TYPE_KEYWORDS = {
    "apartment": [
        "شقة", "شقه", "شقق",
        "apartment", "flat", "apartments", "flats",
        "كاملة", "كامله", "full",
        "وحدة", "وحده", "عقار", "منزل",
        "house", "home", "villa",
    ],
    "room": [
        "اوضة", "اوضه", "غرفة", "غرفه", "غرف",
        "room", "rooms", "bedroom", "studio",
        "سنجل", "single", "خاص", "private", "فردي",
    ],
    "shared": [
        "مشترك", "مشتركة", "مشتركه",
        "shared", "roommate", "roommates",
        "مع ناس", "مع حد", "سكن مشترك",
        "شقه مشتركه", "شقة مشتركة",
        "shared apartment", "shared flat",
    ],
}
```

#### Amenity Keywords

```python
AMENITY_KEYWORDS = {
    "wifi": ["wifi", "wi-fi", "واي", "انترنت", "نت", "internet", "net"],
    "furnished": ["مفروش", "furnished", "furniture"],
    "air_conditioning": ["مكيف", "تكييف", "ac", "air conditioning", "aircon"],
    "balcony": ["بلكونه", "balcony", "balconies", "terrace"],
    "private_bathroom": ["حمام_خاص", "private_bathroom", "ensuite"],
    # ... more amenities
}
```

### Conversation Memory

#### MemoryStore Architecture

**Location**: `app/core/memory_store.py`

**Purpose**: Consolidated session state management with database persistence

**Features**:
- In-memory session storage (fast access)
- PostgreSQL persistence (durable storage)
- Async fire-and-forget database writes
- Session reconstruction from database
- Automatic session eviction (max 1000 sessions)
- Retry logic for database operations

**Data Flow**:
```
User Message
    ↓
MemoryStore.get_context()
    ↓
Check In-Memory Cache
    ↓
If not found → Reconstruct from PostgreSQL
    ↓
Create new session if needed
    ↓
Update context
    ↓
Fire-and-forget DB sync (async)
```

**Session Context Model**:

```python
class SessionContext:
    language: str  # "ar" or "en"
    user_id: str
    conversation_history: List[MessageTurn]
    pending_slot: str  # Current clarification needed
    current_offset: int  # Pagination offset
    page_size: int  # Results per page
    last_search: SearchFilters  # Previous search filters
    user_preferences: UserPreferences  # User's saved preferences
    skipped_slots: Set[str]  # Slots user skipped
    no_results_count: int  # Track consecutive no-results
    total_searches: int  # Total searches in session
```

**Database Persistence**:

Tables used:
- `conversations`: Session metadata
- `messages`: Message history
- `user_preferences`: User preferences
- `search_history`: Search analytics
- `session_analytics`: Session statistics

**Retry Logic**:
- 3 retry attempts with exponential backoff
- 5-second timeout per attempt
- Background thread execution (non-blocking)

---

## Database Schema

### PostgreSQL Schema (Chatbot)

**Location**: `app/database/chatbot_schema.sql`

#### Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB
);
```

**Purpose**: Store conversation sessions and metadata

**Indexes**:
- `idx_conversations_session_id`: Fast session lookup
- `idx_conversations_user_id`: User's conversations
- `idx_conversations_last_activity`: Active session tracking

**Metadata Structure**:
```json
{
  "language": "ar",
  "pending_slot": "location",
  "current_offset": 0,
  "page_size": 5,
  "last_search": {...},
  "user_preferences": {...},
  "skipped_slots": [],
  "no_results_count": 0,
  "total_searches": 3
}
```

#### Messages Table

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(50) DEFAULT 'text',
    metadata JSONB,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

**Purpose**: Store individual messages in conversations

**Roles**: `user`, `assistant`, `system`

**Indexes**:
- `idx_messages_conversation_id`: Message retrieval
- `idx_messages_created_at`: Temporal queries
- `idx_messages_role`: Role-based filtering

#### User Preferences Table

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    min_budget DECIMAL(10, 2),
    max_budget DECIMAL(10, 2),
    preferred_location VARCHAR(255),
    tenant_type VARCHAR(50),
    gender VARCHAR(50),
    furnished BOOLEAN,
    wifi BOOLEAN,
    air_conditioning BOOLEAN,
    balcony BOOLEAN,
    private_bathroom BOOLEAN,
    shared_room BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Store user preferences for personalization

**Trigger**: Auto-update `updated_at` on modification

#### Search History Table

```sql
CREATE TABLE search_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    search_type VARCHAR(50),
    city VARCHAR(255),
    governorate VARCHAR(255),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filters JSONB
);
```

**Purpose**: Track search queries for analytics

**Indexes**:
- `idx_search_history_session_id`: Session searches
- `idx_search_history_user_id`: User search history
- `idx_search_history_created_at`: Temporal analytics

#### Session Analytics Table

```sql
CREATE TABLE session_analytics (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    total_searches INTEGER DEFAULT 0,
    no_results_count INTEGER DEFAULT 0,
    avg_response_time DECIMAL(10, 2)
);
```

**Purpose**: Aggregate session statistics

**Indexes**:
- `idx_session_analytics_session_id`: Session lookup
- `idx_session_analytics_user_id`: User analytics

### SQL Server Schema (Properties)

**Purpose**: Store property and room listings

**Note**: Schema managed separately in main database

**Key Tables** (inferred from repositories):
- Properties/Apartments
- Rooms
- Amenities
- Locations

---

## API Documentation

### Authentication

All endpoints require JWT Bearer token authentication.

**Header**:
```
Authorization: Bearer <jwt_token>
```

**JWT Configuration** (Environment Variables):
- `JWT_SECRET`: Secret key for token signing
- `JWT_ISSUER`: Token issuer
- `JWT_AUDIENCE`: Expected audience

### Endpoints

#### POST /chat

Process a user message and return a structured response.

**Request Body**:
```json
{
  "session_id": "user-123",
  "message": "عايز أوضة في المعادي تحت 5000"
}
```

**Response Body**:
```json
{
  "reply": "لقيت 2 أوضة في Maadi.",
  "response_type": "results",
  "pending_slot": null,
  "filters": {
    "intent": "room_search",
    "search_type": "room",
    "housing_type": "room",
    "city": "Maadi",
    "governorate": null,
    "min_price": null,
    "max_price": 5000,
    "tenant_type": null,
    "furnished": null,
    "wifi": null,
    "private_bathroom": null,
    "balcony": null,
    "air_conditioning": null,
    "gender": null,
    "shared_room": null,
    "sort_by": "relevance"
  },
  "suggestions": [
    {
      "label": "المزيد",
      "value": "المزيد"
    }
  ],
  "results": [
    {
      "id": 1,
      "result_type": "room",
      "title": "Room 1",
      "subtitle": "Property name",
      "location": "Maadi، Cairo",
      "price_text": "4,200 جنيه/شهر",
      "monthly_rent": 4200,
      "deposit": 1000,
      "details": [
        "سنجل",
        "حد أدنى 3 شهر"
      ],
      "amenities": [
        "مفروشة",
        "واي فاي"
      ],
      "attributes": {
        "capacity": 1,
        "capacity_available": 1,
        "furnished": true,
        "shared_room": false
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 5,
    "has_more": false
  }
}
```

**Response Types**:

| Type | Description |
|------|-------------|
| `clarification` | Bot needs more information |
| `results` | Search completed with results |
| `no_results` | Search completed but no matches |
| `end_of_results` | User requested more after final page |
| `small_talk` | Greeting, thanks, or goodbye |
| `faq` | Answer from knowledge base |
| `fallback` | Unsupported or unrelated request |

#### GET /debug/db-status

Debug endpoint to check database connection status.

**Response**:
```json
{
  "property_db": "connected",
  "chatbot_db": "connected",
  "property_engine": "mssql",
  "chatbot_engine": "postgresql"
}
```

#### POST /admin/faq/reload

Reload knowledge_base.json without restarting the service.

**Response**:
```json
{
  "status": "success",
  "message": "Knowledge base reloaded successfully"
}
```

#### GET /admin/faq/stats

Get FAQ service statistics.

**Response**:
```json
{
  "total_questions": 150,
  "cached_answers": 45,
  "rag_enabled": true,
  "gemini_enabled": true
}
```

---

## Component Breakdown

### SearchService

**Location**: `app/services/search_service.py`

**Purpose**: Main orchestration layer for message handling

**Responsibilities**:
- Message routing and intent handling
- NLP pipeline coordination
- Conversation flow management
- Response generation
- Background database persistence

**Key Methods**:
- `handle_message()`: Main message processing
- `_shortcut_response()`: Handle predefined commands
- `_handle_show_more()`: Pagination handling
- `_handle_go_back()`: Back navigation
- `_bg_save()`: Background database persistence

**Flow**:
```
Message → Language Detection → Context Retrieval → 
Shortcut Check → NLP Extraction → Intent Routing → 
Flow Application → Search Execution → Response Generation → 
Background Save
```

### ConversationFlow

**Location**: `app/services/conversation_flow.py`

**Purpose**: Dialogue state machine for conversation management

**Responsibilities**:
- Determine next clarification question
- Apply user preferences to filters
- Handle slot filling
- Manage conversation state transitions

**Key Methods**:
- `get_next_clarification()`: Determine what to ask next
- `apply_preferences_to_filters()`: Apply saved preferences
- `apply_user_overrides()`: Handle explicit user overrides
- `get_slot_suggestions()`: Generate quick reply suggestions

**Clarification Slots**:
- `location`: Ask for location
- `price`: Ask for budget
- `housing_type`: Ask for apartment/room/shared
- `furnished`: Ask about furniture
- `tenant_type`: Ask about student/worker

### SearchExecutor

**Location**: `app/services/search_executor.py`

**Purpose**: Execute database searches and format results

**Responsibilities**:
- Database query execution
- Pagination management
- Result formatting
- Recommendation integration

**Key Methods**:
- `execute()`: Main search execution
- `_search_rooms()`: Room search
- `_search_properties()`: Property search
- `_format_results()`: Result formatting

### LocationService

**Location**: `app/services/location_service.py`

**Purpose**: Typo-tolerant location matching

**Features**:
- Fuzzy string matching
- Governorate and city detection
- Arabic/English location names
- Location normalization

**Data Source**: `app/data/locations.json`

### FaqService

**Location**: `app/services/faq_service.py`

**Purpose**: Answer FAQ questions using RAG and Gemini

**Architecture**:
```
Question → RAG (ChromaDB) → Match Found?
    ↓ No                ↓ Yes
Gemini API          Return Answer
    ↓
Return Answer
```

**Features**:
- ChromaDB vector search (if enabled)
- Gemini API fallback
- Answer caching
- Daily rate limiting
- Bilingual support

**Configuration**:
- `enable_gemini_faq`: Enable/disable Gemini
- `gemini_daily_limit`: Daily API call limit
- `gemini_cache_ttl_seconds`: Cache duration
- `gemini_max_tokens`: Max response tokens

### VectorStore (RAG)

**Location**: `app/rag/vector_store.py`

**Purpose**: ChromaDB-based FAQ retrieval

**Embedding Model**: `intfloat/multilingual-e5-small`

**Features**:
- Persistent vector storage
- Automatic cache recovery
- Adaptive similarity threshold
- Background initialization
- Telemetry disabled

**Configuration**:
- `ENABLE_RAG_EMBEDDINGS`: Enable/disable RAG
- `CHROMA_PATH`: Storage path (`/tmp/chromadb_staymatch`)

**Query Flow**:
```
Question → Embed → Vector Search → 
Similarity Check → Threshold Match → Return Answer
```

### MemoryStore

**Location**: `app/core/memory_store.py`

**Purpose**: Session state management with persistence

**Features**:
- In-memory cache (fast)
- PostgreSQL persistence (durable)
- Async fire-and-forget writes
- Session reconstruction
- Automatic eviction
- Retry logic

**Key Methods**:
- `get_context()`: Get or create session context
- `update_context()`: Update session state
- `store_message()`: Store message with persistence
- `record_search()`: Record search analytics
- `clear_context()`: Clear session

### NLPPipeline

**Location**: `app/nlp/nlp_pipeline.py`

**Purpose**: Main NLP processing engine

**Confidence Threshold**: 0.65

**Processing Steps**:
1. Text normalization
2. Tokenization
3. Intent detection
4. Location extraction
5. Price extraction
6. Amenity extraction
7. Tenant/gender extraction
8. Housing type detection
9. Sort order detection
10. Confidence calculation
11. LLM fallback (if needed)
12. Filter merging
13. Validation

---

## Configuration

### Environment Variables

**Required Variables**:

```env
# Groq API (LLM fallback)
GROQ_API_KEY=your_groq_api_key_here

# SQL Server Database (Properties)
DB_HOST=localhost
DB_PORT=1433
DB_NAME=staymatch_backend_db
DB_USER=sa
DB_PASSWORD=your_password_here

# JWT Authentication
JWT_SECRET=your_jwt_secret
JWT_ISSUER=your-app
JWT_AUDIENCE=your-users
```

**Optional Variables**:

```env
# PostgreSQL Database (Chatbot - Recommended)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Legacy SQL Server for Chatbot (Deprecated)
CHATBOT_DB_HOST=localhost
CHATBOT_DB_PORT=1433
CHATBOT_DB_NAME=staymatch_chatbot_db
CHATBOT_DB_USER=sa
CHATBOT_DB_PASSWORD=your_password_here

# Gemini FAQ
GEMINI_API_KEY=your_gemini_api_key
enable_gemini_faq=true
gemini_daily_limit=1000
gemini_cache_ttl_seconds=3600

# RAG Embeddings
ENABLE_RAG_EMBEDDINGS=true

# Debug Mode
DEBUG_LOGS=1

# Recommendation Service
recommendation_service_url=http://recommendation-service:8000
```

### Configuration Class

**Location**: `app/core/config.py`

**Settings Class**:
```python
class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str | None = None
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    database_url: str | None = None
    jwt_secret: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = ""
    enable_gemini_faq: bool = True
    gemini_daily_limit: int = 1000
    # ... more settings
```

---

## Deployment

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run**:
```bash
docker build -t staymatch-ai-service .
docker run -p 8000:8000 --env-file .env staymatch-ai-service
```

### Platform-Specific Deployment

**Railway** (`railway.toml`):
- Automatic deployment from Git
- PostgreSQL database included
- Environment variables configured

**Render** (`render.yaml`):
- PaaS deployment
- PostgreSQL add-on
- Automatic SSL

**Nixpacks** (`nixpacks.toml`):
- Containerized deployment
- Automatic dependency detection

### Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Database accessible from deployment environment
- [ ] SSL/TLS enabled for database connections
- [ ] Debug logs disabled in production
- [ ] JWT secret properly configured
- [ ] API keys for Groq and Gemini set
- [ ] Frontend uses structured response fields
- [ ] Rate limiting configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy in place

---

## Security

### Authentication

- **JWT Bearer Tokens**: Required for all endpoints
- **Token Validation**: Signature, issuer, audience verification
- **User Context**: Extracted from token for personalization

### Data Protection

- **Environment Variables**: Sensitive data in `.env` (never committed)
- **Database Encryption**: SSL/TLS for PostgreSQL connections
- **API Key Security**: Never logged or exposed in responses

### Rate Limiting

- **slowapi**: Rate limiting middleware
- **Configurable Limits**: Per-endpoint rate limits
- **Prevent Abuse**: Protect against API abuse

### Best Practices

- Never commit `.env` files or API keys
- Use strong JWT secrets
- Rotate API keys regularly
- Enable SSL/TLS for all database connections
- Monitor for suspicious activity
- Keep dependencies updated
- Implement proper error handling (no stack traces in production)

---

## Performance

### Optimization Strategies

1. **Connection Pooling**: Database connection reuse
2. **Caching**: FAQ answers, user preferences
3. **Async Operations**: Non-blocking database writes
4. **In-Memory Cache**: Session state management
5. **Pagination**: Limit result sets
6. **Indexing**: Database query optimization

### Monitoring

- **Response Time Tracking**: Per-request timing
- **Database Query Performance**: Slow query logging
- **LLM API Usage**: Token and cost tracking
- **Session Analytics**: User behavior insights

### Scalability

- **Stateless API**: Horizontal scaling possible
- **Database Connection Pooling**: Handle high concurrency
- **Async Processing**: Non-blocking I/O
- **Session Eviction**: Prevent memory leaks

---

## Troubleshooting

### Common Issues

#### Application won't start

**Error**: `ValidationError: database_url Input should be a valid string`

**Solution**: Set `DATABASE_URL` environment variable or use legacy `CHATBOT_DB_*` variables.

#### Database connection failed

**Error**: `Could not connect to database`

**Solution**:
- Verify database is running
- Check connection string format
- Ensure firewall allows connection
- Verify SSL settings for PostgreSQL

#### LLM fallback not working

**Error**: `Groq API error`

**Solution**:
- Verify `GROQ_API_KEY` is set
- Check API key is valid
- Ensure network allows API access
- Monitor API quota limits

#### Location matching fails

**Issue**: Typos not resolved

**Solution**:
- Check `app/data/locations.json` is present
- Verify location data is complete
- Enable debug logs to see matching process

### Debug Mode

Enable verbose logging:

```env
DEBUG_LOGS=1
```

This shows detailed NLP traces for troubleshooting.

### Log Analysis

**Debug Log Categories**:
- `PIPELINE_START`: NLP pipeline start
- `NORMALIZED`: Normalized text
- `TOKENS`: Tokenized output
- `INTENT`: Detected intent
- `LOCATION`: Location extraction
- `PRICE`: Price extraction
- `AMENITIES`: Amenity extraction
- `CONFIDENCE`: Confidence scores
- `LLM_FALLBACK`: LLM fallback calls
- `RESPONSE_TIMING`: Response time metrics

---

## Appendix

### Supported Housing Types

- **Room**: Private room in shared apartment
- **Apartment**: Full private apartment
- **Shared**: Shared apartment/roommate situation

### Supported Amenities

- WiFi
- Furnished
- Air Conditioning
- Balcony
- Private Bathroom
- Kitchen
- Washer
- Refrigerator

### Supported Locations

All Egyptian governorates and major cities, including:
- Cairo (Maadi, Nasr City, Zamalek, etc.)
- Alexandria
- Giza
- Dakahlia
- Sharqia
- Monufia
- Qalyubia
- ... and more

### Follow-Up Commands

| Command | Effect |
|---------|--------|
| `أرخص` | Sort by lowest price |
| `هات الأعلى سعراً` | Sort by highest price |
| `فيها واي فاي` | Add WiFi filter |
| `مش عايز واي فاي` | Set WiFi to false |
| `غير مفروشة` | Set furnished to false |
| `للطلاب` | Tenant type = student |
| `في اسكندرية بدل المعادي` | Replace location, keep filters |
| `المزيد` | Load next page |
| `ارجع` | Return to previous search |

### Response Language Support

- **Arabic**: Native Egyptian Arabic
- **English**: Keyword support, some responses
- **Auto-detection**: Language detected from user message

---

**Document Version**: 1.0  
**Last Updated**: June 2026  
**Project**: StayMatch AI Service  
**License**: MIT
