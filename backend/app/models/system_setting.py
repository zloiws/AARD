"""
System Setting model for centralized configuration management
"""
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class SettingValueType(str, Enum):
    """Setting value type enumeration"""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    JSON = "json"


class SettingCategory(str, Enum):
    """Setting category enumeration"""
    FEATURE = "feature"
    LOGGING = "logging"
    MODULE = "module"
    SYSTEM = "system"


class SystemSetting(Base):
    """
    System Setting model for storing application configuration in database
    
    Enables dynamic configuration without requiring restart:
    - Feature flags (enable/disable features)
    - Logging levels per module
    - Module-specific settings
    - System parameters
    """
    __tablename__ = "system_settings"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Key identification
    key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Value storage
    value = Column(Text, nullable=True)  # Stored as string, converted based on value_type
    value_type = Column(String(20), nullable=False, default=SettingValueType.STRING.value)
    
    # Categorization
    category = Column(String(50), nullable=False, index=True)
    module = Column(String(100), nullable=True, index=True)  # e.g., 'app.api.chat', 'app.services.planning'
    
    # Metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    updated_by = Column(String(255), nullable=True)  # Who updated the setting
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_settings_category_active', 'category', 'is_active'),
        Index('idx_settings_module', 'module'),
    )
    
    def __repr__(self):
        return f"<SystemSetting(key='{self.key}', value='{self.value}', category='{self.category}')>"
    
    def get_typed_value(self) -> Any:
        """Convert stored string value to appropriate type"""
        if self.value is None:
            return None
        
        value_type = self.value_type.lower() if isinstance(self.value_type, str) else self.value_type.value
        
        if value_type == SettingValueType.BOOLEAN.value:
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == SettingValueType.INTEGER.value:
            return int(self.value)
        elif value_type == SettingValueType.FLOAT.value:
            return float(self.value)
        elif value_type == SettingValueType.JSON.value:
            return json.loads(self.value)
        else:  # STRING
            return self.value
    
    def set_typed_value(self, value: Any, value_type: Optional[SettingValueType] = None):
        """Set value with automatic type conversion"""
        if value_type:
            self.value_type = value_type.value if isinstance(value_type, Enum) else value_type
        
        # Auto-detect type if not specified
        if not value_type:
            if isinstance(value, bool):
                self.value_type = SettingValueType.BOOLEAN.value
            elif isinstance(value, int):
                self.value_type = SettingValueType.INTEGER.value
            elif isinstance(value, float):
                self.value_type = SettingValueType.FLOAT.value
            elif isinstance(value, (dict, list)):
                self.value_type = SettingValueType.JSON.value
            else:
                self.value_type = SettingValueType.STRING.value
        
        # Convert to string for storage
        if self.value_type == SettingValueType.JSON.value:
            self.value = json.dumps(value)
        elif self.value_type == SettingValueType.BOOLEAN.value:
            self.value = str(bool(value)).lower()
        else:
            self.value = str(value)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "key": self.key,
            "value": self.get_typed_value(),
            "value_type": self.value_type,
            "category": self.category,
            "module": self.module,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by
        }

