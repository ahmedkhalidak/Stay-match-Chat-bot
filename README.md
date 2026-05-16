# StayMatch AI Service

Backend service for the StayMatch housing assistant. It understands Egyptian Arabic housing requests, asks only for the missing information needed to continue, searches rooms or apartments, and returns structured responses that are ready for a frontend chat UI.

## What It Does

- Understands room, full apartment, and shared apartment searches.
- Supports Egyptian Arabic, English keywords, typo-tolerant location matching, and follow-up messages.
- Uses a hybrid NLP strategy:
  - deterministic rules first for fast, predictable extraction
  - LLM fallback only when rule confidence is low
- Maintains per-session conversation context, preferences, search history, and pagination.
- Returns clean JSON payloads with quick replies, result cards, and pagination metadata.

## Main Flow

The initial search flow is intentionally short:

1. User states the housing type.
2. Bot asks for the location if it is missing.
3. Bot asks for budget if it is still useful to ask.
4. Bot searches and returns structured results.
5. User can refine with follow-ups such as `أرخص`, `فيها واي فاي`, `مش عايز تكييف`, or `في الإسكندرية بدل المعادي`.

Example:

```text
User: عايز أوضة
Bot: تمام، تحب تدور فين؟

User: في المعادي
Bot: ميزانيتك الشهرية تقريباً كام؟

User: تحت 5000
Bot: لقيت 2 أوضة في Maadi.
```

## Architecture

```text
HTTP /chat
  -> SearchService
    -> NLPPipeline
      -> TextNormalizer
      -> NLP lexicon
      -> rule-based intent/entity extraction
      -> optional LLM fallback
      -> FilterValidator
    -> ConversationFlow
    -> SearchExecutor
      -> repositories
      -> ResponseFormatter
  -> ChatResponse JSON
```

Key modules:

| Area | File |
| --- | --- |
| API route | `app/api/routes.py` |
| Main orchestration | `app/services/search_service.py` |
| Search execution and pagination | `app/services/search_executor.py` |
| Conversation state machine | `app/services/conversation_flow.py` |
| NLP pipeline | `app/nlp/nlp_pipeline.py` |
| NLP vocabulary | `app/nlp/lexicon.py` |
| Location matching | `app/services/location_service.py` |
| Response shaping | `app/formatters/response_formatter.py` |
| Session memory | `app/core/session_context.py` |
| Room search | `app/database/repositories/room_repository.py` |
| Property search | `app/database/repositories/property_repository.py` |

## Supported Search Concepts

### Housing Types

- `room`
- `property`
- `full`
- `shared`

### Filters

- city / governorate
- minimum and maximum monthly price
- tenant type: student / worker
- furnished
- wifi
- balcony
- air conditioning
- private bathroom
- gender
- shared room
- sort order: relevance / lowest price / highest price

### Follow-Up Examples

| User message | Effect |
| --- | --- |
| `أرخص` | sort by lowest price |
| `هات الأعلى سعراً` | sort by highest price |
| `فيها واي فاي` | add wifi filter |
| `مش عايز واي فاي` | set wifi to false |
| `غير مفروشة` | set furnished to false |
| `للطلاب` | tenant type = student |
| `في اسكندرية بدل المعادي` | replace location while keeping prior filters |
| `المزيد` | load next page |
| `ارجع` | return to previous search |

## API

### `POST /chat`

Request body:

```json
{
  "session_id": "user-123",
  "message": "عايز أوضة في المعادي تحت 5000"
}
```

Response body:

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

### Response Types

| Type | Meaning |
| --- | --- |
| `clarification` | the bot needs one more slot such as location or price |
| `results` | search results were found |
| `no_results` | search completed but no matching listings were found |
| `end_of_results` | user asked for more after the final page |
| `small_talk` | greeting, thanks, or goodbye |
| `faq` | answer from the local knowledge base |
| `fallback` | unsupported or unrelated request |

## Frontend Integration Notes

- Render `reply` as the assistant message.
- Use `response_type` to choose the UI state.
- Render `suggestions` as quick-reply chips or buttons.
- Render `results` as cards; do not parse card data out of the reply text.
- Use `pending_slot` to understand what the assistant is waiting for.
- Use `pagination.has_more` to show or hide a `المزيد` action.
- Keep the same `session_id` for the whole conversation so follow-ups continue to work.

## Setup

### Requirements

- Python 3.13+
- SQL Server compatible with the configured schema
- Groq API key for LLM fallback extraction

### Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_key_here
DB_HOST=localhost
DB_PORT=1433
DB_NAME=StayMatch
DB_USER=sa
DB_PASSWORD=your_password_here
```

Optional:

```env
DEBUG_LOGS=1
```

`DEBUG_LOGS=1` enables verbose NLP traces. Leave it unset in normal development and production runs.

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

If your SQL Server container is already configured:

```bash
docker start sqlserver
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the API docs at:

```text
http://localhost:8000/docs
```

## Testing

Run the automated suite:

```bash
python -m unittest discover -s tests -v
```

The test suite currently covers:

- room and apartment searches
- PDF regression scenarios
- typo-tolerant location matching
- price filters and sort orders
- amenities and negated amenities
- room vs shared apartment distinction
- follow-up memory behavior
- skip answers such as `أي مكان` and `أي سعر`
- pagination and `المزيد`
- back navigation
- no-results responses
- FAQ, small talk, and invalid requests
- frontend response shape

Compile-check the project:

```bash
python -m compileall app tests
```

## Live Smoke Test

With a working database connection, these scenarios are useful for a quick manual verification:

```text
عايز اوضة في المعادي تحت 5000
فيها واي فاي

عايز شقة كاملة في المعادي تحت 10000

عايز اوضة في االسمعيلية
```

Expected behavior:

- valid room searches return `results`
- valid empty searches return `no_results`
- incomplete searches return `clarification`
- typo-tolerant locations still resolve correctly

## Data Files

| File | Purpose |
| --- | --- |
| `app/data/locations.json` | governorates, cities, and villages used for location detection |
| `app/data/knowledge_base.json` | FAQ answers |
| `Results.json` | database schema snapshot |
| `Staymatch Chatbot Test Cases Arabic.pdf` | original manual chatbot scenarios |

## Deployment Notes

The repository includes:

- `Dockerfile`
- `render.yaml`
- `nixpacks.toml`
- `runtime.txt`

Before deployment, confirm:

1. environment variables are configured
2. SQL Server is reachable from the service
3. frontend uses the structured response fields instead of parsing plain text
4. debug logs are disabled unless actively investigating an issue

## Known Boundaries

- Conversation memory is in-process memory only; restarting the service clears sessions.
- The LLM fallback depends on the configured Groq API key and external availability.
- Search results depend on the current database contents and approval flags.
