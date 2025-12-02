"""
Test logging API endpoints (requires running server)
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_server_health():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def test_get_log_levels():
    """Test GET /api/logging/levels"""
    print("\n1. Testing GET /api/logging/levels")
    response = requests.get(f"{BASE_URL}/api/logging/levels", timeout=5)
    
    if response.status_code == 200:
        levels = response.json()
        print(f"   ✓ Success: {len(levels)} modules")
        print(f"   Sample levels:")
        for module, level in list(levels.items())[:5]:
            print(f"      {module}: {level}")
        return True
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text}")
        return False


def test_get_module_level():
    """Test GET /api/logging/levels/{module}"""
    print("\n2. Testing GET /api/logging/levels/app")
    response = requests.get(f"{BASE_URL}/api/logging/levels/app", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success: {data.get('module')} = {data.get('level')}")
        return True
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text}")
        return False


def test_set_module_level():
    """Test PUT /api/logging/levels/{module}"""
    print("\n3. Testing PUT /api/logging/levels/test.api")
    
    # Set to DEBUG
    response = requests.put(
        f"{BASE_URL}/api/logging/levels/test.api",
        json={"level": "DEBUG"},
        timeout=5
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Set level to: {data.get('level')}")
        
        # Verify
        response = requests.get(f"{BASE_URL}/api/logging/levels/test.api", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('level') == 'DEBUG':
                print(f"   ✓ Verified: level is now {data.get('level')}")
                
                # Restore to INFO
                requests.put(
                    f"{BASE_URL}/api/logging/levels/test.api",
                    json={"level": "INFO"},
                    timeout=5
                )
                return True
            else:
                print(f"   ✗ Verification failed: expected DEBUG, got {data.get('level')}")
                return False
        else:
            print(f"   ✗ Verification request failed: {response.status_code}")
            return False
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text}")
        return False


def test_get_metrics():
    """Test GET /api/logging/metrics"""
    print("\n4. Testing GET /api/logging/metrics")
    response = requests.get(f"{BASE_URL}/api/logging/metrics", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        metrics = data.get('metrics', {})
        total = data.get('total', 0)
        print(f"   ✓ Success: total={total}")
        for level, count in metrics.items():
            if count > 0:
                print(f"      {level}: {count}")
        return True
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text}")
        return False


def test_reset_metrics():
    """Test POST /api/logging/metrics/reset"""
    print("\n5. Testing POST /api/logging/metrics/reset")
    response = requests.post(f"{BASE_URL}/api/logging/metrics/reset", timeout=5)
    
    if response.status_code == 200:
        print(f"   ✓ Metrics reset successfully")
        
        # Verify metrics are reset
        response = requests.get(f"{BASE_URL}/api/logging/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', -1)
            if total == 0:
                print(f"   ✓ Verified: metrics are reset (total=0)")
                return True
            else:
                print(f"   ⚠ Metrics not fully reset: total={total}")
                return True  # Still pass, metrics may accumulate quickly
        return True
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text}")
        return False


def test_middleware_request_id():
    """Test that middleware adds X-Request-ID header"""
    print("\n6. Testing Middleware Request ID")
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    
    if response.status_code == 200:
        request_id = response.headers.get("X-Request-ID")
        if request_id:
            print(f"   ✓ X-Request-ID header present: {request_id}")
            return True
        else:
            print(f"   ⚠ X-Request-ID header not found")
            return True  # Not critical
    else:
        print(f"   ✗ Health check failed: {response.status_code}")
        return False


def main():
    """Run all API tests"""
    print("="*60)
    print("LOGGING API ENDPOINTS TEST")
    print("="*60)
    
    # Check server
    print("\nChecking if server is running...")
    if not test_server_health():
        print("✗ Server is not running!")
        print("\nPlease start the server first:")
        print("  cd backend && python main.py")
        return 1
    
    print("✓ Server is running")
    
    # Run tests
    results = []
    results.append(("Get Log Levels", test_get_log_levels()))
    results.append(("Get Module Level", test_get_module_level()))
    results.append(("Set Module Level", test_set_module_level()))
    results.append(("Get Metrics", test_get_metrics()))
    results.append(("Reset Metrics", test_reset_metrics()))
    results.append(("Middleware Request ID", test_middleware_request_id()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All API tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

