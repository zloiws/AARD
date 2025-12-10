#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test runner with detailed output"""
import pytest
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ")
    print("=" * 80)
    print()
    
    # Run tests
    exit_code = pytest.main([
        "tests/test_integration_basic.py",
        "tests/test_integration_simple_question.py",
        "tests/test_integration_code_generation.py",
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ])
    
    sys.exit(exit_code)
