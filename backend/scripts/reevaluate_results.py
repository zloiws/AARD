"""
Script to reevaluate existing benchmark results with improved evaluation logic
"""
import sys
from pathlib import Path
import asyncio

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.benchmark_result import BenchmarkResult
from app.models.ollama_model import OllamaModel
from app.services.benchmark_service import BenchmarkService


async def reevaluate_results():
    """Reevaluate all benchmark results with improved logic"""
    db = SessionLocal()
    try:
        service = BenchmarkService(db)
        
        # Get models
        model1 = db.query(OllamaModel).filter(OllamaModel.model_name == "gemma3:4b").first()
        model2 = db.query(OllamaModel).filter(OllamaModel.model_name == "qwen3:8b").first()
        
        models = [m for m in [model1, model2] if m]
        
        print("=" * 70)
        print(" Переоценка результатов benchmark")
        print("=" * 70 + "\n")
        
        for model in models:
            print(f"\n{'='*70}")
            print(f" Модель: {model.model_name}")
            print(f"{'='*70}\n")
            
            results = db.query(BenchmarkResult).filter(
                BenchmarkResult.model_id == model.id
            ).all()
            
            print(f"Найдено результатов: {len(results)}")
            print("Переоценка...\n")
            
            reevaluated = 0
            passed_before = sum(1 for r in results if r.passed)
            
            for i, result in enumerate(results, 1):
                if i % 10 == 0:
                    print(f"  Обработано: {i}/{len(results)}")
                
                try:
                    await service.evaluate_result(result.id, use_llm=False)
                    reevaluated += 1
                except Exception as e:
                    print(f"  Ошибка при переоценке результата {result.id}: {e}")
            
            db.commit()
            
            # Refresh results
            for result in results:
                db.refresh(result)
            
            passed_after = sum(1 for r in results if r.passed)
            
            print(f"\n✅ Переоценено: {reevaluated}/{len(results)}")
            print(f"   Пройдено до: {passed_before} ({passed_before/len(results)*100:.1f}%)")
            print(f"   Пройдено после: {passed_after} ({passed_after/len(results)*100:.1f}%)")
            print(f"   Изменение: +{passed_after - passed_before} ({passed_after - passed_before}/{len(results)})")
        
        print("\n" + "=" * 70)
        print(" ✅ Переоценка завершена!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(reevaluate_results())

