"""Apply benchmark migration"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.database import engine, Base
from app.models.benchmark_task import BenchmarkTask

# Create table if not exists
Base.metadata.create_all(bind=engine, tables=[BenchmarkTask.__table__])
print("✅ Benchmark tasks table created/verified")

