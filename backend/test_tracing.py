"""
Test script for OpenTelemetry tracing
"""
import asyncio
import httpx
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 30.0


async def test_tracing():
    """Test tracing functionality"""
    print("=" * 60)
    print("OpenTelemetry Tracing Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        # Test 1: Make a chat request to generate a trace
        print("\n1. Testing trace generation with chat request...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/chat/",
                json={
                    "message": "Привет! Это тест трассировки.",
                    "task_type": "general_chat"
                }
            )
            
            if response.status_code == 200:
                print("✓ Chat request successful")
                data = response.json()
                print(f"  Response: {data.get('response', '')[:100]}...")
                
                # Get trace_id from response headers
                trace_id = response.headers.get("X-Trace-ID")
                if trace_id:
                    print(f"  Trace ID from header: {trace_id}")
            else:
                print(f"✗ Chat request failed: {response.status_code}")
                print(f"  Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Error making chat request: {e}")
            return False
        
        # Wait a bit for traces to be saved
        await asyncio.sleep(2)
        
        # Test 2: List traces
        print("\n2. Testing trace listing...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/traces/",
                params={"page": 1, "page_size": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                traces = data.get("traces", [])
                total = data.get("total", 0)
                print(f"✓ Found {total} traces")
                
                if traces:
                    print(f"  Showing {len(traces)} traces:")
                    for i, trace in enumerate(traces[:5], 1):
                        print(f"    {i}. {trace.get('operation_name')} - {trace.get('status')} - {trace.get('trace_id')[:16]}...")
                else:
                    print("  ⚠ No traces found yet (may need to wait)")
            else:
                print(f"✗ Failed to list traces: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Error listing traces: {e}")
        
        # Test 3: Get trace statistics
        print("\n3. Testing trace statistics...")
        try:
            response = await client.get(f"{BASE_URL}/api/traces/stats/summary")
            
            if response.status_code == 200:
                stats = response.json()
                print("✓ Trace statistics:")
                print(f"  Total: {stats.get('total', 0)}")
                print(f"  Success: {stats.get('success', 0)}")
                print(f"  Error: {stats.get('error', 0)}")
                print(f"  Timeout: {stats.get('timeout', 0)}")
                print(f"  Avg Duration: {stats.get('avg_duration_ms', 0)} ms")
            else:
                print(f"✗ Failed to get statistics: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Error getting statistics: {e}")
        
        # Test 4: Get a specific trace (if we have one)
        print("\n4. Testing trace details...")
        try:
            # First get list to find a trace_id
            list_response = await client.get(
                f"{BASE_URL}/api/traces/",
                params={"page": 1, "page_size": 1}
            )
            
            if list_response.status_code == 200:
                list_data = list_response.json()
                traces = list_data.get("traces", [])
                
                if traces:
                    trace_id = traces[0].get("trace_id")
                    print(f"  Fetching details for trace: {trace_id[:16]}...")
                    
                    response = await client.get(f"{BASE_URL}/api/traces/{trace_id}")
                    
                    if response.status_code == 200:
                        trace_data = response.json()
                        print("✓ Trace details retrieved:")
                        print(f"  Operation: {trace_data.get('operation_name')}")
                        print(f"  Status: {trace_data.get('status')}")
                        print(f"  Duration: {trace_data.get('duration_ms')} ms")
                        print(f"  Start Time: {trace_data.get('start_time')}")
                    else:
                        print(f"✗ Failed to get trace details: {response.status_code}")
                else:
                    print("  ⚠ No traces available for details test")
            else:
                print(f"✗ Failed to list traces for details test: {list_response.status_code}")
                
        except Exception as e:
            print(f"✗ Error getting trace details: {e}")
        
        # Test 5: Get spans for a trace
        print("\n5. Testing trace spans...")
        try:
            list_response = await client.get(
                f"{BASE_URL}/api/traces/",
                params={"page": 1, "page_size": 1}
            )
            
            if list_response.status_code == 200:
                list_data = list_response.json()
                traces = list_data.get("traces", [])
                
                if traces:
                    trace_id = traces[0].get("trace_id")
                    print(f"  Fetching spans for trace: {trace_id[:16]}...")
                    
                    response = await client.get(f"{BASE_URL}/api/traces/{trace_id}/spans")
                    
                    if response.status_code == 200:
                        spans = response.json()
                        print(f"✓ Found {len(spans)} spans for trace")
                        for i, span in enumerate(spans[:3], 1):
                            print(f"    {i}. {span.get('operation_name')} - {span.get('status')}")
                    else:
                        print(f"✗ Failed to get spans: {response.status_code}")
                else:
                    print("  ⚠ No traces available for spans test")
            else:
                print(f"✗ Failed to list traces for spans test: {list_response.status_code}")
                
        except Exception as e:
            print(f"✗ Error getting spans: {e}")
    
    print("\n" + "=" * 60)
    print("Tracing test completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_tracing())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

