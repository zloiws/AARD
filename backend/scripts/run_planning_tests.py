"""
Script to run planning tests from simple to complex
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tests.integration.test_planning_digital_twin import run_all_tests

if __name__ == "__main__":
    run_all_tests()

