"""
Unified logging configuration with structured JSON logging, context support, and multiple handlers
"""
import logging
import sys
import json
import re
from pathlib import Path
from typing import Dict, Optional, Any
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime
from app.core.config import get_settings

# Context variables for request context
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages"""
    
    SENSITIVE_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', r'password": "***"'),
        (r'password\s*=\s*([^\s&]+)', r'password=***'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', r'token": "***"'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', r'api_key": "***"'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', r'secret": "***"'),
        (r'auth["\']?\s*[:=]\s*["\']?([^"\'\s&]+)', r'auth": "***"'),
        (r'Bearer\s+([^\s"]+)', r'Bearer ***'),
        (r'Authorization:\s*([^\s"]+)', r'Authorization: ***'),
    ]
    
    def __init__(self, enabled: bool = True):
        super().__init__()
        self.enabled = enabled
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data"""
        if not self.enabled:
            return True
        
        # Mask sensitive data in message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        
        # Mask sensitive data in args
        if hasattr(record, 'args') and record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_arg = arg
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        masked_arg = re.sub(pattern, replacement, masked_arg, flags=re.IGNORECASE)
                    new_args.append(masked_arg)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        
        return True


class ContextualFormatter(logging.Formatter):
    """JSON formatter with context support (custom implementation without external dependencies)"""
    
    def __init__(self, *args, **kwargs):
        # Remove format string if provided (we don't use it for JSON)
        kwargs.pop('fmt', None)
        # Store datefmt if provided
        self.datefmt = kwargs.pop('datefmt', None)
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_dict = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add context from contextvars
        ctx = request_context.get({})
        if ctx:
            log_dict.update(ctx)
        
        # Add extra fields from record
        if hasattr(record, 'taskName') and record.taskName:
            log_dict['taskName'] = record.taskName
        
        # Add exception info if present
        if record.exc_info:
            log_dict['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields from record (from extra= parameter in logging calls)
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread', 'threadName',
                          'exc_info', 'exc_text', 'stack_info', 'taskName',
                          'exc_info', 'exc_text', 'stack_info']:
                # Only include serializable values
                try:
                    # Test if serializable
                    json.dumps(value, default=str)
                    log_dict[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable to string
                    log_dict[key] = str(value)
        
        return json.dumps(log_dict, ensure_ascii=False, default=str)


class LoggingConfig:
    """Centralized logging configuration with structured logging support"""
    
    _configured = False
    _module_levels: Dict[str, str] = {}
    _log_metrics: Dict[str, int] = {
        'DEBUG': 0,
        'INFO': 0,
        'WARNING': 0,
        'ERROR': 0,
        'CRITICAL': 0,
    }
    
    @classmethod
    def configure(cls, module_levels: Optional[Dict[str, str]] = None):
        """Configure logging for the application"""
        if cls._configured:
            return
        
        settings = get_settings()
        
        # Determine SQLAlchemy log level
        sqlalchemy_level = "INFO" if settings.log_sqlalchemy else "WARNING"
        uvicorn_access_level = "INFO" if settings.log_uvicorn_access else "WARNING"
        
        # Default module levels
        default_levels = {
            "sqlalchemy.engine": sqlalchemy_level,
            "sqlalchemy.pool": "WARNING",
            "sqlalchemy.dialects": "WARNING",
            "uvicorn.access": uvicorn_access_level,
            "uvicorn.error": "INFO",
            "app": settings.log_level,
            "root": settings.log_level,
        }
        
        # Parse module-specific levels from settings
        if settings.log_module_levels:
            try:
                custom_levels = json.loads(settings.log_module_levels)
                default_levels.update(custom_levels)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Merge with provided levels
        if module_levels:
            default_levels.update(module_levels)
        
        cls._module_levels = default_levels
        
        # Choose formatter based on settings
        if settings.log_format.lower() == "json":
            formatter = ContextualFormatter(
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Create handlers
        handlers = []
        
        # Console handler (always enabled)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter(enabled=not settings.log_sensitive_data))
        handlers.append(console_handler)
        
        # File handler (if enabled)
        if settings.log_file_enabled:
            log_path = Path(settings.log_file_path)
            # Resolve relative to project root
            if not log_path.is_absolute():
                _current_file = Path(__file__).resolve()
                _backend_dir = _current_file.parent.parent.parent
                _project_root = _backend_dir.parent
                log_path = _project_root / log_path
            
            # Create log directory if it doesn't exist
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine rotation parameters
            if settings.log_file_rotation in ['midnight', 'W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6']:
                when = settings.log_file_rotation
                interval = 1
            elif settings.log_file_rotation.endswith(('KB', 'MB', 'GB')):
                # Size-based rotation (handled differently)
                when = 'midnight'
                interval = 1
            else:
                when = 'midnight'
                interval = 1
            
            file_handler = TimedRotatingFileHandler(
                filename=str(log_path),
                when=when,
                interval=interval,
                backupCount=settings.log_file_retention,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter(enabled=not settings.log_sensitive_data))
            handlers.append(file_handler)
        
        # Configure root logger
        root_level = default_levels.get("root", "INFO")
        logging.basicConfig(
            level=getattr(logging, root_level.upper()),
            handlers=handlers,
            force=True  # Override existing configuration
        )
        
        # Configure module-specific loggers
        for module, level in default_levels.items():
            if module != "root":
                logger = logging.getLogger(module)
                logger.setLevel(getattr(logging, level.upper()))
                # Prevent propagation to root if we want separate handling
                if module.startswith("sqlalchemy") or module.startswith("uvicorn"):
                    logger.propagate = False
        
        # Add metrics handler to track log counts
        metrics_handler = cls._MetricsHandler()
        metrics_handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        root_logger.addHandler(metrics_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger for a module"""
        if not cls._configured:
            cls.configure()
        return logging.getLogger(name)
    
    @classmethod
    def set_module_level(cls, module: str, level: str):
        """Set logging level for a specific module"""
        logger = logging.getLogger(module)
        logger.setLevel(getattr(logging, level.upper()))
        cls._module_levels[module] = level
    
    @classmethod
    def get_module_level(cls, module: str) -> str:
        """Get logging level for a specific module"""
        logger = logging.getLogger(module)
        return logging.getLevelName(logger.level)
    
    @classmethod
    def set_context(cls, **kwargs):
        """Set context variables for logging"""
        ctx = request_context.get({}).copy()
        ctx.update(kwargs)
        request_context.set(ctx)
    
    @classmethod
    def clear_context(cls):
        """Clear context variables"""
        request_context.set({})
    
    @classmethod
    def get_metrics(cls) -> Dict[str, int]:
        """Get logging metrics"""
        return cls._log_metrics.copy()
    
    @classmethod
    def reset_metrics(cls):
        """Reset logging metrics"""
        cls._log_metrics = {
            'DEBUG': 0,
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'CRITICAL': 0,
        }
    
    class _MetricsHandler(logging.Handler):
        """Handler to track log metrics"""
        
        def emit(self, record: logging.LogRecord):
            """Count logs by level"""
            level = record.levelname
            if level in LoggingConfig._log_metrics:
                LoggingConfig._log_metrics[level] += 1


# Initialize on import
LoggingConfig.configure()
