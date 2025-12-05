"""
Скрипт для проверки моделей и их capabilities на сервере 10.39.0.6
"""
import sys
from pathlib import Path

# Добавить backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService
from app.core.model_selector import ModelSelector

def main():
    db = SessionLocal()
    
    try:
        # Найти сервер 10.39.0.6
        servers = OllamaService.get_all_active_servers(db)
        print("=" * 80)
        print("АКТИВНЫЕ СЕРВЕРЫ:")
        print("=" * 80)
        for s in servers:
            print(f"  - {s.name}: {s.url} (ID: {s.id})")
        
        server_10_39 = None
        for s in servers:
            if "10.39.0.6" in s.url:
                server_10_39 = s
                break
        
        if not server_10_39:
            print("\n❌ Сервер 10.39.0.6 не найден!")
            return
        
        print(f"\n{'=' * 80}")
        print(f"СЕРВЕР: {server_10_39.name} ({server_10_39.url})")
        print("=" * 80)
        
        # Получить модели
        models = OllamaService.get_models_for_server(db, str(server_10_39.id))
        print(f"\nВсего моделей на сервере: {len(models)}")
        
        # Фильтровать embedding модели
        model_selector = ModelSelector(db)
        non_embedding = model_selector._filter_embedding_models(models)
        print(f"Не-embedding моделей: {len(non_embedding)}")
        
        print(f"\n{'=' * 80}")
        print("МОДЕЛИ НА СЕРВЕРЕ 10.39.0.6:")
        print("=" * 80)
        
        for i, model in enumerate(models, 1):
            capabilities_str = ", ".join(model.capabilities) if model.capabilities else "нет"
            is_embedding = "embedding" in model.model_name.lower() if model.model_name else False
            status = "✓" if model.is_active else "✗"
            embedding_mark = " [EMBEDDING]" if is_embedding else ""
            
            print(f"\n{i}. {status} {model.model_name}{embedding_mark}")
            print(f"   ID: {model.id}")
            print(f"   Capabilities: {capabilities_str}")
            print(f"   Active: {model.is_active}")
            print(f"   Priority: {model.priority if hasattr(model, 'priority') else 'N/A'}")
        
        print(f"\n{'=' * 80}")
        print("АНАЛИЗ ВЫБОРА МОДЕЛИ ДЛЯ PLANNING:")
        print("=" * 80)
        
        # Попробовать выбрать модель для planning
        planning_model = model_selector.get_planning_model(server=server_10_39)
        
        if planning_model:
            print(f"\n✓ Выбрана модель: {planning_model.model_name}")
            print(f"  ID: {planning_model.id}")
            print(f"  Capabilities: {', '.join(planning_model.capabilities) if planning_model.capabilities else 'нет'}")
            
            # Проверить, почему была выбрана
            has_planning = False
            has_reasoning = False
            has_strategy = False
            
            if planning_model.capabilities:
                caps_lower = [c.lower() for c in planning_model.capabilities]
                has_planning = "planning" in caps_lower
                has_reasoning = "reasoning" in caps_lower
                has_strategy = "strategy" in caps_lower
            
            if has_planning or has_reasoning or has_strategy:
                print(f"  ✓ Модель имеет нужные capabilities!")
                if has_planning:
                    print(f"    - planning: ✓")
                if has_reasoning:
                    print(f"    - reasoning: ✓")
                if has_strategy:
                    print(f"    - strategy: ✓")
            else:
                print(f"  ⚠ Модель выбрана как FALLBACK (нет capabilities: planning/reasoning/strategy)")
                print(f"    Это первая доступная не-embedding модель в списке")
        else:
            print("\n❌ Не удалось выбрать модель для planning")
        
        print(f"\n{'=' * 80}")
        print("РЕКОМЕНДАЦИИ:")
        print("=" * 80)
        
        # Проверить, есть ли модели с нужными capabilities
        models_with_caps = []
        for model in non_embedding:
            if model.capabilities:
                caps_lower = [c.lower() for c in model.capabilities]
                if any(cap in caps_lower for cap in ["planning", "reasoning", "strategy"]):
                    models_with_caps.append(model)
        
        if not models_with_caps:
            print("\n⚠ Нет моделей с capabilities: planning, reasoning, strategy")
            print("  Рекомендуется:")
            print("  1. Добавить capabilities к существующим моделям в БД")
            print("  2. Или использовать модели с этими capabilities")
            print(f"\n  Текущая fallback модель: {planning_model.model_name if planning_model else 'нет'}")
        else:
            print(f"\n✓ Найдено {len(models_with_caps)} моделей с нужными capabilities:")
            for model in models_with_caps:
                print(f"  - {model.model_name}: {', '.join(model.capabilities)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()

