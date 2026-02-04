# Sophisticated Summarization System

## Overview

The chat service now includes a sophisticated summarization engine that generates structured, context-aware summaries of conversations. Summaries are organized into specific categories and can be intelligently sliced based on model capabilities.

## Summary Structure

All summaries follow this JSON structure:

```json
{
  "core_facts": ["Fact 1", "Fact 2"],
  "user_preferences": ["Preference 1", "Preference 2"],
  "decisions_made": ["Decision 1", "Decision 2"],
  "constraints": ["Constraint 1", "Constraint 2"],
  "open_questions": ["Question 1", "Question 2"],
  "entities": {
    "entity_name": "entity_role_or_description",
    "person_name": "their_role"
  }
}
```

### Field Definitions

- **core_facts**: Fundamental facts, data, and information discussed in the conversation
- **user_preferences**: Preferences, requirements, and stated priorities
- **decisions_made**: Conclusions reached and decisions made during discussion
- **constraints**: Limitations, restrictions, and requirements mentioned
- **open_questions**: Questions that remain unanswered or need follow-up
- **entities**: Important entities (people, companies, projects) with their roles/descriptions

## Automatic Summarization Trigger

Summarization is **automatically triggered after every 4 messages** in a thread.

### Configuration

To change the threshold, modify `ThreadService.SUMMARIZATION_THRESHOLD`:

```python
# In app/services/thread_service.py
SUMMARIZATION_THRESHOLD = 4  # Summarize after 4 messages
```

## Summary Sizes

The system supports three summary sizes to accommodate different model capabilities:

### Small Summary

**Best for**: Token-constrained models, quick context
**Includes**:

- core_facts
- user_preferences
- constraints

### Medium Summary (Default)

**Best for**: Most models and general use
**Includes**:

- core_facts
- user_preferences
- decisions_made
- constraints
- open_questions

### Large Summary

**Best for**: Advanced models with large context windows
**Includes**: All fields (complete summary)

## Model Metadata Management

Each LLM model can be configured with metadata specifying which summary size it should use.

### Create/Update Model Metadata

```bash
POST /threads/models
Content-Type: application/json

{
  "model_name": "google/gemini-pro",
  "summary_type": "medium",
  "max_tokens": 4096,
  "description": "Google's Gemini Pro model"
}
```

### Response

```json
{
  "id": 1,
  "model_name": "google/gemini-pro",
  "summary_type": "medium",
  "max_tokens": 4096,
  "description": "Google's Gemini Pro model",
  "created_at": "2026-02-03T10:30:00",
  "updated_at": "2026-02-03T10:30:00"
}
```

### List All Models

```bash
GET /threads/models
```

### Get Specific Model

```bash
GET /threads/models/google/gemini-pro
```

### Delete Model Metadata

```bash
DELETE /threads/models/google/gemini-pro
```

## Using Summary Slicing in Code

### Basic Slicing

```python
from app.services.summary_utils import SummarySlicingEngine

# Slice a summary for a specific model size
sliced = SummarySlicingEngine.slice_summary(
    summary=full_summary,
    summary_type="medium"
)
```

### Format Summary for Prompts

```python
# Get formatted text for injection into LLM prompts
formatted = SummarySlicingEngine.format_summary_for_context(
    summary=full_summary,
    summary_type="small"
)

# Use in prompts:
prompt = f"""
Context from previous conversation:
{formatted}

New question: ...
"""
```

### Auto-Select Based on Model

```python
# Get summary sliced appropriately for a model
appropriate_summary = SummarySlicingEngine.get_summary_for_model(
    db=db_session,
    summary=full_summary,
    model_name="google/gemini-pro"
)
```

### Merge Summaries

```python
# Intelligently merge two summaries (deduplicates items)
merged = SummarySlicingEngine.merge_summaries(
    previous=old_summary,
    new_items=new_summary
)
```

### Get Summary Statistics

```python
from app.services.summary_utils import get_summary_stats

stats = get_summary_stats(summary)
# Returns: {
#   "core_facts": 5,
#   "user_preferences": 3,
#   "decisions_made": 2,
#   "constraints": 1,
#   "open_questions": 2,
#   "entities": 3,
#   "total_items": 16
# }
```

## Database Schema

### Summary Table

The `summaries` table stores structured summaries:

```sql
CREATE TABLE summaries (
  id INTEGER PRIMARY KEY,
  thread_id INTEGER NOT NULL REFERENCES threads(id),
  summary_data JSON NOT NULL DEFAULT '{"core_facts": [], ...}',
  embedding VECTOR(1536) NULL,  -- For semantic search
  created_at TIMESTAMP NOT NULL,
  message_count INTEGER DEFAULT 0
);
```

### ModelMetadata Table

The `model_metadata` table stores model configuration:

```sql
CREATE TABLE model_metadata (
  id INTEGER PRIMARY KEY,
  model_name VARCHAR(255) NOT NULL UNIQUE,
  summary_type VARCHAR(50) NOT NULL DEFAULT 'medium',
  max_tokens INTEGER DEFAULT 4096,
  description TEXT,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

## Summary Generation Flow

1. **Message Processing**: User/agent message is added to thread
2. **Count Check**: System checks total message count
3. **Trigger**: If message count ≥ 4, summarization is triggered
4. **Extraction**: LLM analyzes all messages and extracts:
   - Facts discussed
   - User preferences
   - Decisions reached
   - Constraints mentioned
   - Unresolved questions
   - Important entities
5. **Storage**: Structured summary JSON is saved to database
6. **Merging**: On next summarization, previous summary is merged with new items

## LLM Prompt for Summarization

The summarization service uses a specialized prompt that instructs the LLM to:

```
1. Analyze the conversation
2. Extract information into specific categories
3. Return ONLY valid JSON matching the exact structure
4. Avoid duplicates when merging with previous summary
```

## Best Practices

### 1. Configure Models on First Use

```python
# Set up model metadata when you start using a new model
create_or_update_model_metadata(
    db=db,
    model_name="mistralai/mistral-7b-instruct",
    summary_type="small",  # Limited context window
    max_tokens=4096,
    description="Mistral 7B Instruct"
)
```

### 2. Use Appropriate Summary Sizes

- **Small** for initial context building
- **Medium** for standard operation (default)
- **Large** for complex problem-solving sessions

### 3. Monitor Summary Growth

```python
stats = get_summary_stats(summary)
if stats["total_items"] > 50:
    print("Summary growing large, consider archiving old summaries")
```

### 4. Leverage Summary Context

Always include the latest summary when generating LLM responses:

```python
summary = thread_crud.get_last_summary_for_thread(db, thread_id)
if summary:
    context = SummarySlicingEngine.format_summary_for_context(
        summary=summary.summary_data,
        summary_type=model_type
    )
    messages.append({"role": "user", "content": context})
```

## Advanced Features

### Semantic Search on Summaries

Vector embeddings of summaries enable semantic search:

```python
# Find similar conversations by summary embedding
similar_summaries = db.query(Summary).filter(
    Summary.embedding.cosine_distance(query_embedding) < 0.3
).all()
```

### Incremental Summarization

The system intelligently updates summaries by:

1. Retrieving previous summary
2. Adding new messages
3. Merging information (deduplicating)
4. Storing updated summary

This maintains context continuity while avoiding redundancy.

### Custom Summary Slicing

Extend `SummarySlicingEngine` for custom slicing logic:

```python
class CustomSlicingEngine(SummarySlicingEngine):
    SUMMARY_TYPES = {
        "minimal": {
            "fields": ["core_facts"]
        },
        "executive": {
            "fields": ["decisions_made", "constraints", "open_questions"]
        }
    }
```

## Troubleshooting

### Summary Not Generated

- Check if message count is ≥ 4
- Verify LLM service is accessible
- Check logs for "Summarization error"

### Invalid JSON Response

- LLM may not follow instructions perfectly
- Check system prompt in `summarization_service.py`
- Lower model temperature for consistency

### Wrong Summary Size for Model

- Ensure model metadata is configured
- Check `get_model_metadata()` returns correct `summary_type`
- Default is "medium" if metadata not found

## Performance Considerations

- Summaries are generated **after** message is saved (non-blocking)
- JSON storage is efficient and queryable
- Vector embeddings optional but enable semantic search
- Merging logic deduplicates to prevent infinite growth

## Future Enhancements

- [ ] Automatic summary archival for old conversations
- [ ] Custom summary categories per domain
- [ ] Summary importance scoring
- [ ] Multi-language summarization
- [ ] Real-time summary streaming
- [ ] Summary diff/change tracking
