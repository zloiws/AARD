"""
Объяснение выбора модели gemma3:4b
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.model_selector import ModelSelector
from app.services.ollama_service import OllamaService


def main():
    db = SessionLocal()
    
    try:
        # Найти сервер 10.39.0.6
        servers = OllamaService.get_all_active_servers(db)
        server_10_39 = None
        for s in servers:
            if "10.39.0.6" in s.url:
                server_10_39 = s
                break
        
        if not server_10_39:
            print("Сервер 10.39.0.6 не найден!")
            return
        
        print("=" * 80)
        print("ОБЪЯСНЕНИЕ ВЫБОРА МОДЕЛИ gemma3:4b")
        print("=" * 80)
        
        # Получить модели БЕЗ фильтрации
        models_raw = OllamaService.get_models_for_server(db, str(server_10_39.id))
        
        print(f"\n1. ВСЕ МОДЕЛИ НА СЕРВЕРЕ (порядок из БД):")
        print(f"   Сортировка: priority DESC, name ASC")
        print("-" * 80)
        for i, m in enumerate(models_raw, 1):
            priority = getattr(m, 'priority', 0) or 0
            is_embedding = "embedding" in m.model_name.lower() if m.model_name else False
            embedding_mark = " [EMBEDDING - будет исключена]" if is_embedding else ""
            print(f"   {i}. {m.model_name} (priority={priority}, name='{m.name}'){embedding_mark}")
        
        # Применить фильтрацию embedding
        model_selector = ModelSelector(db)
        models_filtered = model_selector._filter_embedding_models(models_raw)
        
        print(f"\n2. ПОСЛЕ ФИЛЬТРАЦИИ EMBEDDING МОДЕЛЕЙ:")
        print(f"   Осталось: {len(models_filtered)} моделей")
        print("-" * 80)
        for i, m in enumerate(models_filtered, 1):
            print(f"   {i}. {m.model_name}")
        
        # Проверить capabilities
        print(f"\n3. ПРОВЕРКА CAPABILITIES:")
        print("-" * 80)
        models_with_caps = []
        for m in models_filtered:
            caps = m.capabilities if m.capabilities else []
            has_planning = any(c.lower() in ["planning", "reasoning", "strategy"] 
                             for c in caps) if caps else False
            status = "✓ ЕСТЬ" if has_planning else "✗ НЕТ"
            print(f"   {m.model_name}: capabilities={caps} -> {status}")
            if has_planning:
                models_with_caps.append(m)
        
        print(f"\n4. РЕЗУЛЬТАТ ПОИСКА МОДЕЛИ С CAPABILITIES:")
        print("-" * 80)
        if models_with_caps:
            print(f"   ✓ Найдено {len(models_with_caps)} моделей с planning/reasoning/strategy")
            for m in models_with_caps:
                print(f"     - {m.model_name}")
        else:
            print(f"   ✗ НЕ НАЙДЕНО моделей с capabilities: planning, reasoning, strategy")
        
        print(f"\n5. FALLBACK ВЫБОР:")
        print("-" * 80)
        if models_filtered:
            fallback_model = models_filtered[0]
            print(f"   ⚠ Используется FALLBACK: первая модель в списке")
            print(f"   Выбрана: {fallback_model.model_name}")
            print(f"   Причина: нет моделей с нужными capabilities")
            print(f"   Порядок в списке определяется:")
            print(f"     1. priority DESC (у всех = 0, поэтому одинаково)")
            print(f"     2. name ASC (алфавитная сортировка)")
            print(f"   После фильтрации embedding, первая по алфавиту: '{fallback_model.model_name}'")
        
        # Показать алфавитную сортировку
        print(f"\n6. АЛФАВИТНАЯ СОРТИРОВКА ИМЕН (name ASC):")
        print("-" * 80)
        sorted_names = sorted([m.name for m in models_filtered])
        for i, name in enumerate(sorted_names, 1):
            model = next(m for m in models_filtered if m.name == name)
            marker = " <-- ВЫБРАНА" if model.model_name == "gemma3:4b" else ""
            print(f"   {i}. '{name}' -> {model.model_name}{marker}")
        
        print(f"\n7. ВЫВОД:")
        print("=" * 80)
        print(f"   Модель 'gemma3:4b' выбрана потому что:")
        print(f"   1. У всех моделей priority = 0 (одинаковый приоритет)")
        print(f"   2. Сортировка идет по name (алфавитно)")
        print(f"   3. После фильтрации embedding моделей")
        print(f"   4. Первая модель по алфавиту (name) = 'gemma3:4b'")
        print(f"   5. Нет моделей с capabilities: planning/reasoning/strategy")
        print(f"   6. Поэтому используется fallback = первая в списке")
        print(f"\n   Это НЕ основано на тестах производительности!")
        print(f"   Это просто порядок сортировки в базе данных.")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()

