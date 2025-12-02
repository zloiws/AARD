"""
Скрипт для настройки основных моделей
Устанавливает приоритет 100 и capabilities для основных моделей
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_db
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from sqlalchemy.orm import Session

def setup_main_models():
    """Настроить основные модели с приоритетом 100 и capabilities"""
    
    # Конфигурация основных моделей
    main_models_config = [
        {
            "model_name": "huihui_ai/deepseek-r1-abliterated:8b",
            "priority": 100,
            "capabilities": ["general_chat", "reasoning", "planning"],
            "description": "Основная модель для общего чата, рассуждений и планирования"
        },
        {
            "model_name": "qwen3-coder:30b-a3b-q4_K_M",
            "priority": 100,
            "capabilities": ["code_generation", "code_analysis"],
            "description": "Основная модель для генерации и анализа кода"
        }
    ]
    
    db: Session = next(get_db())
    
    try:
        updated_count = 0
        
        for config in main_models_config:
            model_name = config["model_name"]
            
            # Найти модель по имени
            model = db.query(OllamaModel).filter(
                OllamaModel.model_name == model_name
            ).first()
            
            if not model:
                print(f"⚠️  Модель '{model_name}' не найдена в базе данных")
                print(f"   Убедитесь, что модель синхронизирована через интерфейс настроек")
                continue
            
            # Получить сервер модели
            server = db.query(OllamaServer).filter(
                OllamaServer.id == model.server_id
            ).first()
            
            if not server:
                print(f"⚠️  Сервер для модели '{model_name}' не найден")
                continue
            
            # Обновить модель
            model.priority = config["priority"]
            model.capabilities = config["capabilities"]
            model.is_active = True
            
            # Обновить имя модели для отображения
            if not model.name or model.name == model.model_name:
                # Создать красивое имя
                if "deepseek" in model.model_name.lower():
                    model.name = "DeepSeek R1 (General/Reasoning)"
                elif "qwen3" in model.model_name.lower() or "coder" in model.model_name.lower():
                    model.name = "Qwen3 Coder (Code Generation)"
                else:
                    model.name = model.model_name.split("/")[-1].split(":")[0]
            
            db.commit()
            
            print(f"✅ Обновлена модель: {model.name}")
            print(f"   Сервер: {server.name} ({server.url})")
            print(f"   Приоритет: {config['priority']}")
            print(f"   Capabilities: {', '.join(config['capabilities'])}")
            print(f"   Активна: {model.is_active}")
            print()
            
            updated_count += 1
        
        if updated_count == 0:
            print("⚠️  Не найдено моделей для обновления")
            print("   Убедитесь, что модели синхронизированы через интерфейс настроек")
        else:
            print(f"✅ Обновлено моделей: {updated_count}/{len(main_models_config)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при обновлении моделей: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    return updated_count > 0

if __name__ == "__main__":
    print("=" * 60)
    print("Настройка основных моделей")
    print("=" * 60)
    print()
    
    success = setup_main_models()
    
    if success:
        print()
        print("=" * 60)
        print("✅ Настройка завершена успешно")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("⚠️  Настройка завершена с предупреждениями")
        print("=" * 60)
        sys.exit(1)

