# Housing Type Intelligent Clarification - Implementation Documentation

## Overview

This implementation adds intelligent housing type detection and clarification to the StayMatch chatbot. The system now automatically detects accommodation type from user messages and only asks for clarification when it will significantly improve search quality.

## Key Features

### 1. Automatic Housing Type Detection

The system automatically detects housing type from user messages using both rule-based NLP and LLM fallback:

**Detection Examples:**
- "عاوز شقة في القاهرة" → `housing_type = apartment`
- "عاوز أوضة في القاهرة" → `housing_type = room`
- "عاوز روم ميت" → `housing_type = shared`
- "عاوز سكن في القاهرة" → `housing_type = unknown` (will execute search first)

### 2. Smart Clarification Flow

The system follows these rules:

**Rule 1:** If housing_type is clear from user message → Execute search immediately

**Rule 2:** If housing_type is unknown → Execute search first

**Rule 3:** Ask clarification ONLY when:
- housing_type is unknown AND
- search result count is large (> 20 results) AND
- housing_type hasn't been explicitly skipped

**Rule 4:** If result count is small (≤ 20) → Return results directly without asking

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Message Input                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              NLP Pipeline - Extract Filters                   │
│  - Detect housing_type from message                          │
│  - Extract other filters (location, price, etc.)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Apply User Preferences                           │
│  - Fill missing filters from stored preferences              │
│  - Respect skipped slots                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Check Other Clarifications                       │
│  - location, price, etc. (existing flow)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Execute Search                                   │
│  - Query database with current filters                      │
│  - Get result count                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                ┌────────┴────────┐
                │                 │
        Result Count ≤ 20   Result Count > 20
                │                 │
                ▼                 ▼
┌───────────────────────┐  ┌─────────────────────────────────┐
│ Return Results        │  │ Check housing_type               │
│ Directly              │  │                                 │
└───────────────────────┘  │ housing_type specified?          │
                           │                                 │
                    ┌──────┴──────┐                        │
                    │             │                        │
                Yes             No                        │
                    │             │                        │
                    ▼             ▼                        │
            ┌───────────┐  ┌─────────────────┐              │
            │ Return    │  │ housing_type     │              │
            │ Results   │  │ previously      │              │
            │           │  │ skipped?        │              │
            └───────────┘  │                 │              │
                         ┌───┴──────┐        │              │
                         │          │        │              │
                     Yes          No        │              │
                         │          │        │              │
                         ▼          ▼        │              │
                   ┌─────────┐ ┌──────────┐ │              │
                   │ Return  │ │ Ask for  │ │              │
                   │ Results │ │ housing_ │ │              │
                   │         │ │ type     │ │              │
                   └─────────┘ │          │ │              │
                                └──────────┘ │              │
                                             │              │
                                             ▼              │
                                   ┌─────────────────────┐  │
                                   │ Show Options:        │  │
                                   │ 🏠 شقة كاملة         │  │
                                   │ 🚪 غرفة              │  │
                                   │ 👥 سكن مشترك         │  │
                                   │ أو اكتب اعرض الكل    │  │
                                   └─────────────────────┘  │
                                             │              │
                                             └──────────────┘
```

## Updated Filter Model

### SearchFilters

```python
class SearchFilters(BaseModel):
    intent: Optional[str] = None
    search_type: Optional[str] = None  # "room" | "property" | "full" | "shared"
    housing_type: Optional[str] = None  # "apartment" | "room" | "shared" | "any"  ← NEW
    city: Optional[str] = None
    governorate: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    tenant_type: Optional[str] = None
    furnished: Optional[bool] = None
    wifi: Optional[bool] = None
    private_bathroom: Optional[bool] = None
    balcony: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    gender: Optional[str] = None
    shared_room: Optional[bool] = None
    sort_by: Optional[str] = None
```

### UserPreferences

```python
class UserPreferences(BaseModel):
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    preferred_location: Optional[str] = None
    tenant_type: Optional[str] = None
    gender: Optional[str] = None
    furnished: Optional[bool] = None
    wifi: Optional[bool] = None
    air_conditioning: Optional[bool] = None
    balcony: Optional[bool] = None
    private_bathroom: Optional[bool] = None
    shared_room: Optional[bool] = None
    housing_type: Optional[str] = None  # ← NEW
```

## Housing Type Keywords

### Arabic/English Detection

```python
HOUSING_TYPE_KEYWORDS = {
    "apartment": [
        "شقة", "شقه", "apartment", "flat", "كاملة", "كامله", "full",
        "وحدة", "وحده", "عقار", "منزل", "house", "home", "villa",
    ],
    "room": [
        "اوضة", "اوضه", "غرفة", "غرفه", "room", "bedroom", "studio",
        "سنجل", "single", "خاص", "private", "فردي", "لوحدي",
    ],
    "shared": [
        "مشترك", "shared", "roommate", "مع ناس", "مع حد", "سكن مشترك",
        "شقه مشتركه", "شقة مشتركة", "shared apartment", "shared flat",
        "روم ميت", "roommate", "شير", "مشاركة",
    ],
}
```

## Intent Examples

### Detection Examples

**User:** "عاوز شقة في القاهرة"
```json
{
  "intent": "property_search",
  "search_type": "property",
  "housing_type": "apartment",
  "city": "Cairo"
}
```
**Result:** Execute search immediately (housing_type is clear)

---

**User:** "عاوز أوضة في القاهرة"
```json
{
  "intent": "room_search",
  "search_type": "room",
  "housing_type": "room",
  "city": "Cairo"
}
```
**Result:** Execute search immediately (housing_type is clear)

---

**User:** "عاوز روم ميت في القاهرة"
```json
{
  "intent": "room_search",
  "search_type": "room",
  "housing_type": "shared",
  "city": "Cairo"
}
```
**Result:** Execute search immediately (housing_type is clear)

---

**User:** "عاوز سكن في القاهرة"
```json
{
  "intent": "property_search",
  "city": "Cairo"
}
```
**Result:** Execute search first, then check result count

### Clarification Flow Examples

**Scenario 1: Large result count (> 20)**

**User:** "عاوز سكن في القاهرة"
**System:** Executes search → 83 results found
**Bot Response:**
```
لقيت 83 نتيجة في القاهرة.

تفضل:
🏠 شقة كاملة
🚪 غرفة
👥 سكن مشترك

أو اكتب اعرض الكل
```

**User:** "شقة كاملة"
**System:** Updates housing_type to "apartment", re-runs search
**Result:** Returns filtered results (apartments only)

---

**Scenario 2: Small result count (≤ 20)**

**User:** "عاوز سكن في أسيوط"
**System:** Executes search → 4 results found
**Bot Response:** Returns the 4 results immediately (no clarification asked)

---

**Scenario 3: User chooses "show all"**

**User:** "اعرض الكل"
**System:** Sets housing_type to "any", marks as skipped
**Result:** Returns all results without filtering by housing_type

---

**Scenario 4: Follow-up with housing_type preserved**

**User:** "عاوز شقة في القاهرة"
**System:** housing_type = "apartment", executes search

**User:** "الأرخص"
**System:** housing_type still = "apartment", sorts by price
**Result:** Returns cheapest apartments only (preserves housing_type preference)

## Implementation Changes

### Files Modified

1. **app/models/search_models.py**
   - Added `housing_type` field to SearchFilters

2. **app/nlp/parsed_message.py**
   - Added `housing_type` field to ParsedMessage
   - Updated `to_search_filters()` to include housing_type

3. **app/core/session_context.py**
   - Added `housing_type` field to UserPreferences
   - Updated `update_preferences()` to handle housing_type

4. **app/nlp/lexicon.py**
   - Added `HOUSING_TYPE_KEYWORDS` for Arabic/English detection

5. **app/nlp/nlp_pipeline.py**
   - Added `_extract_housing_type()` method
   - Updated `_merge_with_last_search()` to preserve housing_type
   - Updated `_llm_fallback()` to handle LLM-detected housing_type
   - Updated `_handle_slot_reply()` to handle "اعرض الكل" response

6. **app/services/conversation_flow.py**
   - Added `HOUSING_TYPE_RESULT_THRESHOLD` constant (20)
   - Added `should_ask_housing_type_clarification()` method
   - Added `get_housing_type_clarification()` method
   - Added `ANY_HOUSING_TYPE_PHRASES` for "show all" detection
   - Updated `apply_preferences_to_filters()` to apply housing_type preference
   - Updated `apply_user_overrides()` to handle "show all" response
   - Updated `sync_skipped_slots()` to handle housing_type
   - Updated `get_slot_suggestions()` to include housing_type options

7. **app/services/search_service.py**
   - Added post-search clarification check
   - Calls `should_ask_housing_type_clarification()` after search execution
   - Returns clarification response if needed

8. **app/extractors/filter_extractor.py**
   - Added housing_type detection using HOUSING_TYPE_KEYWORDS

9. **app/prompts/extraction_prompt.py**
   - Added `housing_type` to field guide
   - Added housing_type examples for LLM extraction

## Configuration

### Threshold Configuration

The result count threshold for asking housing_type clarification is configurable:

```python
# app/services/conversation_flow.py
HOUSING_TYPE_RESULT_THRESHOLD = 20  # Ask for clarification if > 20 results
```

To change the threshold, modify this constant.

## Testing

### Test Cases

1. **Clear housing_type detection**
   - Input: "عاوز شقة في القاهرة"
   - Expected: housing_type = "apartment", execute search immediately

2. **Unknown housing_type with large results**
   - Input: "عاوز سكن في القاهرة" (assuming > 20 results)
   - Expected: Execute search, then ask for housing_type clarification

3. **Unknown housing_type with small results**
   - Input: "عاوز سكن في أسيوط" (assuming ≤ 20 results)
   - Expected: Execute search, return results directly (no clarification)

4. **Housing_type clarification response**
   - Input: "شقة كاملة" (after clarification)
   - Expected: housing_type = "apartment", re-run search

5. **Show all response**
   - Input: "اعرض الكل" (after clarification)
   - Expected: housing_type = "any", return all results

6. **Follow-up preserves housing_type**
   - Input: "الأرخص" (after searching for apartments)
   - Expected: housing_type still = "apartment", sort by price

## Benefits

1. **Reduced Irrelevant Results**: Users get more relevant results by filtering by accommodation type when needed

2. **Natural Conversation Flow**: No forced questionnaires - only ask when it significantly improves search quality

3. **Automatic Detection**: Most users specify housing type naturally, so clarification is rarely needed

4. **Smart Threshold**: Only ask when result count is large enough to warrant filtering

5. **Memory Preservation**: Housing_type preference is stored and used in follow-up requests

6. **Flexible Response**: Users can choose specific type or "show all" to see everything

## Future Enhancements

1. **Dynamic Threshold**: Adjust threshold based on location (e.g., higher threshold for smaller cities)

2. **Machine Learning**: Train model to predict when clarification will improve user satisfaction

3. **Multi-select**: Allow users to select multiple housing types (e.g., "apartment or room")

4. **Context-aware**: Consider user's search history to predict likely housing type

5. **A/B Testing**: Test different thresholds and messages to optimize user experience
