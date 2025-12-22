"""
Запуск полного интеграционного теста Фазы 3
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest

if __name__ == "__main__":
    # Run tests with verbose output
    exit_code = pytest.main([
        "tests/integration/test_phase3_full_integration.py",
        "-v",
        "-s",
        "--tb=short",
        "--color=yes"
    ])
    sys.exit(exit_code)
