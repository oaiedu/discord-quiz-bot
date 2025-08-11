# Logging Estructurado para Google Cloud Run

Este proyecto utiliza logging estructurado para generar logs en formato JSON que Google Cloud Run puede procesar correctamente, mostrando diferentes niveles de gravedad.

## Tipos de Logs Disponibles

### 1. INFO (Información general)
```python
from utils.structured_logging import structured_logger as logger

logger.info("Usuario ejecutó comando quiz", 
           user_id="12345", 
           guild_id="67890", 
           command="quiz",
           topic="mathematics")
```

### 2. WARNING (Advertencias)
```python
logger.warning("Usuario intentó usar comando sin permisos", 
              user_id="12345", 
              guild_id="67890", 
              command="admin_command",
              missing_role="faculty")
```

### 3. ERROR (Errores)
```python
logger.error("Error al conectar con la base de datos", 
            operation="database_connection",
            error_type="ConnectionError",
            retry_count=3)
```

### 4. DEBUG (Información de depuración)
```python
logger.debug("Estado interno del quiz", 
            user_id="12345",
            current_question=3,
            total_questions=5,
            score=2)
```

### 5. CRITICAL (Errores críticos)
```python
logger.critical("Bot perdió conexión con Discord", 
               error_type="ConnectionLost",
               uptime_seconds=3600,
               last_heartbeat="2024-01-01T12:00:00Z")
```

## Campos Estructurados Recomendados

### Para operaciones de usuario:
- `user_id`: ID del usuario de Discord
- `guild_id`: ID del servidor de Discord
- `command`: Comando ejecutado
- `username`: Nombre del usuario

### Para operaciones de base de datos:
- `operation`: Tipo de operación (create, read, update, delete)
- `collection`: Colección de Firestore
- `document_id`: ID del documento
- `error_type`: Tipo de excepción si hay error

### Para operaciones del sistema:
- `component`: Componente del sistema
- `resource_usage`: Uso de recursos
- `response_time_ms`: Tiempo de respuesta
- `status_code`: Código de estado

## Visualización en Google Cloud Console

Los logs aparecerán en Cloud Console con:
- **Severity**: INFO, WARNING, ERROR, DEBUG, CRITICAL
- **Timestamp**: Marca de tiempo UTC
- **Component**: discord-quiz-bot
- **Campos personalizados**: Todos los kwargs adicionales

### Filtros útiles en Cloud Console:

```
# Solo errores
severity >= ERROR

# Logs de un usuario específico
jsonPayload.user_id = "123456789"

# Logs de comandos específicos
jsonPayload.command = "quiz"

# Errores de base de datos
jsonPayload.operation != "" AND severity >= ERROR
```

## Mejores Prácticas

1. **Consistencia**: Usa siempre los mismos nombres de campos
2. **Contexto**: Incluye información suficiente para debug
3. **No PII**: Evita información personal identificable
4. **Estructura**: Usa kwargs para datos estructurados
5. **Severity apropiada**: Usa el nivel correcto de gravedad

### Ejemplo de log completo:
```json
{
  "severity": "ERROR",
  "message": "❌ Error al ejecutar quiz: Database timeout",
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
