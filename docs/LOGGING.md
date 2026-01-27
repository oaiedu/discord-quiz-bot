# Structured Logging for Google Cloud Run

This project uses structured logging to generate logs in JSON format that Google Cloud Run can process correctly, displaying different severity levels.

## Available Log Types

### 1. INFO (General information)
```python
from utils.structured_logging import structured_logger as logger

logger.info("User executed quiz command", 
           user_id="12345", 
           guild_id="67890", 
           command="quiz",
           topic="mathematics")
```

### 2. WARNING (Warnings)
```python
logger.warning("User attempted to use command without permissions", 
              user_id="12345", 
              guild_id="67890", 
              command="admin_command",
              missing_role="faculty")
```

### 3. ERROR (Errors)
```python
logger.error("Error connecting to the database", 
            operation="database_connection",
            error_type="ConnectionError",
            retry_count=3)
```

### 4. DEBUG (Debug information)
```python
logger.debug("Quiz internal state", 
            user_id="12345",
            current_question=3,
            total_questions=5,
            score=2)
```

### 5. CRITICAL (Critical errors)
```python
logger.critical("Bot lost connection with Discord", 
               error_type="ConnectionLost",
               uptime_seconds=3600,
               last_heartbeat="2024-01-01T12:00:00Z")
```

## Recommended Structured Fields

### For user operations:
- `user_id`: Discord user ID
- `guild_id`: Discord server ID
- `command`: Executed command
- `username`: Username

### For database operations:
- `operation`: Type of operation (create, read, update, delete)
- `collection`: Firestore collection
- `document_id`: Document ID
- `error_type`: Exception type if there is an error

### For system operations:
- `component`: System component
- `resource_usage`: Resource usage
- `response_time_ms`: Response time
- `status_code`: Status code

## Viewing in Google Cloud Console

Logs will appear in Cloud Console with:
- **Severity**: INFO, WARNING, ERROR, DEBUG, CRITICAL
- **Timestamp**: UTC timestamp
- **Component**: discord-quiz-bot
- **Custom fields**: All additional kwargs

### Useful filters in Cloud Console:

```
# Only errors
severity >= ERROR

# Logs from a specific user
jsonPayload.user_id = "123456789"

# Logs from specific commands
jsonPayload.command = "quiz"

# Database errors
jsonPayload.operation != "" AND severity >= ERROR
```

## Best Practices

1. **Consistency**: Always use the same field names
2. **Context**: Include enough information for debugging
3. **No PII**: Avoid personally identifiable information
4. **Structure**: Use kwargs for structured data
5. **Appropriate Severity**: Use the correct severity level

### Example of complete log:
```json
{
  "severity": "ERROR",
  "message": "❌ Error executing quiz: Database timeout",
  "timestamp": "2024-01-01T12:00:00+00:00",
  "component": "discord-quiz-bot",
  "user_id": "123456789",
  "guild_id": "987654321",
  "command": "quiz",
  "operation": "quiz_execution",
  "error_type": "TimeoutError",
  "topic": "mathematics",
  "question_number": 3
}
```
