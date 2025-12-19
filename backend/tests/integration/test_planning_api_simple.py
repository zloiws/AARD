"""
Упрощенный тест API планирования - проверка базовой функциональности
Без генерации через LLM (можно создать план вручную через БД)
"""
import json
from typing import Optional

import requests

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/plans"


def print_response(response: requests.Response, title: str = ""):
    """Print formatted response"""
    print(f"\n{'='*60}")
    if title:
        print(f"{title}")
        print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        # Ограничим вывод для больших ответов
        if isinstance(data, dict) and "steps" in data:
            data_copy = data.copy()
            if len(str(data_copy.get("steps", []))) > 500:
                data_copy["steps"] = f"[{len(data.get('steps', []))} шагов] (сокращено)"
            print(f"Response: {json.dumps(data_copy, indent=2, ensure_ascii=False)}")
        else:
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text[:500]}")
    print(f"{'='*60}\n")


def test_health():
    """Test server health"""
    print("🧪 Проверка доступности сервера")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Сервер доступен")
            return True
        else:
            print(f"⚠️  Сервер отвечает с кодом {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        return False


def test_list_plans():
    """Test listing plans"""
    print("🧪 Тест 1: Список планов")
    
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        print_response(response, "Список планов")
        
        if response.status_code == 200:
            plans = response.json()
            print(f"✅ Найдено планов: {len(plans)}")
            return plans
        return []
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []


def test_get_plan(plan_id: str):
    """Test getting plan details"""
    print(f"🧪 Тест 2: Детали плана {plan_id}")
    
    try:
        response = requests.get(f"{API_BASE}/{plan_id}", timeout=10)
        print_response(response, f"Детали плана {plan_id}")
        
        if response.status_code == 200:
            plan = response.json()
            print(f"✅ План получен")
            print(f"   Цель: {plan.get('goal', 'N/A')[:100]}...")
            print(f"   Статус: {plan.get('status', 'N/A')}")
            print(f"   Шагов: {len(plan.get('steps', []))}")
            return plan
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def test_get_plan_status(plan_id: str):
    """Test getting plan status"""
    print(f"🧪 Тест 3: Статус выполнения плана {plan_id}")
    
    try:
        response = requests.get(f"{API_BASE}/{plan_id}/status", timeout=10)
        print_response(response, f"Статус выполнения плана {plan_id}")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Статус получен")
            print(f"   Прогресс: {status.get('progress', 0):.1f}%")
            print(f"   Шагов: {status.get('current_step', 0)}/{status.get('total_steps', 0)}")
            return status
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def test_filter_plans():
    """Test filtering plans"""
    print("🧪 Тест 4: Фильтрация планов")
    
    # Test by status
    for status in ["draft", "approved", "executing"]:
        print(f"   Фильтр по статусу: {status}")
        try:
            response = requests.get(f"{API_BASE}/?status={status}", timeout=10)
            if response.status_code == 200:
                plans = response.json()
                print(f"   ✅ Найдено планов со статусом '{status}': {len(plans)}")
            else:
                print(f"   ⚠️  Код ответа: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")


def main():
    """Run all tests"""
    print("="*60)
    print("УПРОЩЕННОЕ ТЕСТИРОВАНИЕ API ПЛАНИРОВАНИЯ")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print()
    
    # Check health
    if not test_health():
        print("\n❌ Сервер недоступен. Запустите сервер:")
        print("   cd C:\\work\\AARD\\backend")
        print("   python main.py")
        return
    
    print()
    
    # Test 1: List plans
    plans = test_list_plans()
    
    if not plans:
        print("⚠️  Планов не найдено. Создайте план через API или БД для полного тестирования.")
        print("\nДля создания плана через API:")
        print("   POST /api/plans/")
        print("   {")
        print('     "task_description": "Ваша задача"')
        print("   }")
        print("\n⚠️  ВНИМАНИЕ: Создание плана через LLM может занять 5-10 минут!")
        return
    
    # Test 2: Get first plan details
    if plans:
        first_plan = plans[0]
        plan_id = first_plan.get("id")
        if plan_id:
            test_get_plan(plan_id)
            
            # Test 3: Get status
            test_get_plan_status(plan_id)
    
    # Test 4: Filter plans
    test_filter_plans()
    
    print()
    print("="*60)
    print("✅ БАЗОВОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)
    print("\n💡 Для полного теста с созданием плана используйте:")
    print("   python test_planning_api.py")
    print("   (может занять 5-10 минут)")


if __name__ == "__main__":
    main()

