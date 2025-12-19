"""
Скрипт для переноса настроек из .env в БД
Миграция feature flags и logging настроек
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir.parent / ".env")

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.system_setting import SettingCategory
from app.services.system_setting_service import SystemSettingService

logger = LoggingConfig.get_logger(__name__)


def migrate_feature_flags(service: SystemSettingService, settings):
    """Миграция feature flags из .env в БД"""
    print("\n" + "="*70)
    print(" Миграция Feature Flags")
    print("="*70)
    
    feature_flags = {
        'agent_ops': settings.enable_agent_ops,
        'a2a': settings.enable_a2a,
        'planning': settings.enable_planning,
        'tracing': settings.enable_tracing,
        'caching': settings.enable_caching,
    }
    
    for feature, enabled in feature_flags.items():
        try:
            service.set_feature_flag(
                feature=feature,
                enabled=enabled,
                description=f"Enable {feature.replace('_', ' ').title()} feature",
                updated_by="env_migration"
            )
            status = "[+] Enabled" if enabled else "[-] Disabled"
            print(f"  {feature:20} {status}")
        except Exception as e:
            print(f"  {feature:20} [!] Error: {e}")


def migrate_logging_settings(service: SystemSettingService, settings):
    """Миграция logging настроек из .env в БД"""
    print("\n" + "="*70)
    print(" Миграция Logging настроек")
    print("="*70)
    
    # Глобальный уровень логирования
    try:
        service.set_log_level(
            level=settings.log_level,
            module=None,  # Global
            updated_by="env_migration"
        )
        print(f"  Global log level: {settings.log_level}")
    except Exception as e:
        print(f"  Global log level: ❌ Error: {e}")
    
    # Модульные уровни логирования (дефолты для основных модулей)
    module_defaults = {
        # API Routes
        'app.api.routes.chat': 'INFO',
        'app.api.routes.agents': 'INFO',
        'app.api.routes.plans': 'INFO',
        'app.api.routes.benchmarks': 'INFO',
        
        # Services
        'app.services.planning_service': 'INFO',
        'app.services.execution_service': 'INFO',
        'app.services.agent_dialog_service': 'DEBUG',
        'app.services.agent_service': 'INFO',
        'app.services.tool_service': 'INFO',
        'app.services.memory_service': 'INFO',
        'app.services.workflow_event_service': 'WARNING',
        
        # Core
        'app.core.ollama_client': 'WARNING',
        'app.core.request_router': 'INFO',
        'app.core.tracing': 'WARNING',
    }
    
    print("\nУстановка дефолтных уровней для модулей:")
    for module, level in module_defaults.items():
        try:
            service.set_log_level(
                level=level,
                module=module,
                updated_by="env_migration"
            )
            print(f"  {module:50} {level}")
        except Exception as e:
            print(f"  {module:50} ❌ Error: {e}")


def migrate_module_settings(service: SystemSettingService, settings):
    """Миграция дополнительных настроек модулей"""
    print("\n" + "="*70)
    print(" Миграция дополнительных настроек")
    print("="*70)
    
    # Системные настройки из config.py
    additional_settings = [
        # LLM Settings
        {
            'key': 'system.llm.timeout_seconds',
            'value': settings.llm_timeout_seconds,
            'category': SettingCategory.SYSTEM.value,
            'description': 'LLM timeout in seconds (max wait time for response)'
        },
        {
            'key': 'system.llm.max_tokens',
            'value': settings.llm_max_tokens,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Maximum tokens in LLM response (controls output length)'
        },
        {
            'key': 'system.llm.temperature',
            'value': settings.llm_temperature,
            'category': SettingCategory.SYSTEM.value,
            'description': 'LLM temperature (0.0-1.0, lower = more deterministic)'
        },
        {
            'key': 'system.llm.top_p',
            'value': settings.llm_top_p,
            'category': SettingCategory.SYSTEM.value,
            'description': 'LLM top-p sampling (0.0-1.0)'
        },
        {
            'key': 'system.llm.num_ctx',
            'value': settings.llm_num_ctx,
            'category': SettingCategory.SYSTEM.value,
            'description': 'LLM context window size in tokens'
        },
        
        # Planning Settings
        {
            'key': 'system.planning.timeout_seconds',
            'value': settings.planning_timeout_seconds,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Planning timeout in seconds'
        },
        {
            'key': 'system.planning.max_steps',
            'value': settings.planning_max_steps,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Maximum steps allowed in a single plan'
        },
        
        # Execution Settings
        {
            'key': 'system.execution.timeout_seconds',
            'value': settings.execution_timeout_seconds,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Step execution timeout in seconds'
        },
        {
            'key': 'system.execution.max_total_timeout_seconds',
            'value': settings.execution_max_total_timeout_seconds,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Maximum total plan execution time in seconds'
        },
        
        # Code Execution Settings
        {
            'key': 'system.code_execution.timeout_seconds',
            'value': settings.code_execution_timeout_seconds,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Code execution timeout in sandbox'
        },
        {
            'key': 'system.code_execution.memory_limit_mb',
            'value': settings.code_execution_memory_limit_mb,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Memory limit for code execution (MB)'
        },
        
        # Database Settings
        {
            'key': 'system.database.pool_size',
            'value': settings.database_pool_size,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Database connection pool size'
        },
        {
            'key': 'system.database.max_overflow',
            'value': settings.database_max_overflow,
            'category': SettingCategory.SYSTEM.value,
            'description': 'Database pool max overflow connections'
        },
    ]
    
    for setting_data in additional_settings:
        try:
            service.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                category=setting_data['category'],
                description=setting_data['description'],
                updated_by="env_migration"
            )
            print(f"  {setting_data['key']:40} = {setting_data['value']}")
        except Exception as e:
            print(f"  {setting_data['key']:40} ❌ Error: {e}")


def main():
    """Основная функция миграции"""
    print("="*70)
    print(" МИГРАЦИЯ НАСТРОЕК ИЗ .ENV В БД")
    print("="*70)
    
    db = SessionLocal()
    try:
        settings = get_settings()
        service = SystemSettingService(db)
        
        # 1. Мигрировать feature flags
        migrate_feature_flags(service, settings)
        
        # 2. Мигрировать logging настройки
        migrate_logging_settings(service, settings)
        
        # 3. Мигрировать дополнительные настройки
        migrate_module_settings(service, settings)
        
        print("\n" + "="*70)
        print("[OK] MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        
        # Показать сводку
        print("\nСводка:")
        print(f"  Feature flags: {len(service.get_all_feature_flags())}")
        print(f"  Log levels: {len(service.get_all_log_levels())}")
        print(f"  Всего настроек: {len(service.get_all_settings())}")
        
        print("\nТеперь настройки можно управлять через:")
        print("  - API: http://localhost:8000/api/settings")
        print("  - UI: http://localhost:8000/settings (будет реализовано)")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

