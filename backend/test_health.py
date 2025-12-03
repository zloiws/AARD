"""
Test script for health check endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_basic_health():
    """Test basic health endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_detailed_health():
    """Test detailed health endpoint"""
    print("\nTesting /health/detailed endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health/detailed", timeout=10)
        print(f"  Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Overall status: {data.get('status')}")
            print(f"  ✓ Service: {data.get('service')}")
            print(f"  ✓ Environment: {data.get('environment')}")
            print(f"\n  Components:")
            for component, status in data.get('components', {}).items():
                comp_status = status.get('status', 'unknown')
                message = status.get('message', '')
                print(f"    - {component}: {comp_status} - {message}")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_readiness():
    """Test readiness endpoint"""
    print("\nTesting /health/readiness endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health/readiness", timeout=5)
        print(f"  Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {data.get('status')}")
            print(f"  ✓ Message: {data.get('message')}")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_liveness():
    """Test liveness endpoint"""
    print("\nTesting /health/liveness endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health/liveness", timeout=5)
        print(f"  Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {data.get('status')}")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Health Check Endpoints Test")
    print("=" * 60)
    
    test1 = test_basic_health()
    test2 = test_detailed_health()
    test3 = test_readiness()
    test4 = test_liveness()
    
    print("\n" + "=" * 60)
    if all([test1, test2, test3, test4]):
        print("✓ All tests passed!")
    else:
        print("⚠ Some tests failed or server is not running")
    print("=" * 60)

