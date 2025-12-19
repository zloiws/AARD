"""
Скрипт для восстановления всех важных начальных данных в БД
Использовать после очистки БД или при первом запуске
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir.parent / ".env")

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def restore_benchmark_tasks():
    """Восстановить benchmark задачи"""
    print("\n" + "="*70)
    print(" Восстановление Benchmark задач")
    print("="*70)
    
    db = SessionLocal()
    try:
        from app.services.benchmark_service import BenchmarkService
        
        service = BenchmarkService(db)
        benchmarks_dir = backend_dir / "data" / "benchmarks"
        
        if not benchmarks_dir.exists():
            print(f"❌ Директория {benchmarks_dir} не найдена!")
            return False
        
        stats = service.import_tasks_from_directory(benchmarks_dir)
        
        print(f"✅ Импортировано: {stats['imported']}")
        print(f"⏭️  Пропущено: {stats['skipped']}")
        print(f"❌ Ошибок: {stats['errors']}")
        
        return stats['errors'] == 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def restore_initial_prompts():
    """Восстановить начальные промпты"""
    print("\n" + "="*70)
    print(" Восстановление начальных промптов")
    print("="*70)
    
    db = SessionLocal()
    try:
        from app.models.prompt import PromptStatus, PromptType
        from app.services.prompt_service import PromptService
        
        service = PromptService(db)
        
        # Проверить существующие
        existing = service.list_prompts(limit=10)
        if existing:
            print(f"Найдено {len(existing)} существующих промптов. Пропускаем создание.")
            return True
        
        print("Создание начальных промптов...\n")
        
        # Task analysis prompt
        analysis_prompt = service.get_active_prompt(
            name="task_analysis",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        if not analysis_prompt:
            analysis_prompt = service.create_prompt(
                name="task_analysis",
                prompt_text="""You are an expert at task analysis and strategic planning.
Analyze the task and create a strategy that includes:
1. approach: General approach to solving the task
2. assumptions: List of assumptions made
3. constraints: List of constraints and limitations
4. success_criteria: List of criteria for successful completion

Return a JSON object with these fields. Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Создан: {analysis_prompt.name}")
        else:
            print(f"⏭️  Уже существует: {analysis_prompt.name}")
        
        # Task decomposition prompt
        decomposition_prompt = service.get_active_prompt(
            name="task_decomposition",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        if not decomposition_prompt:
            decomposition_prompt = service.create_prompt(
                name="task_decomposition",
                prompt_text="""You are an expert at breaking down complex tasks into executable steps.
Create a detailed plan with steps. Each step should have:
- step_id: unique identifier (e.g., "step_1", "step_2")
- description: clear description of what to do
- type: one of "action", "decision", "validation", "approval"
- inputs: what inputs are needed (object)
- expected_outputs: what outputs are expected (object)
- timeout: timeout in seconds (integer)
- retry_policy: {max_attempts: 3, delay: 10}
- dependencies: list of step_ids that must complete first (array)
- approval_required: boolean
- risk_level: "low", "medium", or "high"
- function_call: (optional) if step requires code execution, include function call

Return a JSON array of steps. Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Создан: {decomposition_prompt.name}")
        else:
            print(f"⏭️  Уже существует: {decomposition_prompt.name}")
        
        # Replan prompt
        replan_prompt = service.get_active_prompt(
            name="task_replan",
            prompt_type=PromptType.SYSTEM,
            level=0
        )
        if not replan_prompt:
            replan_prompt = service.create_prompt(
                name="task_replan",
                prompt_text="""You are an expert at replanning tasks when execution fails or requirements change.
Analyze the current situation and create a new plan.

Context:
- Original task: {original_task}
- Current status: {current_status}
- Issues encountered: {issues}
- Completed steps: {completed_steps}

Create a new plan that addresses issues and builds on completed steps.
Return a JSON object with revised_approach, new_steps, removed_steps, modified_steps, reasoning.
Only return valid JSON, no additional text.""",
                prompt_type=PromptType.SYSTEM,
                level=0,
                created_by="system"
            )
            print(f"✅ Создан: {replan_prompt.name}")
        else:
            print(f"⏭️  Уже существует: {replan_prompt.name}")
        
        print("\n✅ Начальные промпты восстановлены!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка восстановления промптов: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def restore_ollama_servers():
    """Восстановить серверы Ollama из .env"""
    print("\n" + "="*70)
    print(" Восстановление серверов Ollama")
    print("="*70)
    
    db = SessionLocal()
    try:
        from app.core.config import get_settings
        from app.models.ollama_server import OllamaServer

        # Проверить существующие
        existing_count = db.query(OllamaServer).count()
        if existing_count > 0:
            print(f"Найдено {existing_count} существующих серверов. Пропускаем создание.")
            return True
        
        settings = get_settings()
        
        # Импортировать из скрипта
        from scripts.init_ollama_servers import init_servers
        init_servers()
        
        print("✅ Серверы восстановлены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Главная функция восстановления"""
    print("="*70)
    print(" ВОССТАНОВЛЕНИЕ ВАЖНЫХ ДАННЫХ В БД")
    print("="*70)
    
    success = True
    
    # 1. Benchmark задачи
    if not restore_benchmark_tasks():
        success = False
    
    # 2. Начальные промпты
    if not restore_initial_prompts():
        success = False
    
    # 3. Серверы Ollama
    if not restore_ollama_servers():
        success = False
    
    print("\n" + "="*70)
    if success:
        print("✅ ВСЕ ДАННЫЕ УСПЕШНО ВОССТАНОВЛЕНЫ!")
    else:
        print("⚠️  ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО С ОШИБКАМИ")
    print("="*70)
    
    # Показать итоговую статистику
    db = SessionLocal()
    try:
        from app.models.benchmark_task import BenchmarkTask
        from app.models.ollama_server import OllamaServer
        from app.models.prompt import Prompt
        
        print("\nИтоговая статистика:")
        print(f"  Benchmark задач: {db.query(BenchmarkTask).count()}")
        print(f"  Промптов: {db.query(Prompt).count()}")
        print(f"  Серверов: {db.query(OllamaServer).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

