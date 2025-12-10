"""
API routes for system settings management
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.services.system_setting_service import SystemSettingService
from app.models.system_setting import SystemSetting, SettingValueType, SettingCategory

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = LoggingConfig.get_logger(__name__)


class SettingResponse(BaseModel):
    """Response model for system setting"""
    id: str
    key: str
    value: Any
    value_type: str
    category: str
    module: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    updated_by: Optional[str]
    
    class Config:
        from_attributes = True


class SettingCreateRequest(BaseModel):
    """Request model for creating/updating setting"""
    key: str = Field(..., description="Setting key")
    value: Any = Field(..., description="Setting value")
    category: str = Field(..., description="Setting category (feature, logging, module, system)")
    module: Optional[str] = Field(None, description="Module name if applicable")
    description: Optional[str] = Field(None, description="Setting description")
    value_type: Optional[str] = Field(None, description="Value type (boolean, string, integer, float, json)")


class FeatureFlagRequest(BaseModel):
    """Request model for feature flag"""
    feature: str = Field(..., description="Feature name (e.g., 'planning', 'agent_ops')")
    enabled: bool = Field(..., description="Enable or disable feature")
    description: Optional[str] = Field(None, description="Feature description")


class LogLevelRequest(BaseModel):
    """Request model for log level"""
    level: str = Field(..., description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    module: Optional[str] = Field(None, description="Module name or null for global")


@router.get("/", response_model=List[SettingResponse])
async def list_settings(
    category: Optional[str] = None,
    module: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all settings with optional filtering"""
    try:
        service = SystemSettingService(db)
        settings = service.get_all_settings(
            category=category,
            module=module,
            active_only=active_only
        )
        
        return [SettingResponse(
            id=str(s.id),
            key=s.key,
            value=s.get_typed_value(),
            value_type=s.value_type,
            category=s.category,
            module=s.module,
            description=s.description,
            is_active=s.is_active,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
            updated_by=s.updated_by
        ) for s in settings]
    except Exception as e:
        logger.error(f"Error listing settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: Session = Depends(get_db)
):
    """Get a specific setting by key"""
    try:
        service = SystemSettingService(db)
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return SettingResponse(
            id=str(setting.id),
            key=setting.key,
            value=setting.get_typed_value(),
            value_type=setting.value_type,
            category=setting.category,
            module=setting.module,
            description=setting.description,
            is_active=setting.is_active,
            created_at=setting.created_at.isoformat() if setting.created_at else None,
            updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
            updated_by=setting.updated_by
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=SettingResponse)
async def create_or_update_setting(
    request: SettingCreateRequest,
    db: Session = Depends(get_db)
):
    """Create or update a setting"""
    try:
        service = SystemSettingService(db)
        
        # Convert value_type string to enum if provided
        value_type = None
        if request.value_type:
            try:
                value_type = SettingValueType(request.value_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value_type. Must be one of: {[v.value for v in SettingValueType]}"
                )
        
        setting = service.set_setting(
            key=request.key,
            value=request.value,
            category=request.category,
            module=request.module,
            description=request.description,
            value_type=value_type,
            updated_by="api"  # TODO: Get from auth context
        )
        
        return SettingResponse(
            id=str(setting.id),
            key=setting.key,
            value=setting.get_typed_value(),
            value_type=setting.value_type,
            category=setting.category,
            module=setting.module,
            description=setting.description,
            is_active=setting.is_active,
            created_at=setting.created_at.isoformat() if setting.created_at else None,
            updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
            updated_by=setting.updated_by
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating setting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: Session = Depends(get_db)
):
    """Delete a setting (soft delete)"""
    try:
        service = SystemSettingService(db)
        success = service.delete_setting(key)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return {"message": f"Setting '{key}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/all", response_model=Dict[str, bool])
async def list_feature_flags(db: Session = Depends(get_db)):
    """List all feature flags"""
    try:
        service = SystemSettingService(db)
        flags = service.get_all_feature_flags()
        return flags
    except Exception as e:
        logger.error(f"Error listing feature flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/{feature}", response_model=bool)
async def get_feature_flag(
    feature: str,
    db: Session = Depends(get_db)
):
    """Get a specific feature flag"""
    try:
        service = SystemSettingService(db)
        enabled = service.get_feature_flag(feature)
        return enabled
    except Exception as e:
        logger.error(f"Error getting feature flag {feature}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/")
async def set_feature_flag(
    request: FeatureFlagRequest,
    db: Session = Depends(get_db)
):
    """Set a feature flag"""
    try:
        service = SystemSettingService(db)
        setting = service.set_feature_flag(
            feature=request.feature,
            enabled=request.enabled,
            description=request.description,
            updated_by="api"  # TODO: Get from auth context
        )
        
        return {
            "feature": request.feature,
            "enabled": setting.get_typed_value(),
            "message": f"Feature '{request.feature}' {'enabled' if request.enabled else 'disabled'}"
        }
    except Exception as e:
        logger.error(f"Error setting feature flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logging/all", response_model=Dict[str, str])
async def list_log_levels(db: Session = Depends(get_db)):
    """List all log levels (global and per-module)"""
    try:
        service = SystemSettingService(db)
        levels = service.get_all_log_levels()
        return levels
    except Exception as e:
        logger.error(f"Error listing log levels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logging/{module}", response_model=str)
async def get_log_level(
    module: str,
    db: Session = Depends(get_db)
):
    """Get log level for a specific module"""
    try:
        service = SystemSettingService(db)
        # "_global" is a special module name for global log level
        if module == "_global":
            module = None
        level = service.get_log_level(module)
        return level
    except Exception as e:
        logger.error(f"Error getting log level for {module}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logging/")
async def set_log_level(
    request: LogLevelRequest,
    db: Session = Depends(get_db)
):
    """Set log level for global or specific module"""
    try:
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if request.level.upper() not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid log level. Must be one of: {valid_levels}"
            )
        
        service = SystemSettingService(db)
        setting = service.set_log_level(
            level=request.level,
            module=request.module,
            updated_by="api"  # TODO: Get from auth context
        )
        
        scope = request.module or "global"
        return {
            "scope": scope,
            "level": setting.get_typed_value(),
            "message": f"Log level for '{scope}' set to {request.level}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting log level: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/all", response_model=List[str])
async def list_modules(db: Session = Depends(get_db)):
    """List all modules that have settings"""
    try:
        settings = db.query(SystemSetting.module).filter(
            SystemSetting.module.isnot(None),
            SystemSetting.is_active == True
        ).distinct().all()
        
        modules = [s.module for s in settings if s.module]
        return sorted(modules)
    except Exception as e:
        logger.error(f"Error listing modules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

