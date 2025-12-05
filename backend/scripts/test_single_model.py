"""
Script to test a single model on benchmark suite
"""
import sys
from pathlib import Path
import asyncio

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.services.benchmark_service import BenchmarkService


def find_model_by_name(db, server_url, model_name):
    """Find model by server URL and model name"""
    # Find server by URL
    server = db.query(OllamaServer).filter(
        OllamaServer.url.like(f"%{server_url}%")
    ).first()
    
    if not server:
        print(f"❌ Server with URL containing '{server_url}' not found")
        return None, None
    
    # Find model
    model = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.model_name == model_name,
        OllamaModel.is_active == True
    ).first()
    
    if not model:
        print(f"❌ Model '{model_name}' not found on server '{server.name}'")
        print(f"   Available models on this server:")
        all_models = db.query(OllamaModel).filter(
            OllamaModel.server_id == server.id,
            OllamaModel.is_active == True
        ).all()
        for m in all_models:
            print(f"     - {m.model_name}")
        return None, None
    
    return model, server


async def test_model():
    """Test a single model on benchmark suite"""
    db = SessionLocal()
    try:
        print("=" * 70)
        print(" Тестирование модели на benchmark suite")
        print("=" * 70 + "\n")
        
        # Find model
        server_url = "10.39.0.6"
        model_name = "huihui_ai/qwen3-vl-abliterated:8b-instruct"
        
        model, server = find_model_by_name(db, server_url, model_name)
        
        if not model or not server:
            return
        
        print(f"✅ Модель: {model.name or model.model_name}")
        print(f"   Сервер: {server.name} ({server.url})")
        print(f"   GPU: {server.server_metadata.get('gpu', 'Unknown') if server.server_metadata else 'Unknown'}")
        print()
        
        # Run tests
        service = BenchmarkService(db)
        
        print("=" * 70)
        print(" Запуск benchmark тестов")
        print("=" * 70 + "\n")
        
        results = await service.run_suite(
            task_type=None,  # All task types
            model_id=model.id,
            model_name=model.model_name,
            server_id=server.id,
            server_url=server.get_api_url(),
            limit=None,  # All tasks
            timeout=90.0
        )
        
        # Evaluate all results
        print("\n" + "=" * 70)
        print(" Оценка результатов")
        print("=" * 70 + "\n")
        
        evaluated = 0
        for i, result in enumerate(results, 1):
            if i % 10 == 0:
                print(f"  Оценка: {i}/{len(results)}")
            
            try:
                await service.evaluate_result(result.id, use_llm=False)
                evaluated += 1
            except Exception as e:
                print(f"  Ошибка при оценке результата {result.id}: {e}")
        
        db.commit()
        
        # Refresh and show statistics
        for result in results:
            db.refresh(result)
        
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_score = sum(r.score for r in results if r.score) / len([r for r in results if r.score]) if results else 0.0
        avg_time = sum(r.execution_time for r in results if r.execution_time) / len([r for r in results if r.execution_time]) if results else 0.0
        
        print("\n" + "=" * 70)
        print(" Результаты тестирования")
        print("=" * 70 + "\n")
        
        print(f"Всего задач: {len(results)}")
        print(f"Пройдено: {passed} ({passed/len(results)*100:.1f}%)")
        print(f"Провалено: {failed} ({failed/len(results)*100:.1f}%)")
        print(f"Средний Score: {avg_score*100:.1f}%")
        print(f"Среднее время: {avg_time:.2f}s")
        
        # Show results by task type
        print("\n" + "=" * 70)
        print(" Результаты по типам задач")
        print("=" * 70 + "\n")
        
        from collections import defaultdict
        by_type = defaultdict(lambda: {"total": 0, "passed": 0, "scores": []})
        
        for result in results:
            task = result.task
            if task:
                task_type = task.task_type.value
                by_type[task_type]["total"] += 1
                if result.passed:
                    by_type[task_type]["passed"] += 1
                if result.score:
                    by_type[task_type]["scores"].append(result.score)
        
        for task_type, stats in sorted(by_type.items()):
            avg_type_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
            pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0.0
            print(f"{task_type}:")
            print(f"  Задач: {stats['total']}, Пройдено: {stats['passed']} ({pass_rate:.1f}%)")
            print(f"  Средний Score: {avg_type_score*100:.1f}%")
        
        print("\n✅ Тестирование завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_model())

