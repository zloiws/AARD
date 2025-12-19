"""
Test script for plan-approval integration
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.models.approval import ApprovalRequestType
from app.models.plan import Plan
from app.services.approval_service import ApprovalService
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session


async def test_plan_approval_integration():
    """Test that plan creation automatically creates approval request"""
    print("=" * 60)
    print("Тест интеграции планирования с утверждениями")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 1. Create a simple plan
        print("\n1. Создание плана...")
        planning_service = PlanningService(db)
        
        task_description = "Протестировать интеграцию планирования с утверждениями"
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context={"test": True}
        )
        
        print(f"   ✓ План создан: {plan.id}")
        print(f"   ✓ Статус: {plan.status}")
        print(f"   ✓ Цель: {plan.goal[:50]}...")
        
        # 2. Check if approval request was created
        print("\n2. Проверка создания approval request...")
        approval_service = ApprovalService(db)
        
        # Get approval requests for this plan
        from app.models.approval import ApprovalRequest
        approvals = db.query(ApprovalRequest).filter(
            ApprovalRequest.plan_id == plan.id
        ).all()
        
        if not approvals:
            print("   ✗ Approval request не найден!")
            return False
        
        approval = approvals[0]
        print(f"   ✓ Approval request создан: {approval.id}")
        print(f"   ✓ Тип: {approval.request_type}")
        print(f"   ✓ Статус: {approval.status}")
        print(f"   ✓ Plan ID: {approval.plan_id}")
        
        if approval.plan_id != plan.id:
            print("   ✗ Plan ID не совпадает!")
            return False
        
        # 3. Check approval request data
        print("\n3. Проверка данных approval request...")
        request_data = approval.request_data
        print(f"   ✓ Goal: {request_data.get('goal', 'N/A')[:50]}...")
        print(f"   ✓ Version: {request_data.get('version', 'N/A')}")
        print(f"   ✓ Total steps: {request_data.get('total_steps', 'N/A')}")
        
        if approval.risk_assessment:
            print(f"   ✓ Risk rating: {approval.risk_assessment.get('rating', 'N/A')}")
        
        if approval.recommendation:
            print(f"   ✓ Recommendation: {approval.recommendation[:80]}...")
        
        # 4. Test approval
        print("\n4. Тестирование утверждения плана...")
        approval_service.approve_request(
            request_id=approval.id,
            approved_by="test_user",
            feedback="Тестовое утверждение"
        )
        
        # Refresh plan
        db.refresh(plan)
        
        print(f"   ✓ Approval request утвержден")
        print(f"   ✓ Статус плана: {plan.status}")
        
        if plan.status != "approved":
            print("   ✗ План не перешел в статус approved!")
            return False
        
        if not plan.approved_at:
            print("   ✗ approved_at не установлен!")
            return False
        
        print(f"   ✓ Дата утверждения: {plan.approved_at}")
        
        print("\n" + "=" * 60)
        print("✅ Все тесты пройдены успешно!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(test_plan_approval_integration())
    sys.exit(0 if success else 1)

