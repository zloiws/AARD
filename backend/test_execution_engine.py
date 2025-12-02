"""
Test script for plan execution engine
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.approval_service import ApprovalService
from app.models.plan import Plan


async def test_execution_engine():
    """Test plan execution engine"""
    print("=" * 60)
    print("Тест движка выполнения планов")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 1. Get or create a simple approved plan
        print("\n1. Получение утвержденного плана...")
        planning_service = PlanningService(db)
        
        # Get an approved plan or create one
        approved_plans = db.query(Plan).filter(Plan.status == "approved").limit(1).all()
        
        if not approved_plans:
            print("   ⚠️ Нет утвержденных планов. Создаю тестовый план...")
            
            # Create a simple plan
            task_description = "Протестировать выполнение плана: создать простой Python скрипт для вывода 'Hello, World!'"
            
            plan = await planning_service.generate_plan(
                task_description=task_description,
                context={"test": True, "simple": True}
            )
            
            print(f"   ✓ План создан: {plan.id}")
            
            # Approve the plan
            if plan.status == "draft":
                # Get approval request and approve it
                from app.models.approval import ApprovalRequest
                approval = db.query(ApprovalRequest).filter(
                    ApprovalRequest.plan_id == plan.id
                ).first()
                
                if approval:
                    approval_service = ApprovalService(db)
                    approval_service.approve_request(
                        request_id=approval.id,
                        approved_by="test_user",
                        feedback="Тестовое утверждение для выполнения"
                    )
                    db.refresh(plan)
                    print(f"   ✓ План утвержден")
                else:
                    # Directly approve
                    plan.status = "approved"
                    plan.approved_at = db.query(Plan).filter(Plan.id == plan.id).first().created_at
                    db.commit()
                    db.refresh(plan)
                    print(f"   ✓ План утвержден напрямую")
        else:
            plan = approved_plans[0]
            print(f"   ✓ Используется существующий план: {plan.id}")
        
        print(f"   ✓ Статус: {plan.status}")
        print(f"   ✓ Цель: {plan.goal[:60]}...")
        
        # Parse steps
        steps = plan.steps
        if isinstance(steps, str):
            import json
            try:
                steps = json.loads(steps)
            except:
                steps = []
        
        print(f"   ✓ Шагов: {len(steps) if steps else 0}")
        
        # 2. Test execution service
        print("\n2. Тестирование execution service...")
        execution_service = ExecutionService(db)
        
        # Get execution status before
        status_before = execution_service.get_execution_status(plan.id)
        print(f"   ✓ Статус до выполнения: {status_before['status']}")
        print(f"   ✓ Прогресс: {status_before['progress']:.1f}%")
        
        # 3. Execute plan
        print("\n3. Запуск выполнения плана...")
        print("   ⚠️ Внимание: выполнение может занять время (зависит от количества шагов)")
        
        try:
            executed_plan = await execution_service.execute_plan(plan.id)
            
            print(f"   ✓ Выполнение завершено")
            print(f"   ✓ Финальный статус: {executed_plan.status}")
            print(f"   ✓ Текущий шаг: {executed_plan.current_step}")
            
            # Get execution status after
            status_after = execution_service.get_execution_status(plan.id)
            print(f"   ✓ Прогресс: {status_after['progress']:.1f}%")
            
            if executed_plan.actual_duration:
                print(f"   ✓ Фактическое время: {executed_plan.actual_duration / 60:.1f} минут")
            
            # 4. Check results
            print("\n4. Проверка результатов...")
            
            if executed_plan.status == "completed":
                print("   ✅ План успешно выполнен!")
            elif executed_plan.status == "executing":
                print("   ⚠️ План все еще выполняется (возможно, ожидает утверждения шага)")
            elif executed_plan.status == "failed":
                print("   ❌ План завершился с ошибкой")
                print(f"   Остановлен на шаге: {executed_plan.current_step}")
            else:
                print(f"   ℹ️ Статус: {executed_plan.status}")
            
            print("\n" + "=" * 60)
            print("✅ Тест завершен")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n   ✗ Ошибка выполнения: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(test_execution_engine())
    sys.exit(0 if success else 1)

