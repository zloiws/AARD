"""
System Setting Service for managing application configuration
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.system_setting import SystemSetting, SettingValueType, SettingCategory
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SystemSettingService:
    """Service for managing system settings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by key
        
        Args:
            key: Setting key (e.g., 'feature.planning.enabled')
            default: Default value if setting not found
            
        Returns:
            Setting value (typed) or default
        """
        try:
            setting = self.db.query(SystemSetting).filter(
                and_(
                    SystemSetting.key == key,
                    SystemSetting.is_active == True
                )
            ).first()
            
            if setting:
                return setting.get_typed_value()
            return default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}", exc_info=True)
            return default
    
    def set_setting(
        self,
        key: str,
        value: Any,
        category: str,
        module: Optional[str] = None,
        description: Optional[str] = None,
        value_type: Optional[SettingValueType] = None,
        updated_by: Optional[str] = None
    ) -> SystemSetting:
        """
        Set or update a setting
        
        Args:
            key: Setting key
            value: Setting value
            category: Setting category (feature, logging, module, system)
            module: Module name if applicable
            description: Setting description
            value_type: Value type (auto-detected if not provided)
            updated_by: Who updated the setting
            
        Returns:
            Updated or created SystemSetting
        """
        try:
            # Check if setting exists
            setting = self.db.query(SystemSetting).filter(
                SystemSetting.key == key
            ).first()
            
            if setting:
                # Update existing
                setting.set_typed_value(value, value_type)
                setting.category = category
                setting.module = module
                # Reactivate setting if it was previously soft-deleted
                setting.is_active = True
                if description:
                    setting.description = description
                setting.updated_by = updated_by
                logger.info(f"Updated setting: {key} = {value}")
            else:
                # Create new
                setting = SystemSetting(
                    key=key,
                    category=category,
                    module=module,
                    description=description,
                    updated_by=updated_by
                )
                setting.set_typed_value(value, value_type)
                # Ensure new setting is active
                setting.is_active = True
                self.db.add(setting)
                logger.info(f"Created setting: {key} = {value}")
            
            self.db.commit()
            self.db.refresh(setting)
            return setting
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error setting {key}: {e}", exc_info=True)
            raise
    
    def get_feature_flag(self, feature: str) -> bool:
        """
        Get feature flag value
        
        Args:
            feature: Feature name (e.g., 'planning', 'agent_ops')
            
        Returns:
            True if feature is enabled, False otherwise
        """
        key = f"feature.{feature}.enabled"
        return self.get_setting(key, default=False)
    
    def set_feature_flag(
        self,
        feature: str,
        enabled: bool,
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> SystemSetting:
        """
        Set feature flag
        
        Args:
            feature: Feature name
            enabled: Enable or disable
            description: Feature description
            updated_by: Who updated the flag
            
        Returns:
            SystemSetting
        """
        key = f"feature.{feature}.enabled"
        return self.set_setting(
            key=key,
            value=enabled,
            category=SettingCategory.FEATURE.value,
            description=description or f"Enable {feature} feature",
            value_type=SettingValueType.BOOLEAN,
            updated_by=updated_by
        )
    
    def get_log_level(self, module: Optional[str] = None) -> str:
        """
        Get log level for module or global
        
        Args:
            module: Module name (e.g., 'app.api.chat') or None for global
            
        Returns:
            Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if module:
            key = f"logging.module.{module}.level"
            level = self.get_setting(key)
            if level:
                return level
        
        # Fallback to global
        return self.get_setting("logging.global.level", default="INFO")
    
    def set_log_level(
        self,
        level: str,
        module: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> SystemSetting:
        """
        Set log level for module or global
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Module name or None for global
            updated_by: Who updated the level
            
        Returns:
            SystemSetting
        """
        if module:
            key = f"logging.module.{module}.level"
            description = f"Log level for {module}"
        else:
            key = "logging.global.level"
            description = "Global log level"
        
        return self.set_setting(
            key=key,
            value=level.upper(),
            category=SettingCategory.LOGGING.value,
            module=module,
            description=description,
            value_type=SettingValueType.STRING,
            updated_by=updated_by
        )
    
    def get_all_settings(
        self,
        category: Optional[str] = None,
        module: Optional[str] = None,
        active_only: bool = True
    ) -> List[SystemSetting]:
        """
        Get all settings with optional filtering
        
        Args:
            category: Filter by category
            module: Filter by module
            active_only: Return only active settings
            
        Returns:
            List of SystemSetting objects
        """
        query = self.db.query(SystemSetting)
        
        if active_only:
            query = query.filter(SystemSetting.is_active == True)
        
        if category:
            query = query.filter(SystemSetting.category == category)
        
        if module:
            query = query.filter(SystemSetting.module == module)
        
        return query.order_by(SystemSetting.key).all()
    
    def get_all_feature_flags(self) -> Dict[str, bool]:
        """
        Get all feature flags
        
        Returns:
            Dictionary of feature names to enabled status
        """
        settings = self.get_all_settings(category=SettingCategory.FEATURE.value)
        
        flags = {}
        for setting in settings:
            # Extract feature name from key (feature.{name}.enabled)
            if setting.key.startswith("feature.") and setting.key.endswith(".enabled"):
                feature_name = setting.key[8:-8]  # Remove 'feature.' prefix and '.enabled' suffix
                flags[feature_name] = setting.get_typed_value()
        
        return flags
    
    def get_all_log_levels(self) -> Dict[str, str]:
        """
        Get all log levels (global and per-module)
        
        Returns:
            Dictionary of module names to log levels
        """
        settings = self.get_all_settings(category=SettingCategory.LOGGING.value)
        
        levels = {}
        for setting in settings:
            if setting.key == "logging.global.level":
                levels["_global"] = setting.get_typed_value()
            elif setting.key.startswith("logging.module.") and setting.key.endswith(".level"):
                module_name = setting.key[15:-6]  # Remove 'logging.module.' and '.level'
                levels[module_name] = setting.get_typed_value()
        
        return levels
    
    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting (soft delete by setting is_active=False)
        
        Args:
            key: Setting key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            setting = self.db.query(SystemSetting).filter(
                SystemSetting.key == key
            ).first()
            
            if setting:
                setting.is_active = False
                self.db.commit()
                logger.info(f"Deleted setting: {key}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting setting {key}: {e}", exc_info=True)
            raise
    
    def get_module_settings(self, module: str) -> Dict[str, Any]:
        """
        Get all settings for a specific module
        
        Args:
            module: Module name
            
        Returns:
            Dictionary of setting keys to values
        """
        settings = self.get_all_settings(module=module)
        return {s.key: s.get_typed_value() for s in settings}

