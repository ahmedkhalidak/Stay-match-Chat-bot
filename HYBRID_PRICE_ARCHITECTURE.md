# Hybrid Price Understanding Architecture

## Overview

The Hybrid Price Understanding System combines rule-based parsing with LLM fallback to handle both known patterns and novel phrasings without requiring constant keyword expansion.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Message Input                           │
│                    "ازيد 5000" or "تحت 5000"                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PriceParser.extract_price()                     │
│                  (Hybrid Architecture)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: Rule-Based Parsing                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Normalize text (Arabic digits, thousands, etc.)     │  │
│  │  2. Check range patterns (بين 3000 و 5000)                │  │
│  │  3. Check budget patterns (ميزانيتي 5000)                │  │
│  │  4. Check max patterns (تحت 5000)                        │  │
│  │  5. Check min patterns (فوق 5000)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │ Pattern Matched?        │
            └────────────┬────────────┘
                         │
            ┌────────────┴────────────┐
            │ YES                     │ NO
            ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ Return Rule Result  │  │ STEP 2: LLM Fallback                  │
│ (min, max, type)    │  │ ┌────────────────────────────────────┐ │
└──────────────────────┘  │ │ Check: contains_number == True?    │ │
                         │ └────────────┬───────────────────────┘ │
                         │              │ NO                      │
                         │              ▼                         │
                         │    ┌──────────────────────┐           │
                         │    │ Return "none"       │           │
                         │    └──────────────────────┘           │
                         │              │ YES                     │
                         │              ▼                         │
                         │ ┌────────────────────────────────────┐ │
                         │ │ Invoke LLMPriceClassifier         │ │
                         │ │ - System prompt with examples     │ │
                         │ │ - Return JSON schema              │ │
                         │ └────────────┬───────────────────────┘ │
                         │              │                         │
                         │              ▼                         │
                         │ ┌────────────────────────────────────┐ │
                         │ │ Check: confidence >= 0.70?        │ │
                         │ └────────────┬───────────────────────┘ │
                         │              │                         │
                         │    ┌─────────┴─────────┐             │
                         │    │ YES               │ NO          │
                         │    ▼                   ▼             │
                         │ ┌────────┐      ┌──────────────┐    │
                         │ │ Return │      │ Return None  │    │
                         │ │ LLM    │      │ (fallback    │    │
                         │ │ Result │      │  failed)     │    │
                         │ └────────┘      └──────────────┘    │
                         └──────────────────────────────────────┘
```

## Flow Steps

### STEP 1: Rule-Based Parsing

**Purpose:** Fast, deterministic classification for known patterns.

**Process:**
1. Normalize text:
   - Convert Arabic digits (٥٠٠٠ → 5000)
   - Convert thousands (5k → 5000, 5 آلاف → 5000)
   - Convert Arabic number words (خمسة آلاف → 5000)

2. Check patterns in priority order:
   - **Range:** `بين 3000 و 5000`, `3000-5000`, `between 3000 and 5000`
   - **Budget:** `ميزانيتي 5000`, `budget 5000`, `معايا 5000`
   - **Max:** `تحت 5000`, `اقل من 5000`, `max 5000`
   - **Min:** `فوق 5000`, `اكثر من 5000`, `min 5000`

3. If pattern matches:
   - Apply budget tolerance (10%) for budget intent
   - Return result immediately

**Debug Logs:**
- `PRICE_RULE_MATCH`: Pattern matched
- `PRICE_RANGE_GENERATED`: Generated range

### STEP 2: LLM Fallback

**Purpose:** Handle novel phrasings not covered by rules.

**Trigger Condition:**
- Rule-based parsing failed
- Message contains numeric values

**Process:**
1. Check if message contains numbers
2. If yes, invoke LLM classifier
3. LLM returns JSON with:
   ```json
   {
     "price_intent": "budget|min|max|range|none",
     "min_price": number|null,
     "max_price": number|null,
     "confidence": float
   }
   ```
4. Check confidence threshold (>= 0.70)
5. If confident, apply budget tolerance for budget intent
6. Return result

**Debug Logs:**
- `PRICE_RULE_FAILED`: No rule patterns matched
- `PRICE_LLM_FALLBACK`: Invoking LLM classifier
- `PRICE_LLM_RESPONSE`: LLM classification result
- `PRICE_LLM_FAILED`: LLM failed or confidence below threshold
- `PRICE_OVERRIDE`: LLM classification applied

## LLM Classifier

### System Prompt

```
You are a price intent classifier for a real estate chatbot in Egypt.
Your task is to analyze user messages and extract price information.

You must return ONLY valid JSON with this exact schema:
{
  "price_intent": "budget|min|max|range|none",
  "min_price": number|null,
  "max_price": number|null,
  "confidence": float
}

Rules:
- "budget": User states their budget/limit (apply 10% tolerance: 5000 → 4500-5500)
- "min": User wants minimum price (e.g., "ازيد من 5000" → min=5000)
- "max": User wants maximum price (e.g., "تحت 5000" → max=5000)
- "range": User specifies a range (e.g., "بين 3000 و 5000" → 3000-5000)
- "none": No price intent detected

Return ONLY JSON. No explanations.
```

### Examples

| Input | Output |
|-------|--------|
| `ازيد 5000` | `{"price_intent":"min","min_price":5000,"max_price":null,"confidence":0.95}` |
| `تحت 5000` | `{"price_intent":"max","min_price":null,"max_price":5000,"confidence":0.99}` |
| `في حدود 5000` | `{"price_intent":"budget","min_price":4500,"max_price":5500,"confidence":0.95}` |
| `معايا 5000` | `{"price_intent":"budget","min_price":4500,"max_price":5500,"confidence":0.95}` |
| `بين 3000 و 5000` | `{"price_intent":"range","min_price":3000,"max_price":5000,"confidence":0.99}` |

## Budget Tolerance Rule

For budget intent, apply configurable tolerance:

```
BUDGET_TOLERANCE_PERCENT = 10

Example:
5000
margin = 500
Result: 4500 - 5500

Formula:
margin = budget * tolerance
min_price = budget - margin
max_price = budget + margin
```

## Merge Rules

When LLM returns a valid price intent, override previous budget filters:

**Example:**
```
Previous: max_price = 5000
User: "ازيد 7000"
Result: min_price = 7000, max_price = null
```

**Do NOT inherit conflicting budget values.**

## Failsafe

If confidence < 0.70, return clarification instead of guessing:

```
Input: "5000 ولا 7000"
Bot: "تقصد ميزانيتك 5000 ولا 7000؟"
```

## Debug Logs

| Log Name | Description |
|----------|-------------|
| `PRICE_RULE_MATCH` | Rule pattern matched |
| `PRICE_RULE_FAILED` | No rule patterns matched |
| `PRICE_LLM_FALLBACK` | Invoking LLM classifier |
| `PRICE_LLM_RESPONSE` | LLM classification result |
| `PRICE_LLM_FAILED` | LLM failed or confidence below threshold |
| `PRICE_OVERRIDE` | LLM classification applied |
| `FINAL_PRICE_FILTERS` | Final min/max values |

## Affected Files

### Created
- `app/services/llm_price_classifier.py` - LLM fallback service
- `tests/test_llm_price_classifier.py` - LLM classifier unit tests (23 tests)
- `tests/test_hybrid_price_parser.py` - Hybrid architecture integration tests (23 tests)

### Modified
- `app/utils/price_parser.py` - Updated to use hybrid architecture
- `app/extractors/price_extractor.py` - Delegates to new PriceParser

## Test Coverage

### Rule-Based Tests (56 tests)
- Exact budget with tolerance
- Budget phrases (ميزانيتي, budget, معايا, etc.)
- Max price patterns (تحت, اقل من, max, etc.)
- Min price patterns (فوق, اكثر من, min, etc.)
- Range patterns (بين, من, between, etc.)
- Thousands shorthand (5k, 5 آلاف)
- Arabic digits (٥٠٠٠)
- Price override sequences

### LLM Fallback Tests (23 tests)
- Min price novel phrasings (ازيد 5000)
- Max price novel phrasings (في حدود 5000)
- Budget novel phrasings (معايا 5000, حاجة ب 6000)
- Approximate budget (بحوالي 4000)
- Confidence threshold rejection
- Arabic digits with LLM
- Thousands with LLM

### Hybrid Integration Tests (23 tests)
- Rule priority over LLM
- LLM only invoked when rules fail
- Mixed rule and LLM overrides
- End-to-end hybrid flow
- Price override with hybrid

**Total: 102 tests passing**

## Benefits

1. **Scalability:** No need to add new keywords for every phrasing
2. **Performance:** Fast rule-based parsing for common patterns
3. **Flexibility:** LLM handles novel phrasings automatically
4. **Reliability:** Confidence threshold prevents bad guesses
5. **Maintainability:** Clear separation between rules and LLM
6. **Debugging:** Comprehensive debug logs for troubleshooting

## Migration Path

### Before (Rule-Only)
```
Input: "ازيد 5000"
Result: Not recognized (needs new keyword)
```

### After (Hybrid)
```
Input: "ازيد 5000"
Result: min_price=5000 (LLM fallback)
```

## Configuration

```python
# In LLMPriceClassifier
CONFIDENCE_THRESHOLD = 0.70
BUDGET_TOLERANCE_PERCENT = 10

# In PriceParser
BUDGET_TOLERANCE_PERCENT = 10
```

## Future Enhancements

1. Replace mock LLM with actual LLM API (OpenAI, etc.)
2. Add learning from user feedback
3. Cache LLM results for common phrasings
4. Add A/B testing for confidence thresholds
5. Support for more complex price expressions
