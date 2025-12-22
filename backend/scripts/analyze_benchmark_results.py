"""
Script to analyze benchmark results and understand why tests are failing
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.benchmark_result import BenchmarkResult
from app.models.benchmark_task import BenchmarkTask
from app.models.ollama_model import OllamaModel
from sqlalchemy import and_


def analyze_results():
    """Analyze benchmark results to understand failures"""
    db = SessionLocal()
    try:
        # Get models
        model1 = db.query(OllamaModel).filter(OllamaModel.model_name == "gemma3:4b").first()
        model2 = db.query(OllamaModel).filter(OllamaModel.model_name == "qwen3:8b").first()
        
        if not model1 or not model2:
            print("Models not found")
            return
        
        print("=" * 70)
        print(" Анализ результатов benchmark")
        print("=" * 70 + "\n")
        
        for model in [model1, model2]:
            print(f"\n{'='*70}")
            print(f" Модель: {model.model_name}")
            print(f"{'='*70}\n")
            
            results = db.query(BenchmarkResult).filter(
                BenchmarkResult.model_id == model.id
            ).all()
            
            print(f"Всего результатов: {len(results)}")
            
            # Analyze by score ranges
            score_ranges = {
                "0.0": 0,
                "0.0-0.3": 0,
                "0.3-0.5": 0,
                "0.5": 0,
                "0.5-0.7": 0,
                "0.7-1.0": 0,
                "1.0": 0
            }
            
            has_expected = 0
            no_expected = 0
            passed_count = 0
            failed_count = 0
            
            for result in results:
                if result.score is None:
                    score_ranges["0.0"] += 1
                elif result.score == 0.0:
                    score_ranges["0.0"] += 1
                elif result.score < 0.3:
                    score_ranges["0.0-0.3"] += 1
                elif result.score < 0.5:
                    score_ranges["0.3-0.5"] += 1
                elif result.score == 0.5:
                    score_ranges["0.5"] += 1
                elif result.score < 0.7:
                    score_ranges["0.5-0.7"] += 1
                elif result.score < 1.0:
                    score_ranges["0.7-1.0"] += 1
                else:
                    score_ranges["1.0"] += 1
                
                if result.passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                # Check if task has expected_output
                task = db.query(BenchmarkTask).filter(
                    BenchmarkTask.id == result.benchmark_task_id
                ).first()
                
                if task:
                    if task.expected_output:
                        has_expected += 1
                    else:
                        no_expected += 1
            
            print(f"\nРаспределение по score:")
            for range_name, count in score_ranges.items():
                if count > 0:
                    print(f"  {range_name}: {count} ({count/len(results)*100:.1f}%)")
            
            print(f"\nСтатус:")
            print(f"  Пройдено: {passed_count} ({passed_count/len(results)*100:.1f}%)")
            print(f"  Провалено: {failed_count} ({failed_count/len(results)*100:.1f}%)")
            
            print(f"\nЗадачи с expected_output:")
            print(f"  С expected_output: {has_expected}")
            print(f"  Без expected_output: {no_expected}")
            
            # Show examples of failed results
            print(f"\nПримеры проваленных тестов (первые 5):")
            failed_results = [r for r in results if not r.passed][:5]
            for result in failed_results:
                task = db.query(BenchmarkTask).filter(
                    BenchmarkTask.id == result.benchmark_task_id
                ).first()
                if task:
                    print(f"\n  Задача: {task.name}")
                    print(f"    Score: {result.score*100 if result.score else 0:.1f}%")
                    print(f"    Pass threshold: {task.evaluation_criteria.get('pass_threshold', 0.7) if task.evaluation_criteria else 0.7}")
                    print(f"    Has expected_output: {bool(task.expected_output)}")
                    if result.metrics:
                        print(f"    Metrics: {result.metrics}")
                    if result.output:
                        output_preview = result.output[:100].replace('\n', ' ')
                        print(f"    Output preview: {output_preview}...")
        
        # Check pass threshold
        print(f"\n{'='*70}")
        print(" Анализ порога прохождения")
        print(f"{'='*70}\n")
        
        all_tasks = db.query(BenchmarkTask).all()
        threshold_counts = {}
        for task in all_tasks:
            threshold = task.evaluation_criteria.get("pass_threshold", 0.7) if task.evaluation_criteria else 0.7
            threshold_key = str(threshold)
            threshold_counts[threshold_key] = threshold_counts.get(threshold_key, 0) + 1
        
        print("Распределение порогов прохождения:")
        for threshold, count in sorted(threshold_counts.items()):
            print(f"  {threshold}: {count} задач")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_results()

