# Variable Naming Conventions

This document outlines the naming conventions used throughout the Discord Quiz Bot codebase to ensure consistency and maintainability.

## Overview

The codebase follows **PEP 8 Python naming conventions** with some specific patterns tailored to the project's architecture.

---

## Python Naming Conventions

### 1. **Variables & Parameters** - `snake_case`

All local variables, function parameters, and instance variables use lowercase with underscores separating words.

**Examples:**
```python
user_id = "12345"
guild_id = interaction.guild.id
topic_name = "Mathematics"
correct_answer = True
xp_change = 50
user_data = user_ref.get().to_dict()
new_xp = max(0, current_xp + xp_change)
question_type = QuestionType.TRUE_FALSE
```

**Guidelines:**
- Use descriptive names that indicate the data type or purpose
- Avoid single-letter variables except in loops (`i`, `j`, `x`) or when mathematically conventional
- Use `_id` suffix for identifier fields (user_id, guild_id, topic_id)
- Use `_name` suffix for string names (user_name, guild_name, channel_name)
- Use `_data` suffix for dictionary/object data (user_data, topic_data)

### 2. **Functions & Methods** - `snake_case`

All function and method names use lowercase with underscores.

**Examples:**
```python
def is_professor(interaction: discord.Interaction) -> bool:
    pass

def get_user_xp(user_id: str, guild_id: str):
    pass

def add_xp(user_id: str, guild_id: str, xp_change: int):
    pass

async def autocomplete_topics(interaction: discord.Interaction, current: str):
    pass

def calculate_level(xp: int) -> int:
    pass

def get_topics_for_autocomplete(guild_id: int):
    pass
```

**Guidelines:**
- Use verb-noun combinations for clarity (e.g., `get_user_xp`, `add_xp`, `register_user`)
- Use `is_` prefix for boolean-returning functions (e.g., `is_professor`)
- Use `get_` prefix for retrieval functions
- Use `update_` or `set_` prefix for modification functions
- Use `async def` for asynchronous functions (Discord interaction handlers)

### 3. **Classes** - `PascalCase`

Class names use uppercase first letter of each word (no underscores).

**Examples:**
```python
class StructuredLogger:
    pass

class PaginationView(discord.ui.View):
    pass

class QuestionType(Enum):
    pass
```

**Guidelines:**
- Use PascalCase for all class names
- Descriptive names indicating the purpose or entity type
- Inherit from appropriate base classes

### 4. **Constants** - `UPPER_SNAKE_CASE`

Module-level constants use all uppercase with underscores.

**Examples:**
```python
ROLE_PROFESSOR = "faculty"
DOCS_PATH = "docs"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "mistralai/mistral-7b-instruct:free"
SECRET_NAME = "firebase-config"
SERVICE_NAME = "discord-quiz-bot"
REGION = "us-central1"
```

**Guidelines:**
- Use for values that never change
- Environment-based configuration values
- Magic numbers should be named constants
- All uppercase with underscores separating words

### 5. **Private Variables & Methods** - `_leading_underscore`

Variables and methods intended for internal use only start with a single underscore.

**Examples:**
```python
def _format_log_entry(self, data):
    pass

_internal_state = {}
```

**Guidelines:**
- Signals to other developers this is internal/private
- Not meant to be part of public API
- Can be safely refactored without breaking external code

### 6. **Dunder (Magic) Methods** - `__double_underscore__`

Special Python methods use double underscores on both sides.

**Examples:**
```python
def __init__(self, name="discord-quiz-bot"):
    pass

def __str__(self):
    pass
```

---

## Structured Logging Fields

### Log Field Naming - `snake_case`

All logging fields use snake_case for consistency with structured logging best practices.

**User Operation Fields:**
```python
user_id = "12345"
guild_id = "67890"
username = "username"
command = "quiz"
user_display_name = "Display Name"
is_professor = True
```

**Database Operation Fields:**
```python
operation = "get_user_xp"  # Type of operation
collection = "servers"
document_id = "doc_123"
error_type = "ConnectionError"
```

**System Operation Fields:**
```python
component = "discord-quiz-bot"
resource_usage = "512Mi"
response_time_ms = 250
status_code = 200
```

**Example Full Log:**
```python
logger.info(
    "User executed quiz command",
    user_id="12345",
    guild_id="67890",
    command="quiz",
    topic="mathematics",
    question_number=3,
    correct_answer=True
)
```

---

## Shell Script Variables

### Environment Variables - `UPPER_SNAKE_CASE`

Exported environment variables use all uppercase.

**Examples:**
```bash
export PROJECT_ID="my-project-id"
export DISCORD_TOKEN="token123"
export OPENROUTER_API_KEY="key123"
export GCS_BUCKET_NAME="bucket-name"
export GOOGLE_CLOUD_PROJECT="project-id"
export SERVICE_NAME="discord-quiz-bot"
export REGION="us-central1"
export IMAGE_NAME="region-docker.pkg.dev/project/repo/image"
```

### Local Shell Variables - `snake_case`

Local script variables use lowercase for clarity.

**Examples:**
```bash
response=""
cleanup() {
    rm -f firebase_config.json
}
```

---

## Firestore Collection & Document Fields

### Collection Names - `lowercase`

Firestore collections use lowercase names.

**Examples:**
```
servers/         # Server configurations
users/           # User data
topics/          # Quiz topics
questions/       # Quiz questions
stats/           # User statistics
```

### Document Fields - `snake_case`

All document field names use snake_case.

**Examples:**
```javascript
{
    user_id: "12345",
    guild_id: "67890",
    xp: 150,
    level: 2,
    user_name: "username",
    created_at: timestamp,
    last_quiz_date: timestamp,
    correct_answers: 10,
    total_attempts: 15,
    topic_id: "topic_123"
}
```

---

## Discord-Specific Naming

### Discord API Objects

These inherit Discord.py naming conventions and should not be changed:

```python
interaction: discord.Interaction  # Discord interaction object
message: discord.Message          # Discord message object
user: discord.User                # Discord user object
guild: discord.Guild              # Discord server object
channel: discord.TextChannel      # Discord channel object
member: discord.Member            # Discord server member object
```

---

## Summary Table

| Convention | Usage | Example |
|-----------|-------|---------|
| `snake_case` | Variables, parameters, functions, methods | `user_id`, `get_user_xp()`, `topic_name` |
| `PascalCase` | Classes | `StructuredLogger`, `PaginationView` |
| `UPPER_SNAKE_CASE` | Constants, environment variables | `ROLE_PROFESSOR`, `PROJECT_ID` |
| `_snake_case` | Private methods/variables | `_format_log_entry` |
| `__dunder__` | Magic/special methods | `__init__`, `__str__` |

---

## Best Practices

1. **Be Descriptive**: Use full words instead of abbreviations where possible
   - ✅ `user_id` instead of `uid`
   - ✅ `question_type` instead of `qtype`

2. **Consistency**: Match existing patterns in the codebase
   - Always use `_id` suffix for identifiers
   - Always use `get_` prefix for retrieval functions

3. **Type Hints**: Include type hints in function signatures
   ```python
   def add_xp(user_id: str, guild_id: str, xp_change: int) -> None:
       pass
   ```

4. **Docstrings**: Document functions with clear descriptions
   ```python
   def calculate_level(xp: int) -> int:
       """Calculate user level based on XP (100 XP per level)."""
       return xp // 100 + 1
   ```

5. **Avoid Magic Numbers**: Use named constants
   - ❌ `new_xp = xp + 50`
   - ✅ `xp_reward = 50; new_xp = xp + xp_reward`

6. **Use English**: All code, comments, and documentation in English (as per project standards)

---

## References

- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Google Cloud Naming Conventions](https://cloud.google.com/docs/styleguide)
- [Firestore Best Practices](https://firebase.google.com/docs/firestore/best-practices)
