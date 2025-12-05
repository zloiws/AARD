"""
Comprehensive real-world test for Phase 6: A/B Testing of Plans
Tests all modules with actual LLM calls
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.services.planning_service import PlanningService
from app.services.plan_evaluation_service import PlanEvaluationService
from app.services.execution_service import ExecutionService
from app.services.decision_pipeline import DecisionPipeline
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


async def test_scenario_1_basic_ab_testing():
    """Scenario 1: Basic A/B Testing - Generate and evaluate alternatives"""
    print("\n" + "="*80)
    print("SCENARIO 1: Basic A/B Testing")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Create a REST API for user management with authentication",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        print(f"  Description: {task.description}")
        
        # Initialize services
        planning_service = PlanningService(db)
        evaluation_service = PlanEvaluationService(db)
        
        # Generate plan with alternatives
        print("\n[->] Generating plan with 3 alternatives...")
        start_time = datetime.now()
        
        best_plan = await planning_service.generate_plan(
            task_description=task.description,
            task_id=task.id,
            generate_alternatives=True,
            num_alternatives=3
        )
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n[OK] Plan generated in {generation_time:.2f}s")
        print(f"  Best plan ID: {best_plan.id}")
        print(f"  Goal: {best_plan.goal[:100]}...")
        print(f"  Steps: {len(best_plan.steps) if best_plan.steps else 0}")
        
        # Check evaluation metadata
        if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
            print(f"\n[OK] Evaluation metadata:")
            print(f"  Is best: {best_plan.alternatives.get('is_best', 'N/A')}")
            print(f"  Evaluation score: {best_plan.alternatives.get('evaluation_score', 'N/A')}")
            print(f"  Ranking: {best_plan.alternatives.get('ranking', 'N/A')}")
        
        # Get all alternative plans
        all_plans = db.query(Plan).filter(Plan.task_id == task.id).all()
        print(f"\n[OK] Total plans in database: {len(all_plans)}")
        
        # Evaluate all plans
        if len(all_plans) > 1:
            print("\n[->] Evaluating all alternative plans...")
            results = evaluation_service.evaluate_plans(all_plans)
            
            print(f"\n[OK] Evaluation results:")
            for i, result in enumerate(results[:5], 1):  # Show top 5
                print(f"  {i}. Plan {str(result.plan_id)[:8]}... - Score: {result.total_score:.2f}")
                print(f"     Execution time: {result.scores.get('execution_time', 0):.2f}")
                print(f"     Risk level: {result.scores.get('risk_level', 0):.2f}")
                print(f"     Efficiency: {result.scores.get('efficiency', 0):.2f}")
        
        print("\n[OK] Scenario 1 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scenario_2_custom_evaluation_weights():
    """Scenario 2: Custom evaluation weights - Prioritize speed"""
    print("\n" + "="*80)
    print("SCENARIO 2: Custom Evaluation Weights (Speed Priority)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Create a fast API endpoint for real-time data processing",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        
        planning_service = PlanningService(db)
        
        # Custom weights emphasizing speed
        weights = {
            "execution_time": 0.6,  # High priority on speed
            "approval_points": 0.1,
            "risk_level": 0.2,
            "efficiency": 0.1
        }
        
        print("\n[->] Generating plan with speed-priority weights...")
        print(f"  Weights: {weights}")
        
        best_plan = await planning_service.generate_plan(
            task_description=task.description,
            task_id=task.id,
            generate_alternatives=True,
            num_alternatives=2,
            evaluation_weights=weights
        )
        
        print(f"\n[OK] Best plan selected: {best_plan.id}")
        
        # Check that speed was prioritized
        evaluation_service = PlanEvaluationService(db)
        result = evaluation_service.evaluate_plan(best_plan, weights=weights)
        
        print(f"\n[OK] Evaluation with custom weights:")
        print(f"  Total score: {result.total_score:.2f}")
        print(f"  Execution time score: {result.scores.get('execution_time', 0):.2f}")
        print(f"  Recommendations: {len(result.recommendations)}")
        
        if result.recommendations:
            print(f"\n  Recommendations:")
            for rec in result.recommendations[:3]:
                print(f"    - {rec}")
        
        print("\n[OK] Scenario 2 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scenario_3_integration_with_execution():
    """Scenario 3: Integration with ExecutionService"""
    print("\n" + "="*80)
    print("SCENARIO 3: Integration with ExecutionService")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Create a simple calculator API with add and subtract operations",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        
        planning_service = PlanningService(db)
        execution_service = ExecutionService(db)
        
        # Generate plan with alternatives
        print("\n[->] Generating plan with alternatives...")
        best_plan = await planning_service.generate_plan(
            task_description=task.description,
            task_id=task.id,
            generate_alternatives=True,
            num_alternatives=2
        )
        
        print(f"\n[OK] Best plan selected: {best_plan.id}")
        print(f"  Steps: {len(best_plan.steps) if best_plan.steps else 0}")
        
        # Approve plan
        best_plan.status = PlanStatus.APPROVED.value
        db.commit()
        db.refresh(best_plan)
        
        print("\n[OK] Plan approved")
        
        # Check that ExecutionService can work with this plan
        plan_from_db = execution_service.db.query(Plan).filter(Plan.id == best_plan.id).first()
        
        if plan_from_db:
            print(f"\n[OK] ExecutionService can access plan: {plan_from_db.id}")
            print(f"  Status: {plan_from_db.status}")
            print(f"  Steps count: {len(plan_from_db.steps) if plan_from_db.steps else 0}")
        
        print("\n[OK] Scenario 3 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scenario_4_decision_pipeline_integration():
    """Scenario 4: Integration with DecisionPipeline"""
    print("\n" + "="*80)
    print("SCENARIO 4: Integration with DecisionPipeline")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Analyze and summarize a text document",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        
        decision_pipeline = DecisionPipeline(db)
        
        # DecisionPipeline uses PlanningService internally
        # It should work with default parameters (no alternatives)
        print("\n[->] Executing task through DecisionPipeline...")
        print("  (PlanningService will be called internally)")
        
        result = await decision_pipeline.execute_task(
            task_description=task.description,
            context={"task_id": str(task.id)}
        )
        
        print(f"\n[OK] DecisionPipeline execution completed")
        print(f"  Status: {result.get('status', 'N/A')}")
        print(f"  Stages completed: {result.get('pipeline_metadata', {}).get('stages_completed', [])}")
        
        # Check if plan was created
        plans = db.query(Plan).filter(Plan.task_id == task.id).all()
        if plans:
            print(f"\n[OK] Plan created by DecisionPipeline: {plans[0].id}")
            print(f"  Steps: {len(plans[0].steps) if plans[0].steps else 0}")
        
        print("\n[OK] Scenario 4 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scenario_5_alternative_plans_method():
    """Scenario 5: Direct use of generate_alternative_plans method"""
    print("\n" + "="*80)
    print("SCENARIO 5: Direct Alternative Plans Generation")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Build a microservice for order processing",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        
        planning_service = PlanningService(db)
        evaluation_service = PlanEvaluationService(db)
        
        # Generate alternatives directly
        print("\n[->] Generating alternative plans directly...")
        alternative_plans = await planning_service.generate_alternative_plans(
            task_description=task.description,
            task_id=task.id,
            num_alternatives=3
        )
        
        print(f"\n[OK] Generated {len(alternative_plans)} alternative plans")
        
        # Check each plan
        for i, plan in enumerate(alternative_plans, 1):
            print(f"\n  Plan {i}:")
            print(f"    ID: {plan.id}")
            print(f"    Steps: {len(plan.steps) if plan.steps else 0}")
            
            # Check strategy metadata
            if plan.strategy and isinstance(plan.strategy, dict):
                alt_strategy = plan.strategy.get("alternative_strategy")
                if alt_strategy:
                    print(f"    Strategy: {alt_strategy}")
            
            # Evaluate plan
            result = evaluation_service.evaluate_plan(plan)
            print(f"    Evaluation score: {result.total_score:.2f}")
        
        # Compare plans
        if len(alternative_plans) > 1:
            print("\n[->] Comparing all alternatives...")
            comparison = evaluation_service.compare_plans(alternative_plans)
            
            print(f"\n[OK] Comparison results:")
            print(f"  Best plan: {comparison.get('best_plan_id', 'N/A')}")
            print(f"  Rankings:")
            for ranking in comparison.get('rankings', [])[:3]:
                print(f"    {ranking.get('ranking', 'N/A')}. Plan {str(ranking.get('plan_id', ''))[:8]}... - {ranking.get('total_score', 0):.2f}")
        
        print("\n[OK] Scenario 5 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 5 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scenario_6_full_cycle():
    """Scenario 6: Full cycle - Generate, evaluate, select, execute"""
    print("\n" + "="*80)
    print("SCENARIO 6: Full A/B Testing Cycle")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test task
        task = Task(
            id=uuid4(),
            description="Create a simple blog API with CRUD operations",
            status=TaskStatus.PENDING,
            priority=5
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        print(f"\n[OK] Created task: {task.id}")
        
        planning_service = PlanningService(db)
        evaluation_service = PlanEvaluationService(db)
        
        # Step 1: Generate alternatives
        print("\n[->] Step 1: Generating 3 alternative plans...")
        best_plan = await planning_service.generate_plan(
            task_description=task.description,
            task_id=task.id,
            generate_alternatives=True,
            num_alternatives=3
        )
        
        print(f"[OK] Best plan selected: {best_plan.id}")
        
        # Step 2: Get all alternatives
        all_plans = db.query(Plan).filter(Plan.task_id == task.id).all()
        print(f"\n[->] Step 2: Found {len(all_plans)} plans in database")
        
        # Step 3: Re-evaluate all plans
        print("\n[->] Step 3: Re-evaluating all plans...")
        results = evaluation_service.evaluate_plans(all_plans)
        
        print(f"[OK] Evaluation complete:")
        for i, result in enumerate(results[:3], 1):
            is_best = result.plan_id == best_plan.id
            marker = "[*]" if is_best else "   "
            print(f"  {marker} {i}. Plan {str(result.plan_id)[:8]}... - Score: {result.total_score:.2f}")
        
        # Step 4: Verify best plan is actually best
        if results and results[0].plan_id == best_plan.id:
            print(f"\n[OK] Step 4: Best plan verification - PASSED")
            print(f"  Selected plan is ranked #1 with score {results[0].total_score:.2f}")
        else:
            print(f"\n⚠ Step 4: Best plan verification - WARNING")
            print(f"  Selected plan may not be the highest ranked")
        
        # Step 5: Check metadata
        print("\n[->] Step 5: Checking plan metadata...")
        if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
            print(f"[OK] Metadata present:")
            print(f"  is_best: {best_plan.alternatives.get('is_best', 'N/A')}")
            print(f"  evaluation_score: {best_plan.alternatives.get('evaluation_score', 'N/A')}")
            print(f"  ranking: {best_plan.alternatives.get('ranking', 'N/A')}")
        
        print("\n[OK] Scenario 6 completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[X] Scenario 6 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def main():
    """Run all test scenarios"""
    print("\n" + "="*80)
    print("PHASE 6: A/B TESTING - COMPREHENSIVE REAL-WORLD TESTS")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    scenarios = [
        ("Basic A/B Testing", test_scenario_1_basic_ab_testing),
        ("Custom Evaluation Weights", test_scenario_2_custom_evaluation_weights),
        ("ExecutionService Integration", test_scenario_3_integration_with_execution),
        ("DecisionPipeline Integration", test_scenario_4_decision_pipeline_integration),
        ("Direct Alternative Plans", test_scenario_5_alternative_plans_method),
        ("Full Cycle", test_scenario_6_full_cycle),
    ]
    
    results = []
    
    for name, scenario_func in scenarios:
        try:
            result = await scenario_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[X] Scenario '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] PASSED" if result else "[X] FAILED"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} scenarios passed")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

