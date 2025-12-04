"""
Run Test 6: Complex Multi-Step Decomposition
Tests detailed task breakdown requiring multiple implementation steps
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def print_separator(title: str):
    """Print test separator"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


async def test_6_complex_decomposition():
    """Test 6: Complex task requiring detailed multi-step decomposition"""
    print_separator("TEST 6: Complex Multi-Step Decomposition")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        # A complex task that should naturally decompose into many steps
        task_description = """Build a complete user authentication system with the following requirements:
        1. User registration with email validation
        2. Password hashing using bcrypt
        3. JWT token generation for authentication
        4. Login endpoint with rate limiting
        5. Password reset functionality with email verification
        6. Session management with Redis
        7. Role-based access control (admin, user, moderator)
        8. API endpoint documentation with OpenAPI/Swagger
        9. Unit tests for all authentication functions
        10. Integration tests for authentication flow"""
        
        print(f"📝 Task: {task_description[:100]}...")
        print("\n⏳ Generating detailed multi-step plan...")
        print("   (This complex task should decompose into 10+ steps)")
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        print(f"\n✅ Plan created!")
        print(f"   Plan ID: {plan.id}")
        print(f"   Total steps: {len(plan.steps)}")
        
        # Verify
        print("\n🔍 Verification:")
        assert plan is not None, "Plan should not be None"
        assert len(plan.steps) > 0, "Plan should have at least one step"
        
        # Check step count - for complex tasks, expect multiple steps
        if len(plan.steps) >= 5:
            print(f"   ✅ Plan has {len(plan.steps)} steps (good decomposition)")
        elif len(plan.steps) >= 3:
            print(f"   ⚠️ Plan has {len(plan.steps)} steps (moderate decomposition)")
        else:
            print(f"   ⚠️ Plan has {len(plan.steps)} steps (may be too generalized)")
        
        # Analyze step types
        print(f"\n📊 Step Analysis:")
        step_types = {}
        step_details = []
        
        for step in plan.steps:
            step_type = step.get('type', 'unknown')
            step_types[step_type] = step_types.get(step_type, 0) + 1
            
            step_details.append({
                'id': step.get('step_id', 'N/A'),
                'type': step_type,
                'description': step.get('description', 'N/A')[:60]
            })
        
        print(f"   Step types distribution:")
        for step_type, count in step_types.items():
            print(f"     - {step_type}: {count}")
        
        # Show all steps
        print(f"\n📋 All Steps ({len(plan.steps)}):")
        for i, step in enumerate(plan.steps, 1):
            desc = step.get('description', 'N/A')
            if len(desc) > 70:
                desc = desc[:70] + "..."
            step_type = step.get('type', 'unknown')
            step_id = step.get('step_id', 'N/A')
            print(f"   {i:2d}. [{step_type:8s}] {step_id:12s}: {desc}")
        
        # Check for specific requirements in steps
        print(f"\n🔍 Requirement Coverage:")
        requirements = [
            'email', 'validation', 'bcrypt', 'hash', 'jwt', 'token',
            'login', 'rate limit', 'reset', 'password', 'redis', 'session',
            'role', 'admin', 'access control', 'api', 'documentation',
            'swagger', 'openapi', 'test', 'unit', 'integration'
        ]
        
        all_step_text = " ".join([
            step.get('description', '').lower() for step in plan.steps
        ])
        
        found_requirements = []
        for req in requirements:
            if req in all_step_text:
                found_requirements.append(req)
        
        print(f"   Found {len(found_requirements)}/{len(requirements)} requirement keywords")
        if len(found_requirements) > 0:
            print(f"   Keywords: {', '.join(found_requirements[:10])}")
        
        # Check step dependencies/order
        print(f"\n🔍 Step Structure:")
        has_sequential_ids = True
        for i, step in enumerate(plan.steps, 1):
            step_id = step.get('step_id', '')
            expected_id = f"step_{i}"
            if step_id != expected_id:
                has_sequential_ids = False
                break
        
        if has_sequential_ids:
            print(f"   ✅ Step IDs are sequential (step_1, step_2, ...)")
        else:
            print(f"   ⚠️ Step IDs may not be sequential")
        
        # Check strategy details
        if plan.strategy and isinstance(plan.strategy, dict):
            print(f"\n📊 Strategy Details:")
            approach = plan.strategy.get('approach', 'N/A')
            if approach and approach != 'N/A':
                approach_str = str(approach)
                if len(approach_str) > 100:
                    approach_str = approach_str[:100] + "..."
                print(f"   Approach: {approach_str}")
            
            assumptions = plan.strategy.get('assumptions', [])
            constraints = plan.strategy.get('constraints', [])
            success_criteria = plan.strategy.get('success_criteria', [])
            
            print(f"   Assumptions: {len(assumptions) if isinstance(assumptions, list) else 0}")
            print(f"   Constraints: {len(constraints) if isinstance(constraints, list) else 0}")
            print(f"   Success criteria: {len(success_criteria) if isinstance(success_criteria, list) else 0}")
        
        # Evaluation
        print(f"\n📈 Evaluation:")
        score = 0
        max_score = 5
        
        if len(plan.steps) >= 5:
            score += 1
            print(f"   ✅ Step count ({len(plan.steps)}) >= 5")
        else:
            print(f"   ⚠️ Step count ({len(plan.steps)}) < 5 (may be too generalized)")
        
        if len(found_requirements) >= 5:
            score += 1
            print(f"   ✅ Requirement coverage ({len(found_requirements)} keywords)")
        else:
            print(f"   ⚠️ Requirement coverage ({len(found_requirements)} keywords) could be better")
        
        if len(plan.steps) >= 3:
            score += 1
            print(f"   ✅ Has multiple steps for complex task")
        else:
            print(f"   ⚠️ Only {len(plan.steps)} step(s) for complex task")
        
        if plan.strategy:
            score += 1
            print(f"   ✅ Has strategy defined")
        else:
            print(f"   ⚠️ No strategy defined")
        
        if has_sequential_ids:
            score += 1
            print(f"   ✅ Step IDs are well-structured")
        else:
            print(f"   ⚠️ Step IDs structure could be improved")
        
        print(f"\n   Score: {score}/{max_score}")
        
        if score >= 4:
            print(f"   🎯 Excellent decomposition!")
        elif score >= 3:
            print(f"   ✅ Good decomposition")
        else:
            print(f"   ⚠️ Decomposition could be improved")
        
        return plan
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" PLANNING SERVICE - TEST 6: COMPLEX MULTI-STEP DECOMPOSITION")
    print("=" * 70)
    
    try:
        plan = asyncio.run(test_6_complex_decomposition())
        
        if plan:
            print("\n" + "=" * 70)
            print(" ✅ TEST 6 COMPLETED!")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print(" ❌ TEST 6 FAILED!")
            print("=" * 70 + "\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

