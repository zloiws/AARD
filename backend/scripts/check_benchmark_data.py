"""
Проверка наличия benchmark данных в БД
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.models.prompt import Prompt
from app.models.ollama_server import OllamaServer

db = SessionLocal()

print("="*70)
print("ПРОВЕРКА ДАННЫХ В БД")
print("="*70)

# Benchmark задачи
benchmark_count = db.query(BenchmarkTask).count()
print(f"\nBenchmark задач: {benchmark_count}")

if benchmark_count > 0:
    for task_type in BenchmarkTaskType:
        count = db.query(BenchmarkTask).filter(BenchmarkTask.task_type == task_type).count()
        print(f"  - {task_type.value}: {count}")
else:
    print("  ⚠️  Нет benchmark задач! Запустите: python scripts/import_benchmark_tasks.py")

# Промпты
prompt_count = db.query(Prompt).count()
print(f"\nПромптов: {prompt_count}")

if prompt_count > 0:
    prompts = db.query(Prompt).limit(5).all()
    for p in prompts:
        print(f"  - {p.name} ({p.prompt_type})")
else:
    print("  ⚠️  Нет промптов! Запустите: python scripts/restore_initial_data.py")

# Серверы
server_count = db.query(OllamaServer).count()
print(f"\nСерверов Ollama: {server_count}")

if server_count > 0:
    servers = db.query(OllamaServer).all()
    for s in servers:
        print(f"  - {s.name} ({s.url})")
else:
    print("  ⚠️  Нет серверов! Запустите: python scripts/init_ollama_servers.py")

print("\n" + "="*70)
if benchmark_count == 0 or prompt_count == 0:
    print("⚠️  ОТСУТСТВУЮТ ВАЖНЫЕ ДАННЫЕ!")
    print("Запустите: python scripts/restore_initial_data.py")
else:
    print("✅ Все важные данные на месте!")
print("="*70)

db.close()

