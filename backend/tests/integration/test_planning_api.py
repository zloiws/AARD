"""
Test script for Planning API endpoints
"""
import json
import os
import time
from typing import Optional

import pytest
import requests

# These are manual API checks that require the backend server to be running at localhost:8000.
# In automated test runs we skip them unless RUN_API_INTEGRATION_TESTS env var is set.
if not os.getenv("RUN_API_INTEGRATION_TESTS"):
    pytest.skip("Skipping planning API integration tests (require running server). Set RUN_API_INTEGRATION_TESTS=1 to enable.", allow_module_level=True)

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/plans"

# Увеличенные таймауты для длительных операций (генерация плана через LLM)
REQUEST_TIMEOUT = 600  # 10 минут для создания плана (модель может выгрузиться из GPU)


def print_response(response: requests.Response, title: str = ""):
    """Print formatted response"""
    print(f"\n{'='*60}")
    if title:
        print(f"{title}")
        print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*60}\n")


def test_create_plan():
    """Test creating a plan"""
    print("🧪 Тест 1: Создание плана")
    print("   ⏳ Это может занять 1-10 минут (генерация через LLM)...")
    print("   ⚠️  Модель может выгрузиться из GPU, если запрос слишком долгий")
    print("   💡 Таймаут установлен на 5 минут")
    print("   💡 Если модель выгрузилась, она автоматически загрузится при запросе")
    
    # Упрощенная задача для быстрого теста
    data = {
        "task_description": "Написать функцию для сложения двух чисел",
        "context": {
            "language": "Python"
        }
    }
    
    start_time = time.time()
    print(f"   🕐 Начало: {time.strftime('%H:%M:%S')}")
    
    try:
        response = requests.post(
            f"{API_BASE}/",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        elapsed = time.time() - start_time
        print(f"   🕐 Конец: {time.strftime('%H:%M:%S')}")
        print(f"   ⏱️  Время выполнения: {elapsed:.1f} секунд ({elapsed/60:.1f} минут)")
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"   ❌ Таймаут после {elapsed:.1f} секунд ({elapsed/60:.1f} минут)")
        print(f"   💡 Возможно, модель выгрузилась из GPU или запрос слишком долгий")
        print(f"   💡 Попробуйте увеличить таймаут или проверить состояние модели")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Ошибка после {elapsed:.1f} секунд ({elapsed/60:.1f} минут): {e}")
        return None
    
    print_response(response, "Создание плана")
    
    if response.status_code == 200:
        plan_data = response.json()
        return plan_data.get("id")
    return None


def test_list_plans():
    """Test listing plans"""
    print("🧪 Тест 2: Список планов")
    
    response = requests.get(f"{API_BASE}/")
    print_response(response, "Список планов")
    
    if response.status_code == 200:
        plans = response.json()
        print(f"Найдено планов: {len(plans)}")
        return plans
    return []


def test_get_plan(plan_id: str):
    """Test getting plan details"""
    print(f"🧪 Тест 3: Детали плана {plan_id}")
    
    response = requests.get(f"{API_BASE}/{plan_id}")
    print_response(response, f"Детали плана {plan_id}")
    
    if response.status_code == 200:
        return response.json()
    return None


def test_update_plan(plan_id: str):
    """Test updating a plan"""
    print(f"🧪 Тест 4: Обновление плана {plan_id}")
    
    data = {
        "goal": "Обновленная цель: Создать улучшенный инструмент для поиска файлов"
    }
    
    response = requests.put(
        f"{API_BASE}/{plan_id}",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    print_response(response, f"Обновление плана {plan_id}")
    
    return response.status_code == 200


def test_approve_plan(plan_id: str):
    """Test approving a plan"""
    print(f"🧪 Тест 5: Утверждение плана {plan_id}")
    
    response = requests.post(f"{API_BASE}/{plan_id}/approve")
    print_response(response, f"Утверждение плана {plan_id}")
    
    if response.status_code == 200:
        plan_data = response.json()
        print(f"✅ План утвержден. Статус: {plan_data.get('status')}")
        return True
    return False


def test_execute_plan(plan_id: str):
    """Test starting plan execution"""
    print(f"🧪 Тест 6: Начало выполнения плана {plan_id}")
    
    response = requests.post(f"{API_BASE}/{plan_id}/execute")
    print_response(response, f"Начало выполнения плана {plan_id}")
    
    if response.status_code == 200:
        plan_data = response.json()
        print(f"✅ Выполнение начато. Статус: {plan_data.get('status')}")
        return True
    return False


def test_get_plan_status(plan_id: str):
    """Test getting plan status"""
    print(f"🧪 Тест 7: Статус выполнения плана {plan_id}")
    
    response = requests.get(f"{API_BASE}/{plan_id}/status")
    print_response(response, f"Статус выполнения плана {plan_id}")
    
    if response.status_code == 200:
        status_data = response.json()
        print(f"📊 Прогресс: {status_data.get('progress', 0):.1f}%")
        print(f"   Текущий шаг: {status_data.get('current_step', 0)}/{status_data.get('total_steps', 0)}")
        return status_data
    return None


def test_replan(plan_id: str):
    """Test replanning"""
    print(f"🧪 Тест 8: Перепланирование плана {plan_id}")
    print("   ⏳ Это может занять 1-5 минут (генерация через LLM)...")
    
    data = {
        "reason": "Требуется более детальная декомпозиция задачи",
        "context": {
            "feedback": "Нужно добавить больше шагов для валидации"
        }
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{API_BASE}/{plan_id}/replan",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        elapsed = time.time() - start_time
        print(f"   ⏱️  Время выполнения: {elapsed:.1f} секунд ({elapsed/60:.1f} минут)")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"   ❌ Таймаут после {elapsed:.1f} секунд")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Ошибка после {elapsed:.1f} секунд: {e}")
        return None
    
    print_response(response, f"Перепланирование плана {plan_id}")
    
    if response.status_code == 200:
        new_plan = response.json()
        print(f"✅ Создан новый план. Версия: {new_plan.get('version')}")
        return new_plan.get("id")
    return None


def test_filter_plans():
    """Test filtering plans"""
    print("🧪 Тест 9: Фильтрация планов")
    
    # Test by status
    response = requests.get(f"{API_BASE}/?status=draft")
    print_response(response, "Планы со статусом 'draft'")
    
    if response.status_code == 200:
        plans = response.json()
        print(f"Найдено планов со статусом 'draft': {len(plans)}")
        return plans
    return []


def main():
    """Run all tests"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ API ПЛАНИРОВАНИЯ")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Сервер не отвечает на /health")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Не удалось подключиться к серверу: {e}")
        print("   Убедитесь, что сервер запущен: cd backend && python main.py")
        return
    
    print("✅ Сервер доступен")
    print()
    
    # ВАЖНО: Создание плана через LLM отключено по умолчанию
    # чтобы избежать зацикливания и долгой нагрузки на GPU
    print("⚠️  ВНИМАНИЕ: Создание плана через LLM отключено в тесте!")
    print("   Это предотвращает зацикливание и долгую нагрузку на GPU")
    print("   Для тестирования создания плана используйте существующие планы")
    print()
    
    # Test 1: List existing plans first
    plans = test_list_plans()
    
    # Test 2: Get plan details if available
    plan_id = None
    if plans:
        plan_id = plans[0].get("id")
        if plan_id:
            print(f"✅ Используем существующий план: {plan_id}")
            test_get_plan(plan_id)
    else:
        print("⚠️  Планов не найдено. Пропускаем тесты, требующие существующий план.")
        print("   Для создания плана вручную используйте:")
        print("   curl -X POST http://localhost:8000/api/plans/ \\")
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"task_description": "Простая задача"}\'')
        print()
        return
    
    # Test 2: List plans
    plans = test_list_plans()
    
    # Test 3: Get plan details
    plan_data = test_get_plan(plan_id)
    if plan_data:
        print(f"✅ План содержит {len(plan_data.get('steps', []))} шагов")
        print(f"   Статус: {plan_data.get('status')}")
        print(f"   Цель: {plan_data.get('goal')[:100]}...")
    
    # Test 4: Update plan (only if status is DRAFT)
    if plan_data and plan_data.get('status') == 'draft':
        test_update_plan(plan_id)
        # Refresh plan data
        plan_data = test_get_plan(plan_id)
    
    # Test 5: Approve plan
    if plan_data and plan_data.get('status') == 'draft':
        test_approve_plan(plan_id)
        # Refresh plan data
        plan_data = test_get_plan(plan_id)
    
    # Test 6: Execute plan (only if approved)
    if plan_data and plan_data.get('status') == 'approved':
        test_execute_plan(plan_id)
        # Refresh plan data
        plan_data = test_get_plan(plan_id)
    
    # Test 7: Get status
    test_get_plan_status(plan_id)
    
    # Test 8: Replan
    new_plan_id = test_replan(plan_id)
    if new_plan_id:
        print(f"✅ Новый план создан: {new_plan_id}")
        test_get_plan(new_plan_id)
    
    # Test 9: Filter plans
    test_filter_plans()
    
    print()
    print("="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)


if __name__ == "__main__":
    main()

