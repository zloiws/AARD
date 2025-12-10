#!/bin/bash
# Скрипт для запуска интеграционных тестов

echo "=========================================="
echo "Integration Tests with Real LLM"
echo "=========================================="
echo ""

# Проверка Ollama
echo "1. Checking Ollama server..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✓ Ollama server is running"
else
    echo "   ✗ Ollama server is not accessible"
    echo "   Please start Ollama server first"
    exit 1
fi

echo ""
echo "2. Running simple question tests..."
pytest tests/test_integration_simple_question.py -v -s

echo ""
echo "3. Running code generation tests..."
pytest tests/test_integration_code_generation.py -v -s

echo ""
echo "4. Running complex task tests (slow)..."
pytest tests/test_integration_complex_task.py -v -s -m slow

echo ""
echo "5. Running prompt improvement tests (slow)..."
pytest tests/test_integration_prompt_improvement.py -v -s -m slow

echo ""
echo "=========================================="
echo "All integration tests completed!"
echo "=========================================="
