# Sophisticated Summarization System - Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHAT SERVICE FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │  User Input  │
                              └──────┬───────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │ ThreadService.process_ │
                        │    user_message()      │
                        └────────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐  ┌────────────────┐  ┌─────────┐
            │ Save User    │  │ Get Context    │  │ Call    │
            │ Message      │  │ (last summary) │  │ LLM     │
            └──────┬───────┘  └────────┬───────┘  └────┬────┘
                   │                   │               │
                   └───────────┬───────┴───────────────┘
                               │
                               ▼
                        ┌────────────────┐
                        │ Save Agent     │
                        │ Message        │
                        └────────┬───────┘
                                 │
                    ┌────────────┴─────────────┐
                    │                          │
            Message Count < 4?          Message Count >= 4?
                    │ Yes                      │ No
                    │                          ▼
                    │                 ┌────────────────────┐
                    │                 │ Trigger            │
                    │                 │ Summarization()    │
                    │                 └────────┬───────────┘
                    │                          │
                    │                ┌─────────┴──────────────┐
                    │                │                        │
                    │                ▼                        ▼
                    │         ┌──────────────────┐  ┌──────────────────┐
                    │         │ Get All Messages │  │ Get Last Summary │
                    │         │ from Thread      │  │ (for context)    │
                    │         └────────┬─────────┘  └────────┬─────────┘
                    │                  │                     │
                    │                  └──────────┬──────────┘
                    │                             │
                    │                             ▼
                    │                 ┌─────────────────────────┐
                    │                 │ SummarizationService    │
                    │                 │ .summarize_conversation │
                    │                 │ (messages, prev_summary)│
                    │                 └──────────┬──────────────┘
                    │                            │
                    │          ┌─────────────────┴─────────────────┐
                    │          │                                   │
                    │          ▼                                   ▼
                    │   ┌────────────────┐             ┌──────────────────────┐
                    │   │ Call LLM with  │             │ If Previous Summary  │
                    │   │ system prompt  │             │ Merge + Deduplicate  │
                    │   │ asking for     │             │ (SummarySlicingEngine│
                    │   │ structured     │             │  .merge_summaries)   │
                    │   │ extraction     │             └──────────────────────┘
                    │   └────────┬───────┘                       │
                    │            │                               │
                    │            └───────────────┬───────────────┘
                    │                            │
                    │                            ▼
                    │                 ┌─────────────────────────┐
                    │                 │ Parse JSON Response     │
                    │                 │ Validate Structure      │
                    │                 │ {                       │
                    │                 │   "core_facts": [...],  │
                    │                 │   "user_prefs": [...],  │
                    │                 │   "decisions": [...],   │
                    │                 │   "constraints": [...], │
                    │                 │   "open_questions": [...],
                    │                 │   "entities": {...}     │
                    │                 │ }                       │
                    │                 └────────┬────────────────┘
                    │                          │
                    │                          ▼
                    │                 ┌─────────────────────┐
                    │                 │ Save to Database    │
                    │                 │ Summary Model       │
                    │                 └────────┬────────────┘
                    │                          │
                    └──────────────┬───────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │  Return to   │
                            │  User        │
                            └──────────────┘
```

---

## Summary Storage & Retrieval Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐   │
│  │  threads TABLE  │  │  messages TABLE  │  │ summaries  │   │
│  ├─────────────────┤  ├──────────────────┤  │  TABLE     │   │
│  │ id (PK)         │  │ id (PK)          │  ├────────────┤   │
│  │ title           │  │ thread_id (FK)   │  │ id (PK)    │   │
│  │ system_prompt   │  │ sender           │  │ thread_id  │   │
│  │ created_at      │  │ role             │  │ (FK)       │   │
│  │                 │  │ content          │  │            │   │
│  │ ──────────────  │  │ model_used       │  │ summary_   │   │
│  │ relationships:  │  │ timestamp        │  │ data (JSON)│   │
│  │ - messages      │  │                  │  │ {          │   │
│  │ - summaries     │  │ ──────────────── │  │   "core_   │   │
│  │                 │  │ relationships:   │  │   facts":  │   │
│  │                 │  │ - thread         │  │   [...],   │   │
│  │                 │  │                  │  │   ...      │   │
│  │                 │  │                  │  │ }          │   │
│  │                 │  │                  │  │            │   │
│  │                 │  │                  │  │ embedding  │   │
│  │                 │  │                  │  │ (Vector)   │   │
│  │                 │  │                  │  │ created_at │   │
│  │                 │  │                  │  │ msg_count  │   │
│  └─────────────────┘  └──────────────────┘  │            │   │
│                                             │ ────────── │   │
│                                             │ relations: │   │
│                                             │ - thread   │   │
│  ┌──────────────────────────────────┐       └────────────┘   │
│  │   model_metadata (In memory)     │                        │
│  ├──────────────────────────────────┤                        │
│  │ id (PK)                          │                        │
│  │ model_name (UNIQUE)              │                        │
│  │ summary_type (small/med/large)   │                        │
│  │ max_tokens                       │                        │
│  │ description                      │                        │
│  │ created_at                       │                        │
│  │ updated_at                       │                        │
│  └──────────────────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Summary Slicing Engine Architecture

```
┌───────────────────────────────────────────────────────────┐
│         SummarySlicingEngine (summary_utils.py)           │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Full Summary (7 fields)                                  │
│  ┌──────────────────────────────────────────┐             │
│  │ core_facts                               │             │
│  │ user_preferences                         │             │
│  │ decisions_made                           │             │
│  │ constraints                              │             │
│  │ open_questions                           │             │
│  │ entities                                 │             │
│  │ other                                    │             │
│  └──────────────────────────────────────────┘             │
│                    │                                      │
│                    ▼                                      │
│  ┌──────────────────────────────────────────┐             │
│  │ slice_summary(type)                      │             │
│  │ SUMMARY_TYPES = {                        │             │
│  │   "small": [                             │             │
│  │     "core_facts",                        │             │
│  │     "user_preferences",                  │             │
│  │     "constraints"                        │             │
│  │   ],                                     │             │
│  │   "medium": [                            │             │
│  │     "core_facts",                        │             │
│  │     "user_preferences",                  │             │
│  │     "decisions_made",                    │             │
│  │     "constraints",                       │             │
│  │     "open_questions",                    │             │
│  │     "other         "                     │             │
│  │   ],                                     │             │
│  │   "large": [                             │             │
│  │     ALL FIELDS                           │             │
│  │   ]                                      │             │
│  │ }                                        │             │
│  └──────────────────────────────────────────┘             │
│         │             │              │                    │
│         └─────────────┼──────────────┘                    │
│                       ▼                                   │
│        ┌──────────────────────────────────┐               │
│        │ format_summary_for_context()     │               │
│        │ Converts to readable string      │               │
│        │ for LLM injection                │               │
│        └──────────────────────────────────┘               │
│                       │                                   │
│                       ▼                                   │
│        ┌──────────────────────────────────┐               │
│        │ get_summary_for_model(model)     │               │
│        │ Looks up model metadata          │               │
│        │ Auto-selects appropriate size    │               │
│        └──────────────────────────────────┘               │
│                       │                                   │
│                       ▼                                   │
│        ┌──────────────────────────────────┐               │
│        │ merge_summaries(old, new)        │               │
│        │ Merges while deduplicating       │               │
│        └──────────────────────────────────┘               │
│                                                           │
└────────────────────────────────────────────────────────── ┘
```

---

## API Endpoint Architecture

```
┌──────────────────────────────────────────────────┐
│              THREAD ROUTES API                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  /threads (existing)                             │
│  ├─ POST /              Create thread            │
│  ├─ GET /               List threads             │
│  ├─ GET /{id}           Get thread with msgs/sums
│  ├─ POST /{id}/messages Add message              │
│  └─ GET /{id}/summaries Get summaries            │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Data Flow: Summary Generation

```
Thread has 4+ messages
         │
         ▼
  ┌─────────────────┐
  │ ThreadService   │
  │._trigger_       │
  │ summarization() │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────────────┐
  │ Fetch messages from DB  │
  │ Fetch previous summary  │
  └────────┬────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ SummarizationService         │
  │ .summarize_conversation()    │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Call LLM with:               │
  │ - System prompt (extraction) │
  │ - Conversation messages      │
  │ - Previous summary (context) │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ LLM Response (JSON):         │
  │ {                            │
  │   "core_facts": [...],       │
  │   "user_preferences": [...], │
  │   ...                        │
  │ }                            │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Validate JSON structure      │
  │ Ensure all fields present    │
  └────────┬─────────────────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │ Save to summaries table      │
  │ Store summary_data as JSON   │
  │ Keep embedding (if computed) │
  └────────┬─────────────────────┘
           │
           ▼
     ✓ Complete
```

---

## Integration Points

```
┌──────────────────────────────────────────────────────────────┐
│                  SYSTEM INTEGRATION MAP                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ThreadService                                              │
│  ├─ Calls: thread_crud.get_messages_for_thread()           │
│  ├─ Calls: thread_crud.get_last_summary_for_thread()       │
│  ├─ Calls: SummarizationService.summarize_conversation()   │
│  └─ Calls: thread_crud.add_summary_to_thread()             │
│                                                              │
│  SummarizationService                                       │
│  ├─ Calls: LLMService.generate_response()                  │
│  └─ Returns: Dict[str, Any] (JSON summary)                 │
│                                                              │
│  API Routes                                                 │
│  ├─ Calls: thread_crud.create_or_update_model_metadata()   │
│  ├─ Calls: thread_crud.get_model_metadata()                │
│  ├─ Calls: thread_crud.get_all_model_metadata()            │
│  ├─ Calls: thread_crud.delete_model_metadata()             │
│  └─ Calls: thread_crud.get_summaries_for_thread()          │
│                                                              │
│  SummarySlicingEngine                                       │
│  ├─ Provides: slice_summary()                              │
│  ├─ Provides: format_summary_for_context()                 │
│  ├─ Provides: get_summary_for_model()                      │
│  ├─ Provides: merge_summaries()                            │
│  └─ Used by: ThreadService, API handlers, client code      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration Flow

```
Admin/Developer
        │
        ▼
┌──────────────────────────────────────┐
│ POST /threads/models                 │
│ {                                    │
│   "model_name": "google/gemini-pro", │
│   "summary_type": "large",           │
│   "max_tokens": 4096                 │
│ }                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Save to model_metadata table         │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Later: When using this model for LLM │
│                                      │
│ SummarySlicingEngine.get_summary_for_model(
│   db, summary, "google/gemini-pro"
│ )                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Retrieve model_metadata              │
│ Get: summary_type = "large"          │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Return full summary (all 6 fields)   │
│ for use in LLM prompt                │
└──────────────────────────────────────┘
```

---