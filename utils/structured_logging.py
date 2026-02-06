import logging
import json
import sys
from datetime import datetime, timezone


class StructuredLogger:
    """Structured logger for Google Cloud Run"""

    def __init__(self, name="discord-quiz-bot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)

        # Create handler for stdout (Cloud Run captures this)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        # Custom formatter for structured JSON logs
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
    """Formatter that converts logs to structured JSON for Google Cloud"""

    def format(self, record):
        log_entry = {
            'severity': getattr(record, 'severity', record.levelname),
            'message': record.getMessage(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'component': 'discord-quiz-bot',
            'logger': record.name
        }

        # Add additional info if available
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        if hasattr(record, 'guild_id'):
            log_entry['guild_id'] = record.guild_id

        if hasattr(record, 'command'):
            log_entry['command'] = record.command

        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type

        # Add stack trace for errors
        if record.exc_info:
            log_entry['stack_trace'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


# Global logger instance
structured_logger = StructuredLogger()
