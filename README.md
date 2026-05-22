# StayMatch AI Service

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**An intelligent Arabic housing assistant powered by NLP and LLM**

</div>

---

## Overview

StayMatch AI Service is a sophisticated backend service for the StayMatch housing platform. It understands Egyptian Arabic housing requests, intelligently gathers missing information through conversation, searches for rooms or apartments, and returns structured, frontend-ready responses.

### Key Features

- **🌍 Multi-Language Support**: Native Egyptian Arabic with English keyword support
- **🧠 Hybrid NLP Engine**: Combines deterministic rule-based extraction with LLM fallback for optimal performance
- **💬 Conversational AI**: Maintains context, asks clarifying questions, and handles follow-up queries
- **🔍 Smart Search**: Supports rooms, full apartments, and shared apartments with advanced filtering
- **📍 Location Intelligence**: Typo-tolerant matching across Egyptian governorates and cities
- **📊 Structured Responses**: Clean JSON payloads with quick replies, result cards, and pagination
- **🗄️ PostgreSQL Integration**: Modern database layer with Neon PostgreSQL support

---

## Table of Contents

- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Supported Features](#supported-features)
- [API Documentation](#api-documentation)
- [Frontend Integration](#frontend-integration)
- [Installation](#installation)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Database Migration](#database-migration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture

### System Architecture

```mermaid
graph TD
    A[User Message] --> B[FastAPI /chat Endpoint]
    B --> C[SearchService]
    C --> D[NLPPipeline]
    D --> E[TextNormalizer]
    D --> F[NLP Lexicon]
    D --> G[Rule-Based Extraction]
    D --> H[LLM Fallback]
    D --> I[FilterValidator]
    C --> J[ConversationFlow]
    C --> K[SearchExecutor]
    K --> L[Repositories]
    K --> M[ResponseFormatter]
    B --> N[ChatResponse JSON]
```

### Module Structure

| Module | Description | File |
|--------|-------------|------|
| **API Layer** | HTTP endpoints and request handling | `app/api/routes.py` |
| **Orchestration** | Main service coordination | `app/services/search_service.py` |
| **Search Execution** | Database queries and pagination | `app/services/search_executor.py` |
| **Conversation Flow** | State machine for dialogue | `app/services/conversation_flow.py` |
| **NLP Pipeline** | Natural language processing | `app/nlp/nlp_pipeline.py` |
| **NLP Vocabulary** | Token dictionaries and lexicons | `app/nlp/lexicon.py` |
| **Location Service** | Geographic matching | `app/services/location_service.py` |
| **Response Formatter** | JSON response shaping | `app/formatters/response_formatter.py` |
| **Session Context** | In-memory conversation state | `app/core/session_context.py` |
| **Memory Store** | Persistent conversation storage | `app/core/memory_store.py` |
| **Conversation Memory** | Database-backed memory | `app/core/conversation_memory.py` |
| **Room Repository** | Room data access | `app/database/repositories/room_repository.py` |
| **Property Repository** | Property data access | `app/database/repositories/property_repository.py` |
| **Conversation Repository** | Chat conversation storage | `app/database/repositories/conversation_repository.py` |
| **Message Repository** | Chat message storage | `app/database/repositories/message_repository.py` |

---

## How It Works

### Conversation Flow

The search flow is designed to be concise and natural:

1. **Initial Request**: User states housing type (e.g., "عايز أوضة")
2. **Location Clarification**: Bot asks for location if missing
3. **Budget Inquiry**: Bot asks for budget if useful
4. **Search Execution**: Bot searches and returns results
5. **Refinement**: User can refine with follow-ups

### Example Conversation

```
User: عايز أوضة
Bot: تمام، تحب تدور فين؟

User: في المعادي
Bot: ميزانيتك الشهرية تقريباً كام؟

User: تحت 5000
Bot: لقيت 2 أوضة في Maadi.
```

### NLP Strategy

The service uses a hybrid approach:

1. **Rule-Based Extraction** (Fast, deterministic)
   - Text normalization and tokenization
   - Intent and entity extraction using lexicons
   - Filter validation and normalization

2. **LLM Fallback** (When confidence is low)
   - Groq API for complex queries
   - Structured extraction from unstructured input
   - Fallback only when needed for cost efficiency

---

## Supported Features

### Housing Types

- **Room** - Individual rooms in shared apartments
- **Property** - Full apartments
- **Full** - Complete apartments
- **Shared** - Shared apartment options

### Search Filters

| Filter | Type | Description |
|--------|------|-------------|
| City / Governorate | Location | Geographic filtering |
| Min Price | Numeric | Minimum monthly rent |
| Max Price | Numeric | Maximum monthly rent |
| Tenant Type | Enum | Student / Worker |
| Furnished | Boolean | Furniture status |
| WiFi | Boolean | Internet availability |
| Balcony | Boolean | Balcony presence |
| Air Conditioning | Boolean | AC availability |
| Private Bathroom | Boolean | Private bath |
| Gender | Enum | Gender preference |
| Shared Room | Boolean | Room sharing |
| Sort Order | Enum | Relevance / Lowest / Highest |

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

---

## API Documentation

### POST /chat

Process a user message and return a structured response.

#### Request Body

```json
{
  "session_id": "user-123",
  "message": "عايز أوضة في المعادي تحت 5000"
}
```

#### Response Body

```json
{
  "reply": "لقيت 2 أوضة في Maadi.",
  "response_type": "results",
  "pending_slot": null,
  "filters": {
    "intent": "room_search",
    "search_type": "room",
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

#### Response Types

| Type | Description |
|------|-------------|
| `clarification` | Bot needs more information (location, price, etc.) |
| `results` | Search completed with results |
| `no_results` | Search completed but no matches found |
| `end_of_results` | User requested more after final page |
| `small_talk` | Greeting, thanks, or goodbye |
| `faq` | Answer from knowledge base |
| `fallback` | Unsupported or unrelated request |

---

## Frontend Integration

### Implementation Guidelines

1. **Message Display**: Render `reply` as the assistant message
2. **State Management**: Use `response_type` to determine UI state
3. **Quick Replies**: Render `suggestions` as chips or buttons
4. **Result Cards**: Display `results` as structured cards (don't parse text)
5. **Context Tracking**: Use `pending_slot` to understand what's needed
6. **Pagination**: Show/hide "المزيد" based on `pagination.has_more`
7. **Session Continuity**: Maintain `session_id` across conversation

### Example Integration

```javascript
// Handle chat response
async function handleChatResponse(response) {
  // Display assistant message
  displayMessage(response.reply);
  
  // Handle response type
  switch (response.response_type) {
    case 'results':
      displayResults(response.results);
      break;
    case 'clarification':
      highlightPendingSlot(response.pending_slot);
      break;
    // ... other cases
  }
  
  // Show quick replies
  if (response.suggestions) {
    displaySuggestions(response.suggestions);
  }
  
  // Handle pagination
  if (response.pagination?.has_more) {
    showLoadMoreButton();
  }
}
```

---

## Installation

### Prerequisites

- **Python**: 3.10 or higher
- **Database**: SQL Server (for properties) or PostgreSQL (for chatbot)
- **API Key**: Groq API key for LLM features

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/staymatch-ai-service.git
cd staymatch-ai-service
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create a `.env` file in the project root:

```env
# Groq API
GROQ_API_KEY=your_groq_api_key_here

# Backend Database (Properties, Rooms) - SQL Server
DB_HOST=localhost
DB_PORT=1433
DB_NAME=staymatch_backend_db
DB_USER=sa
DB_PASSWORD=your_password_here

# Chatbot Database (Conversations, Messages) - PostgreSQL (Neon)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Optional: Legacy SQL Server for chatbot (deprecated)
CHATBOT_DB_HOST=localhost
CHATBOT_DB_PORT=1433
CHATBOT_DB_NAME=staymatch_chatbot_db
CHATBOT_DB_USER=sa
CHATBOT_DB_PASSWORD=your_password_here

# Optional: Debug Mode
DEBUG_LOGS=0
```

### Step 5: Initialize Database

Run the schema scripts:

```bash
# For PostgreSQL chatbot database
psql -h host -U user -d database -f app/database/chatbot_schema.sql
```

### Step 6: Run Development Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access API documentation at: `http://localhost:8000/docs`

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM features |
| `DB_HOST` | Yes | SQL Server host for properties |
| `DB_PORT` | Yes | SQL Server port |
| `DB_NAME` | Yes | SQL Server database name |
| `DB_USER` | Yes | SQL Server username |
| `DB_PASSWORD` | Yes | SQL Server password |
| `DATABASE_URL` | No | PostgreSQL URL for chatbot (recommended) |
| `CHATBOT_DB_*` | No | Legacy SQL Server for chatbot (deprecated) |
| `DEBUG_LOGS` | No | Enable verbose NLP traces (0 or 1) |

### Database Configuration

#### Backend Database (SQL Server)

Stores property and room listings. Schema defined in the main database.

#### Chatbot Database (PostgreSQL - Neon)

Stores conversations, messages, user preferences, search history, and analytics.

**Recommended**: Use Neon PostgreSQL for serverless, scalable chatbot storage.

**Legacy**: SQL Server support maintained for backward compatibility.

---

## Development

### Project Structure

```
staymatch-ai-service/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Configuration and utilities
│   ├── database/         # Database connections and repositories
│   ├── data/             # Static data files
│   ├── extractors/       # NLP extractors
│   ├── formatters/       # Response formatters
│   ├── models/           # Data models
│   ├── nlp/              # NLP pipeline and lexicons
│   ├── prompts/          # LLM prompts
│   ├── rag/              # Retrieval-augmented generation
│   ├── ranking/          # Result ranking
│   ├── services/         # Business logic
│   ├── utils/            # Utility functions
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── Dockerfile           # Container configuration
└── README.md            # This file
```

### Running Tests

```bash
# Run all tests
python -m unittest discover -s tests -v

# Run specific test file
python -m unittest tests.test_nlp_pipeline -v

# Run with coverage
pip install pytest-cov
pytest --cov=app tests/
```

### Code Quality

```bash
# Compile check
python -m compileall app tests

# Type checking (if using mypy)
pip install mypy
mypy app/
```

---

## Testing

### Automated Test Coverage

The test suite covers:

- ✅ Room and apartment searches
- ✅ PDF regression scenarios
- ✅ Typo-tolerant location matching
- ✅ Price filters and sort orders
- ✅ Amenities and negated amenities
- ✅ Room vs shared apartment distinction
- ✅ Follow-up memory behavior
- ✅ Skip answers (`أي مكان`, `أي سعر`)
- ✅ Pagination and `المزيد`
- ✅ Back navigation
- ✅ No-results responses
- ✅ FAQ, small talk, and invalid requests
- ✅ Frontend response shape
- ✅ PostgreSQL database operations

### Manual Smoke Test

Test these scenarios with a working database:

```
عايز اوضة في المعادي تحت 5000
فيها واي فاي

عايز شقة كاملة في المعادي تحت 10000

عايز اوضة في السمعيلية
```

**Expected behavior**:
- Valid searches → `results` response
- Empty searches → `no_results` response
- Incomplete searches → `clarification` response
- Typos → Still resolve correctly

---

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t staymatch-ai-service .

# Run container
docker run -p 8000:8000 \
  --env-file .env \
  staymatch-ai-service
```

### Platform-Specific Deployment

The repository includes configuration for:

- **Render**: `render.yaml`
- **Railway**: `railway.toml`
- **Nixpacks**: `nixpacks.toml`
- **Heroku**: `runtime.txt`

### Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Database accessible from deployment environment
- [ ] SSL/TLS enabled for database connections
- [ ] Debug logs disabled in production
- [ ] Frontend uses structured response fields
- [ ] API rate limiting configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy in place

### Performance Considerations

- Use connection pooling for database connections
- Enable caching for frequently accessed data
- Monitor LLM API usage and costs
- Implement rate limiting for API endpoints
- Use CDN for static assets if applicable

---

## Database Migration

### SQL Server to PostgreSQL Migration

The chatbot database layer has been migrated from SQL Server to PostgreSQL (Neon).

**Key Changes**:
- Removed SQL Server dependencies (pyodbc, pymssql, FreeTDS)
- Added PostgreSQL support (psycopg)
- Updated schema for PostgreSQL compatibility
- Maintained backward compatibility with legacy variables

**Migration Guide**: See `POSTGRESQL_MIGRATION_GUIDE.md` for detailed instructions.

**Benefits**:
- Serverless architecture with Neon
- Better performance and scalability
- Simplified deployment (no ODBC dependencies)
- Automatic backups and point-in-time recovery

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

This will show detailed NLP traces for troubleshooting.

---

## Data Files

| File | Purpose |
|------|---------|
| `app/data/locations.json` | Egyptian governorates, cities, and villages |
| `app/data/knowledge_base.json` | FAQ answers and knowledge base |
| `Results.json` | Database schema snapshot |
| `cities.json` | City reference data |
| `governorates.json` | Governorate reference data |

---

## Known Limitations

- **Session Memory**: In-process memory only; service restart clears sessions
- **LLM Dependency**: Fallback requires Groq API and external availability
- **Database Dependency**: Results depend on current database contents
- **Language Support**: Primarily Egyptian Arabic; limited English support
- **Real-time Updates**: No real-time property listing updates

---

## Security Considerations

- Never commit `.env` files or API keys
- Use environment variables for sensitive configuration
- Enable SSL/TLS for all database connections
- Implement rate limiting on API endpoints
- Regularly rotate API keys and database credentials
- Monitor for suspicious activity
- Keep dependencies updated

---

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Write tests**: Ensure test coverage is maintained
5. **Run tests**: `python -m unittest discover -s tests -v`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings for new functions
- Keep functions focused and concise
- Write tests for new features

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Support

For questions, issues, or contributions:

- 📧 Email: support@staymatch.com
- 🐛 Issues: GitHub Issues
- 📖 Documentation: See this README and migration guide

---

## Acknowledgments

- Groq for LLM API services
- Neon for PostgreSQL hosting
- The open-source community for excellent tools and libraries

---

**Built with ❤️ for the Egyptian housing market**
