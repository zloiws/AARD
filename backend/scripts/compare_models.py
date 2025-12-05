"""
Script to compare two models using benchmark suite
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
from app.models.benchmark_result import BenchmarkResult


def find_model_by_name(db, server_name, model_name):
    """Find model by server name and model name"""
    server = db.query(OllamaServer).filter(OllamaServer.name == server_name).first()
    if not server:
        print(f"❌ Server '{server_name}' not found")
        return None
    
    model = db.query(OllamaModel).filter(
        OllamaModel.server_id == server.id,
        OllamaModel.model_name == model_name,
        OllamaModel.is_active == True
    ).first()
    
    if not model:
        print(f"❌ Model '{model_name}' not found on server '{server_name}'")
        return None
    
    return model


async def run_tests_for_model(service, model, db, limit=None):
    """Run benchmark tests for a model"""
    print(f"\n{'='*70}")
    print(f" Запуск тестов для модели: {model.name or model.model_name}")
    print(f"{'='*70}\n")
    
    server = model.server
    server_url = server.get_api_url()
    
    # Get all tasks or limited set
    tasks = service.list_tasks(limit=limit)
    
    if not tasks:
        print("⚠️  Нет доступных задач для тестирования")
        return 0
    
    print(f"Найдено задач: {len(tasks)}")
    print(f"Запуск тестов...\n")
    
    results_count = 0
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task.name}... ", end="", flush=True)
        
        try:
            result = await service.run_benchmark(
                task_id=task.id,
                model_id=model.id,
                model_name=model.model_name,
                server_id=server.id,
                server_url=server_url,
                timeout=90.0
            )
            
            # Evaluate result
            if result.output and not result.error_message:
                await service.evaluate_result(result.id, use_llm=False)
                db.refresh(result)
            
            if result.passed:
                print(f"✓ (score: {result.score*100:.1f}%, time: {result.execution_time:.2f}s)")
            else:
                print(f"✗ (score: {result.score*100 if result.score else 0:.1f}%, time: {result.execution_time:.2f}s)")
            
            results_count += 1
            
        except Exception as e:
            print(f"✗ Ошибка: {str(e)[:50]}")
    
    print(f"\n✅ Выполнено тестов: {results_count}/{len(tasks)}")
    return results_count


async def compare_models():
    """Compare two models"""
    db = SessionLocal()
    try:
        # Find models
        print("=" * 70)
        print(" Поиск моделей для сравнения")
        print("=" * 70 + "\n")
        
        model1 = find_model_by_name(db, "Server 2 - Coding", "gemma3:4b")
        model2 = find_model_by_name(db, "Server 1 - General/Reasoning", "qwen3:8b")
        
        if not model1 or not model2:
            print("\n❌ Не удалось найти одну или обе модели")
            return
        
        print(f"✅ Модель 1: {model1.name or model1.model_name} (ID: {model1.id})")
        print(f"   Сервер: {model1.server.name}")
        print(f"✅ Модель 2: {model2.name or model2.model_name} (ID: {model2.id})")
        print(f"   Сервер: {model2.server.name}")
        
        # Check existing results
        service = BenchmarkService(db)
        
        results1 = db.query(BenchmarkResult).filter(BenchmarkResult.model_id == model1.id).count()
        results2 = db.query(BenchmarkResult).filter(BenchmarkResult.model_id == model2.id).count()
        
        total_tasks = len(service.list_tasks())
        
        # Run tests if needed
        print("\n" + "=" * 70)
        print(" Проверка существующих результатов")
        print("=" * 70)
        print(f"Модель 1: {results1} результатов из {total_tasks} задач")
        print(f"Модель 2: {results2} результатов из {total_tasks} задач")
        
        if results1 < total_tasks or results2 < total_tasks:
            print("\n" + "=" * 70)
            print(" Запуск тестов для моделей")
            print("=" * 70)
            
            if results1 < total_tasks:
                await run_tests_for_model(service, model1, db)
            else:
                print(f"\n✅ Модель 1 уже протестирована ({results1} результатов)")
            
            if results2 < total_tasks:
                await run_tests_for_model(service, model2, db)
            else:
                print(f"\n✅ Модель 2 уже протестирована ({results2} результатов)")
        else:
            print("\n✅ Обе модели уже протестированы")
        
        # Run comparison
        print("\n" + "=" * 70)
        print(" Запуск сравнения")
        print("=" * 70 + "\n")
        
        comparison = service.compare_models(
            model_ids=[model1.id, model2.id],
            task_type=None,  # All task types
            limit=None
        )
        
        # Display results
        print("\n" + "=" * 70)
        print(" Результаты сравнения")
        print("=" * 70 + "\n")
        
        for model_data in comparison.get("models", []):
            print(f"Модель: {model_data['model_name']}")
            print(f"  Всего задач: {model_data['total_tasks']}")
            print(f"  Выполнено: {model_data['completed']}")
            print(f"  Пройдено: {model_data['passed']}")
            print(f"  Провалено: {model_data['failed']}")
            print(f"  Средний Score: {model_data['avg_score']:.2%}")
            print(f"  Среднее время: {model_data['avg_execution_time']:.2f}s")
            print()
        
        if comparison.get("summary"):
            summary = comparison["summary"]
            print("Итоги:")
            print(f"  Лучшая модель: {summary.get('best_model', 'N/A')}")
            print(f"  Самая быстрая: {summary.get('fastest_model', 'N/A')}")
            print()
        
        # Show detailed results
        print("\n" + "=" * 70)
        print(" Детальные результаты по задачам")
        print("=" * 70 + "\n")
        
        model1_results = {r['benchmark_task_id']: r for r in comparison['models'][0]['results']}
        model2_results = {r['benchmark_task_id']: r for r in comparison['models'][1]['results']} if len(comparison['models']) > 1 else {}
        
        all_task_ids = set(model1_results.keys()) | set(model2_results.keys())
        
        print(f"{'Задача':<40} {comparison['models'][0]['model_name']:<25} {comparison['models'][1]['model_name'] if len(comparison['models']) > 1 else 'N/A':<25}")
        print("-" * 90)
        
        for task_id in sorted(all_task_ids):
            r1 = model1_results.get(task_id)
            r2 = model2_results.get(task_id)
            
            task_name = r1.get('task', {}).get('name', 'Unknown') if r1 else (r2.get('task', {}).get('name', 'Unknown') if r2 else 'Unknown')
            
            score1 = f"{r1['score']:.2%}" if r1 and r1.get('score') is not None else "N/A"
            score2 = f"{r2['score']:.2%}" if r2 and r2.get('score') is not None else "N/A"
            
            status1 = "✓" if r1 and r1.get('passed') else "✗" if r1 else "-"
            status2 = "✓" if r2 and r2.get('passed') else "✗" if r2 else "-"
            
            print(f"{task_name[:38]:<40} {status1} {score1:<20} {status2} {score2:<20}")
        
        print("\n✅ Сравнение завершено!")
        print(f"\nДля просмотра в UI откройте: /benchmarks/comparison?model_ids={model1.id},{model2.id}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(compare_models())

