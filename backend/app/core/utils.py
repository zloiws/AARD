"""
Общие утилиты для проекта AARD
Консолидированные функции, используемые в разных частях проекта
"""
from typing import Optional


def print_separator(title: str, width: int = 70):
    """Печать разделителя для тестов и скриптов
    
    Args:
        title: Заголовок для отображения
        width: Ширина разделителя (по умолчанию 70)
    """
    print("\n" + "=" * width)
    print(f" {title}")
    print("=" * width + "\n")


def format_duration(seconds: float) -> str:
    """Форматировать длительность в читаемый вид
    
    Args:
        seconds: Количество секунд
        
    Returns:
        Отформатированная строка (например, "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def safe_get_nested(data: dict, *keys, default=None):
    """Безопасное получение вложенного значения из словаря
    
    Args:
        data: Словарь для поиска
        *keys: Ключи для последовательного доступа
        default: Значение по умолчанию, если ключ не найден
        
    Returns:
        Значение или default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

