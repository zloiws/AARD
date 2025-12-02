"""
Logging configuration with module-level control
"""
import logging
import sys
from typing import Dict, Optional
from app.core.config import get_settings


class LoggingConfig:
    """Centralized logging configuration"""
    
    _configured = False
    _module_levels: Dict[str, str] = {}
    
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
                import json
                custom_levels = json.loads(settings.log_module_levels)
                default_levels.update(custom_levels)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Merge with provided levels
        if module_levels:
            default_levels.update(module_levels)
        
        cls._module_levels = default_levels
        
        # Configure root logger
        root_level = default_levels.get("root", "INFO")
        logging.basicConfig(
            level=getattr(logging, root_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Configure module-specific loggers
        for module, level in default_levels.items():
            if module != "root":
                logger = logging.getLogger(module)
                logger.setLevel(getattr(logging, level.upper()))
                # Prevent propagation to root if we want separate handling
                if module.startswith("sqlalchemy") or module.startswith("uvicorn"):
                    logger.propagate = False
        
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


# Initialize on import
LoggingConfig.configure()

