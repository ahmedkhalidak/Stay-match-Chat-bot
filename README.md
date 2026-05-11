Message
  ↓
Normalizer
  ↓
Rule Engine
  ↓
Intent Detection
  ↓
Entity Extraction
  ↓
LLM Enhancement
  ↓
Validator
  ↓
SearchFilters

----------------
ChatController
    ↓
NLPPipeline
    ├── Normalizer
    ├── Intent Detector
    ├── Rule Engine
    ├── AI Extractor
    └── Validator

SearchManager
    ├── Search Execution
    ├── Pagination
    └── Cache

ConversationManager
    ├── Memory
    ├── Follow-up
    └── Clarifications

ResponseFormatter

-> docker start sqlserver 
-> uvicorn app.main:app --host 0.0.0.0 --port 8000
