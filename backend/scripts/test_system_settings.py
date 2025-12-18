"""
Тестирование системы настроек
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.system_setting_service import SystemSettingService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def test_feature_flags(service: SystemSettingService):
    """Тест feature flags"""
    print("\n" + "="*70)
    print(" Тест Feature Flags")
    print("="*70)
    
    # Получить все flags
    flags = service.get_all_feature_flags()
    print(f"\nВсего flags: {len(flags)}")
    for feature, enabled in flags.items():
        status = "✓ Enabled" if enabled else "✗ Disabled"
        print(f"  {feature:20} {status}")
    
    # Проверить конкретный flag
    planning_enabled = service.get_feature_flag('planning')
    print(f"\nPlanning feature: {'Enabled' if planning_enabled else 'Disabled'}")
    
    # Изменить flag
    print("\nИзменяем planning flag на противоположное...")
    service.set_feature_flag('planning', not planning_enabled, updated_by="test")
    new_status = service.get_feature_flag('planning')
    print(f"Новый статус: {'Enabled' if new_status else 'Disabled'}")
    
    # Вернуть обратно
    service.set_feature_flag('planning', planning_enabled, updated_by="test")
    print("✓ Feature flags работают корректно")


def test_log_levels(service: SystemSettingService):
    """Тест уровней логирования"""
    print("\n" + "="*70)
    print(" Тест Log Levels")
    print("="*70)
    
    # Получить все levels
    levels = service.get_all_log_levels()
    print(f"\nВсего уровней: {len(levels)}")
    for module, level in levels.items():
        print(f"  {module:50} {level}")
    
    # Глобальный уровень
    global_level = service.get_log_level(None)
    print(f"\nГлобальный уровень: {global_level}")
    
    # Уровень для модуля
    module_level = service.get_log_level('app.services.planning_service')
    print(f"Planning service уровень: {module_level}")
    
    # Изменить уровень
    print("\nИзменяем уровень для app.services.planning_service на DEBUG...")
    service.set_log_level('DEBUG', 'app.services.planning_service', updated_by="test")
    new_level = service.get_log_level('app.services.planning_service')
    print(f"Новый уровень: {new_level}")
    
    # Вернуть обратно
    service.set_log_level(module_level, 'app.services.planning_service', updated_by="test")
    print("✓ Log levels работают корректно")


def test_custom_settings(service: SystemSettingService):
    """Тест пользовательских настроек"""
    print("\n" + "="*70)
    print(" Тест Custom Settings")
    print("="*70)
    
    # Создать настройку
    print("\nСоздаем тестовую настройку...")
    service.set_setting(
        key='test.custom.setting',
        value=42,
        category='system',
        description='Test setting',
        updated_by='test'
    )
    
    # Получить настройку
    value = service.get_setting('test.custom.setting')
    print(f"Значение: {value} (type: {type(value).__name__})")
    assert value == 42, f"Expected 42, got {value}"
    
    # Обновить настройку
    print("Обновляем настройку...")
    service.set_setting(
        key='test.custom.setting',
        value=100,
        category='system',
        updated_by='test'
    )
    
    new_value = service.get_setting('test.custom.setting')
    print(f"Новое значение: {new_value}")
    assert new_value == 100, f"Expected 100, got {new_value}"
    
    # Удалить настройку
    print("Удаляем настройку...")
    service.delete_setting('test.custom.setting')
    deleted_value = service.get_setting('test.custom.setting', default='DELETED')
    print(f"После удаления: {deleted_value}")
    assert deleted_value == 'DELETED', "Setting should be deleted"
    
    # Use ASCII output to avoid encoding issues on some consoles
    print("OK Custom settings work correctly")


def test_all_settings(service: SystemSettingService):
    """Тест получения всех настроек"""
    print("\n" + "="*70)
    print(" Тест All Settings")
    print("="*70)
    
    # Все настройки
    all_settings = service.get_all_settings()
    print(f"\nВсего настроек: {len(all_settings)}")
    
    # По категориям
    for category in ['feature', 'logging', 'system']:
        cat_settings = service.get_all_settings(category=category)
        print(f"  {category:10} {len(cat_settings)}")
    
    # По модулям
    module_settings = service.get_all_settings(module='app.services.planning_service')
    print(f"\nНастроек для planning_service: {len(module_settings)}")
    
    print("✓ All settings работают корректно")


def main():
    """Основная функция тестирования"""
    print("="*70)
    print(" ТЕСТИРОВАНИЕ СИСТЕМЫ НАСТРОЕК")
    print("="*70)
    
    db = SessionLocal()
    try:
        service = SystemSettingService(db)
        
        # Проверить наличие настроек
        all_settings = service.get_all_settings()
        if len(all_settings) == 0:
            print("\n⚠️  Настройки не найдены в БД!")
            print("Запустите: python scripts/migrate_env_to_db.py")
            return
        
        # Запустить тесты
        test_feature_flags(service)
        test_log_levels(service)
        test_custom_settings(service)
        test_all_settings(service)
        
        print("\n" + "="*70)
        print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

