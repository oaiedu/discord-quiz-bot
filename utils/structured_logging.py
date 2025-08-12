import logging
import json
import sys
from datetime import datetime, timezone

class StructuredLogger:
    """Logger estructurado para Google Cloud Run"""
    
    def __init__(self, name="discord-quiz-bot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remover handlers existentes
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        
        # Crear handler para stdout (Cloud Run captura esto)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Formatter personalizado para JSON estructurado
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
    def info(self, message, **kwargs):
        self.logger.info(message, extra={'severity': 'INFO', **kwargs})
    
    def warning(self, message, **kwargs):
        self.logger.warning(message, extra={'severity': 'WARNING', **kwargs})
    
    def error(self, message, **kwargs):
        self.logger.error(message, extra={'severity': 'ERROR', **kwargs})
    
    def debug(self, message, **kwargs):
        self.logger.debug(message, extra={'severity': 'DEBUG', **kwargs})
    
    def critical(self, message, **kwargs):
        self.logger.critical(message, extra={'severity': 'CRITICAL', **kwargs})

class StructuredFormatter(logging.Formatter):
    """Formatter que convierte logs a JSON estructurado para Google Cloud"""
    
    def format(self, record):
        log_entry = {
            'severity': getattr(record, 'severity', record.levelname),
            'message': record.getMessage(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'component': 'discord-quiz-bot',
            'logger': record.name
        }
        
        # Añadir información adicional si está disponible
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'guild_id'):
            log_entry['guild_id'] = record.guild_id
        
        if hasattr(record, 'command'):
            log_entry['command'] = record.command
        
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        
        # Añadir stack trace para errores
        if record.exc_info:
            log_entry['stack_trace'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Instancia global del logger
structured_logger = StructuredLogger()
