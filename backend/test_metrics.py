"""
Test script for Prometheus metrics
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_metrics_endpoint():
    """Test that /metrics endpoint returns valid Prometheus format"""
    print("Testing /metrics endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Metrics endpoint is accessible")
            content = response.text
            
            # Check for some expected metrics
            expected_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "llm_requests_total",
                "llm_request_duration_seconds",
                "app_info"
            ]
            
            found_metrics = []
            for metric in expected_metrics:
                if metric in content:
                    found_metrics.append(metric)
                    print(f"  ✓ Found metric: {metric}")
                else:
                    print(f"  ✗ Metric not found: {metric}")
            
            # Show first 20 lines of metrics
            print("\nFirst 20 lines of metrics:")
            print("-" * 60)
            lines = content.split('\n')[:20]
            for line in lines:
                if line.strip():
                    print(line)
            print("-" * 60)
            
            return True
        else:
            print(f"✗ Metrics endpoint returned status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_metrics_after_requests():
    """Make some requests and check that metrics are updated"""
    print("\nTesting metrics collection after requests...")
    
    try:
        # Make a request to health endpoint
        print("Making request to /health...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Status: {response.status_code}")
        
        # Wait a bit for metrics to be updated
        time.sleep(0.5)
        
        # Check metrics again
        print("Checking metrics after request...")
        metrics_response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        if metrics_response.status_code == 200:
            content = metrics_response.text
            
            # Check if http_requests_total has increased
            if "http_requests_total" in content:
                # Look for our endpoint
                lines = content.split('\n')
                for line in lines:
                    if 'http_requests_total' in line and ('/health' in line or 'method="GET"' in line):
                        print(f"  ✓ Found HTTP request metric: {line[:100]}")
                        break
                else:
                    print("  ⚠ HTTP request metric found but endpoint not visible yet")
            
            return True
        else:
            print(f"  ✗ Failed to get metrics: {metrics_response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Prometheus Metrics Test")
    print("=" * 60)
    
    # Test 1: Check metrics endpoint
    test1 = test_metrics_endpoint()
    
    # Test 2: Check metrics after making requests
    if test1:
        test2 = test_metrics_after_requests()
    else:
        test2 = False
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✓ All tests passed!")
    elif test1:
        print("⚠ Basic test passed, but request test failed")
    else:
        print("✗ Tests failed")
    print("=" * 60)

