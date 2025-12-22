"""
Test script for new components: Request Ranking, Task Queue, Checkpoint
"""
import asyncio
import sys
from datetime import datetime

import httpx

BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30.0


async def test_request_ranking():
    """Test request ranking system"""
    print("\n" + "=" * 60)
    print("Testing Request Ranking System")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Test 1: List requests
        print("\n1. Testing request listing...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/requests/",
                params={"page": 1, "page_size": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                requests = data.get("requests", [])
                total = data.get("total", 0)
                print(f"✓ Found {total} requests")
                
                if requests:
                    print(f"  Showing {len(requests)} requests:")
                    for i, req in enumerate(requests[:3], 1):
                        print(f"    {i}. {req.get('request_type')} - {req.get('status')} - rank: {req.get('overall_rank', 0):.3f}")
            else:
                print(f"✗ Failed to list requests: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Error listing requests: {e}")
        
        # Test 2: Get ranked requests
        print("\n2. Testing ranked requests...")
        try:
            response = await client.get(f"{BASE_URL}/api/requests/ranked", params={"limit": 5})
            
            if response.status_code == 200:
                data = response.json()
                requests = data.get("requests", [])
                print(f"✓ Found {len(requests)} top-ranked requests")
                
                if requests:
                    for i, req in enumerate(requests[:3], 1):
                        print(f"    {i}. {req.get('request_type')} - rank: {req.get('overall_rank', 0):.3f}")
            else:
                print(f"✗ Failed to get ranked requests: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error getting ranked requests: {e}")
        
        # Test 3: Get statistics
        print("\n3. Testing request statistics...")
        try:
            response = await client.get(f"{BASE_URL}/api/requests/stats/summary")
            
            if response.status_code == 200:
                stats = response.json()
                print("✓ Request statistics:")
                print(f"  Total: {stats.get('total', 0)}")
                print(f"  Success: {stats.get('success', 0)}")
                print(f"  Failed: {stats.get('failed', 0)}")
                print(f"  Avg Rank: {stats.get('avg_rank', 0):.3f}")
            else:
                print(f"✗ Failed to get statistics: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error getting statistics: {e}")


async def test_task_queues():
    """Test task queue system"""
    print("\n" + "=" * 60)
    print("Testing Task Queue System")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Test 1: Create a queue
        print("\n1. Testing queue creation...")
        queue_id = None
        try:
            response = await client.post(
                f"{BASE_URL}/api/queues/",
                json={
                    "name": "test_queue",
                    "description": "Test queue",
                    "max_concurrent": 2,
                    "priority": 7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                queue_id = data.get("id")
                print(f"✓ Queue created: {data.get('name')} (ID: {queue_id})")
            else:
                print(f"✗ Failed to create queue: {response.status_code}")
                print(f"  Error: {response.text}")
                # Try to get existing queue
                list_response = await client.get(f"{BASE_URL}/api/queues/")
                if list_response.status_code == 200:
                    queues = list_response.json()
                    if queues:
                        queue_id = queues[0].get("id")
                        print(f"  Using existing queue: {queue_id}")
                
        except Exception as e:
            print(f"✗ Error creating queue: {e}")
        
        if not queue_id:
            print("  ⚠ Skipping queue tests - no queue available")
            return
        
        # Test 2: Add a task
        print("\n2. Testing task addition...")
        task_id = None
        try:
            response = await client.post(
                f"{BASE_URL}/api/queues/{queue_id}/tasks",
                json={
                    "task_type": "test_task",
                    "task_data": {"message": "Test task"},
                    "priority": 5,
                    "max_retries": 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("id")
                print(f"✓ Task added: {data.get('task_type')} (ID: {task_id})")
            else:
                print(f"✗ Failed to add task: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Error adding task: {e}")
        
        # Test 3: Get queue stats
        print("\n3. Testing queue statistics...")
        try:
            response = await client.get(f"{BASE_URL}/api/queues/{queue_id}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                print("✓ Queue statistics:")
                print(f"  Total: {stats.get('total', 0)}")
                print(f"  Pending: {stats.get('pending', 0)}")
                print(f"  Processing: {stats.get('processing', 0)}")
                print(f"  Completed: {stats.get('completed', 0)}")
            else:
                print(f"✗ Failed to get queue stats: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error getting queue stats: {e}")


async def test_checkpoints():
    """Test checkpoint system"""
    print("\n" + "=" * 60)
    print("Testing Checkpoint System")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Test 1: List checkpoints (will be empty initially)
        print("\n1. Testing checkpoint listing...")
        try:
            # Need a plan_id to test - try to get one from plans
            plans_response = await client.get(f"{BASE_URL}/api/plans/", params={"limit": 1})
            
            if plans_response.status_code == 200:
                plans_data = plans_response.json()
                # Handle both list and dict response formats
                if isinstance(plans_data, list):
                    plans = plans_data
                else:
                    plans = plans_data.get("plans", [])
                
                if plans:
                    plan = plans[0] if isinstance(plans[0], dict) else plans[0]
                    plan_id = plan.get("id") if isinstance(plan, dict) else str(plan.id)
                    print(f"  Using plan: {plan_id}")
                    
                    response = await client.get(
                        f"{BASE_URL}/api/checkpoints/",
                        params={
                            "entity_type": "plan",
                            "entity_id": plan_id,
                            "limit": 10
                        }
                    )
                    
                    if response.status_code == 200:
                        checkpoints = response.json()
                        print(f"✓ Found {len(checkpoints)} checkpoints for plan")
                        
                        if checkpoints:
                            for i, cp in enumerate(checkpoints[:3], 1):
                                print(f"    {i}. {cp.get('reason', 'N/A')} - {cp.get('created_at', '')[:19]}")
                        else:
                            print("  ⚠ No checkpoints found (normal if plan hasn't been executed)")
                    else:
                        print(f"✗ Failed to list checkpoints: {response.status_code}")
                else:
                    print("  ⚠ No plans available for testing")
            else:
                print("  ⚠ Could not get plans for testing")
                
        except Exception as e:
            print(f"✗ Error listing checkpoints: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing New Components")
    print("=" * 60)
    
    # Wait a bit for server to start
    await asyncio.sleep(2)
    
    # Test server availability
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print(f"✗ Server not ready (status: {response.status_code})")
                return
    except Exception as e:
        print(f"✗ Server not available: {e}")
        print("  Please start the server first: python backend/main.py")
        return
    
    print("✓ Server is running")
    
    # Run tests
    await test_request_ranking()
    await test_task_queues()
    await test_checkpoints()
    
    print("\n" + "=" * 60)
    print("Testing completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

