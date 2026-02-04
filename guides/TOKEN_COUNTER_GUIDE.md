# Token Counter System Documentation

## Overview

The token counter system ensures your application never exceeds model context windows. It provides:

- **Automatic token counting** for text and messages
- **Context window validation** before making API calls
- **Real-time tracking** of token usage across conversations
- **Safety buffers** to prevent hitting hard limits
- **REST API endpoints** for token management
- **Context awareness** integrated with LLM service

---

## Key Components

### 1. TokenCounter Class

Low-level utility for counting tokens and validating context.

```python
from app.core.token_counter import TokenCounter

# Count tokens for text
tokens = TokenCounter.count_tokens("Your text here", "google/gemini-pro")

# Count tokens for messages
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
]
total_tokens = TokenCounter.count_messages_tokens(
    messages,
    "openai/gpt-4",
    system_prompt="You are helpful"
)

# Validate context usage
validation = TokenCounter.validate_context("google/gemini-pro", used_tokens=5000)
print(validation)
# Output:
# {
#     "is_valid": True,
#     "used_tokens": 5000,
#     "max_tokens": 30000,
#     "remaining": 25000,
#     "safety_exceeded": False,
#     "percentage_used": 16.67,
#     "model": "google/gemini-pro"
# }
```

### 2. ContextWindowManager Class

High-level manager for tracking token usage across a conversation.

```python
from app.core.token_counter import ContextWindowManager

# Create manager for a model with 500-token safety buffer
manager = ContextWindowManager("google/gemini-pro", buffer=500)

# Add tokens as you process text
manager.add_tokens("User message text")
manager.add_tokens("Response from model")

# Check current status
status = manager.get_status()
print(f"Using {status['percentage_used']}% of context")

# Check if text can fit safely
can_fit = manager.can_fit("New message to add")

# Get available tokens (accounting for buffer)
available = manager.get_available_tokens()

# Get warning if approaching limit
warning = manager.warn_if_approaching_limit()
if warning:
    print(warning)

# Reset when starting new conversation
manager.reset()
```

### 3. ModelConfig with Context Window

All models now have context window limits configured in [app/core/models.py](app/core/models.py):

```python
@dataclass
class ModelConfig:
    name: ModelName
    provider: ModelProvider
    max_tokens: int                  # Max output tokens
    temperature: float = 0.7
    supports_vision: bool = False
    context_window: int = 4096       # ← Total context window
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
```

**Example Context Windows:**

| Model         | Context Window | Max Output |
| ------------- | -------------- | ---------- |
| Gemini Pro    | 30,000         | 2,048      |
| GPT-4         | 8,192          | 8,192      |
| GPT-4 Turbo   | 128,000        | 4,096      |
| Claude 3 Opus | 200,000        | 4,096      |
| Mistral 7B    | 32,000         | 1,500      |

---

## REST API Endpoints

### 1. Count Tokens for Text

```http
POST /tokens/count
?text=Your%20text%20here&model=google/gemini-pro
```

**Response:**

```json
{
  "text": "Your text here",
  "model": "google/gemini-pro",
  "tokens": 4,
  "text_length": 15,
  "word_count": 3
}
```

### 2. Count Tokens for Messages

```http
POST /tokens/count-messages
?model=google/gemini-pro&system_prompt=You%20are%20helpful

{
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"}
  ]
}
```

**Response:**

```json
{
  "model": "google/gemini-pro",
  "total_tokens": 87,
  "message_count": 2,
  "has_system_prompt": true,
  "system_prompt": "You are helpful"
}
```

### 3. Validate Context Usage

```http
GET /tokens/validate/google/gemini-pro
?used_tokens=5000&buffer=100
```

**Response:**

```json
{
  "is_valid": true,
  "used_tokens": 5000,
  "max_tokens": 30000,
  "remaining": 25000,
  "safety_exceeded": false,
  "percentage_used": 16.67,
  "model": "google/gemini-pro"
}
```

### 4. Get Context Status

```http
GET /tokens/status/google/gemini-pro?used_tokens=15000
```

**Response:**

```json
{
  "is_valid": true,
  "used_tokens": 15000,
  "max_tokens": 30000,
  "remaining": 15000,
  "safety_exceeded": false,
  "percentage_used": 50.0,
  "model": "google/gemini-pro",
  "buffer": 500,
  "tokens_to_safety": 0,
  "history_length": 0
}
```

### 5. Get Available Tokens (with buffer)

```http
GET /tokens/available-tokens/google/gemini-pro
?used_tokens=5000&buffer=500
```

**Response:**

```json
{
  "model": "google/gemini-pro",
  "available_tokens": 24500,
  "buffer": 500,
  "used_tokens": 5000,
  "context_window": 30000,
  "is_safe": true,
  "percentage_used": 16.67
}
```

### 6. Check if Text Fits

```http
POST /tokens/check-fit
?text=New%20message&model=google/gemini-pro&used_tokens=5000&buffer=500
```

**Response:**

```json
{
  "can_fit": true,
  "text_tokens": 2,
  "available_tokens": 24500,
  "used_tokens": 5000,
  "buffer": 500,
  "shortage": 0,
  "model": "google/gemini-pro"
}
```

### 7. Get All Models Info

```http
GET /tokens/models-info
```

**Response:**

```json
{
  "total_models": 8,
  "models": {
    "google/gemini-pro": {
      "provider": "google",
      "max_tokens": 2048,
      "temperature": 0.7,
      "context_window": 30000,
      "max_output_tokens": 2048
    },
    ...
  }
}
```

---

## Integration with LLMService

The LLMService now validates tokens before making API calls:

```python
from app.services.llm_service import LLMService

service = LLMService()

# Generate response with automatic token validation
try:
    response, token_info = await service.generate_response(
        model="google/gemini-pro",
        system_prompt="You are helpful",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=500,
        validate_tokens=True  # ← Validates before API call
    )

    print(f"Response: {response}")
    print(f"Token info: {token_info}")
    # Output token_info:
    # {
    #     "input_tokens": 87,
    #     "output_tokens": 234,
    #     "total_tokens": 321,
    #     "context_status": {...},
    #     "warning": ""
    # }
except Exception as e:
    print(f"Token validation failed: {e}")

# Skip validation if needed
response, token_info = await service.generate_response(
    model="google/gemini-pro",
    system_prompt="You are helpful",
    messages=[...],
    validate_tokens=False  # ← Skip validation
)

# Get token count without API call
token_count = service.get_token_count("Text", "google/gemini-pro")

# Validate separately
validation = service.validate_context("google/gemini-pro", used_tokens=5000)

# Get current context status
status = service.get_context_status("google/gemini-pro")

# Reset context tracking
service.reset_context_manager()
```

---

## Best Practices

### 1. Always Validate Before Processing

```python
# ✅ Good: Validate before processing
validation = TokenCounter.validate_context(model, used_tokens)
if not validation["is_valid"]:
    # Handle error or reduce context
    print(f"Not enough tokens: {validation['remaining']} remaining")
else:
    # Safe to proceed
    response = await service.generate_response(...)
```

### 2. Use Safety Buffers

```python
# ✅ Good: Reserve buffer for unexpected needs
manager = ContextWindowManager(model, buffer=1000)  # Reserve 1000 tokens

# ❌ Bad: No buffer
manager = ContextWindowManager(model, buffer=0)
```

### 3. Monitor Context Usage

```python
# ✅ Good: Track and warn
manager = ContextWindowManager("google/gemini-pro", buffer=500)

# After each message
manager.add_tokens(text, source="user_message")

# Check for warnings
warning = manager.warn_if_approaching_limit()
if warning:
    logger.warning(warning)
```

### 4. Handle Context Overflow

```python
# ✅ Good: Gracefully handle overflow
if not manager.is_safe():
    # Start new conversation or summarize
    manager.reset()
    # Trigger summarization if in thread
    # Re-add only summary of previous context
```

### 5. Configure Model Context Windows

In [app/core/models.py](app/core/models.py):

```python
ModelConfig(
    name=ModelName.GPT_4,
    provider=ModelProvider.OPENAI,
    max_tokens=8192,           # Max output tokens
    context_window=8192,       # Total context window
    # ... other config
)
```

---

## Token Counting Methods

The system uses **approximate token counting** based on word count and provider:

```python
# Approximation formula:
tokens ≈ word_count × tokens_per_word

# Tokens per word by provider:
# - Google (Gemini): 1.3 tokens/word
# - OpenAI (GPT): 1.3 tokens/word
# - Mistral: 1.3 tokens/word
# - Anthropic (Claude): 1.3 tokens/word

# Additional overhead:
# - System prompt: 50 tokens
# - Per message: 10 tokens (for formatting)
```

**Limitations:**

- These are estimates; actual token counts may vary
- For exact counts, use the model's official tokenizer
- Estimates are conservative (slightly higher than actual)

---

## Configuration

### Model Context Windows

Edit [app/core/models.py](app/core/models.py) to adjust context windows:

```python
ModelName.GEMINI_PRO: ModelConfig(
    name=ModelName.GEMINI_PRO,
    provider=ModelProvider.GOOGLE,
    max_tokens=2048,
    context_window=30000,  # ← Adjust here
    # ...
)
```

### Safety Buffer

Adjust buffer when creating manager:

```python
# Larger buffer for safety
manager = ContextWindowManager(model, buffer=2000)

# Smaller buffer for efficiency
manager = ContextWindowManager(model, buffer=100)
```

### Token Estimation

Adjust per-word estimation in [app/core/token_counter.py](app/core/token_counter.py):

```python
TOKENS_PER_WORD = {
    "google": 1.3,      # ← Adjust these
    "openai": 1.3,
    "mistralai": 1.3,
    "anthropic": 1.3,
}
```

---

## Troubleshooting

### Issue: Token validation always fails

**Solution:** Check if context_window is configured correctly:

```python
config = get_model_config("your/model")
print(f"Context window: {config.context_window}")
print(f"Max tokens: {config.max_tokens}")
```

### Issue: Token counts seem too high

**Solution:** Token estimates are conservative. For exact counts:

```python
# Use official tokenizer
import tiktoken
encoding = tiktoken.encoding_for_model("gpt-4")
tokens = len(encoding.encode("text"))
```

### Issue: Model not found

**Solution:** Ensure model is in [app/core/models.py](app/core/models.py):

```python
ModelName.YOUR_MODEL = "provider/model-name"

# Then add to MODEL_CONFIGS:
ModelName.YOUR_MODEL: ModelConfig(...)
```

### Issue: Context window exceeded

**Solution:** Implement context compression:

```python
# Summarize old messages
summary = await summarization_service.summarize_messages(old_messages)

# Reset manager
manager.reset()

# Add only summary
manager.add_tokens(summary, source="context_summary")
```

---

## Examples

### Example 1: Single Message Processing

```python
from app.core.token_counter import TokenCounter

model = "google/gemini-pro"
message = "What is the capital of France?"

# Count tokens
tokens = TokenCounter.count_tokens(message, model)
print(f"Message uses {tokens} tokens")

# Validate
validation = TokenCounter.validate_context(model, tokens)
if validation["is_valid"]:
    # Safe to process
    response = await service.generate_response(model, message)
```

### Example 2: Conversation with Token Tracking

```python
from app.core.token_counter import ContextWindowManager

manager = ContextWindowManager("google/gemini-pro")
messages = []

while True:
    user_input = input("You: ")

    # Check if fits
    if not manager.can_fit(user_input):
        print("Context window full. Starting new conversation.")
        manager.reset()

    # Add user message
    manager.add_tokens(user_input, source="user")
    messages.append({"role": "user", "content": user_input})

    # Get response
    response = await service.generate_response(
        model="google/gemini-pro",
        messages=messages
    )

    # Add response
    manager.add_tokens(response, source="assistant")
    messages.append({"role": "assistant", "content": response})

    # Check status
    status = manager.get_status()
    print(f"Assistant: {response}")
    print(f"Context: {status['percentage_used']}% used")

    # Warn if needed
    warning = manager.warn_if_approaching_limit()
    if warning:
        print(warning)
```

### Example 3: Batch Processing with Validation

```python
from app.core.token_counter import TokenCounter

async def process_batch(messages, model):
    """Process multiple messages safely."""

    # Count total tokens
    total_tokens = TokenCounter.count_messages_tokens(messages, model)

    # Validate
    validation = TokenCounter.validate_context(model, total_tokens)

    if not validation["is_valid"]:
        raise Exception(
            f"Batch too large: {total_tokens} tokens "
            f"exceeds {validation['remaining']} remaining"
        )

    # Process safely
    results = []
    for msg in messages:
        response = await service.generate_response(model, [msg])
        results.append(response)

    return results
```

---

## API Examples

### Using cURL

```bash
# Count tokens
curl "http://localhost:8000/tokens/count?text=Hello&model=google/gemini-pro"

# Validate context
curl "http://localhost:8000/tokens/validate/google/gemini-pro?used_tokens=5000"

# Check if text fits
curl -X POST "http://localhost:8000/tokens/check-fit" \
  -d "text=New message&model=google/gemini-pro&used_tokens=5000"
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Count tokens
response = requests.post(
    f"{BASE_URL}/tokens/count",
    params={
        "text": "Your text here",
        "model": "google/gemini-pro"
    }
)
print(response.json())

# Validate context
response = requests.get(
    f"{BASE_URL}/tokens/validate/google/gemini-pro",
    params={"used_tokens": 5000}
)
print(response.json())

# Check fit
response = requests.post(
    f"{BASE_URL}/tokens/check-fit",
    params={
        "text": "New message",
        "model": "google/gemini-pro",
        "used_tokens": 5000
    }
)
print(response.json())
```

---

## Summary

The token counter system provides:

✅ **Automatic token counting** with provider-specific estimation
✅ **Context window validation** to prevent overflow
✅ **Real-time tracking** via ContextWindowManager
✅ **Safety buffers** to reserve tokens
✅ **REST API endpoints** for external use
✅ **Integration** with LLMService for validation
✅ **Warning system** when approaching limits
✅ **Easy configuration** in ModelConfig

Start by checking [app/core/models.py](app/core/models.py) to see model context windows, then use the appropriate API endpoint or class for your use case!
