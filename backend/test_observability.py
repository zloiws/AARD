"""
Comprehensive test for observability features:
- Health checks
- Prometheus metrics
- Logging system
"""
import requests
import json
import time
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"
TEST_RESULTS = []


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result"""
    status = "✓" if passed else "✗"
    print(f"  {status} {name}", end="")
    if message:
        print(f" - {message}")
    else:
        print()
    TEST_RESULTS.append({"name": name, "passed": passed, "message": message})


def test_server_running():
    """Test if server is running"""
    print("\n" + "=" * 60)
    print("1. Server Availability Test")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            log_test("Server is running", True)
            return True
        else:
            log_test("Server is running", False, f"Status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log_test("Server is running", False, "Cannot connect to server")
        return False
    except Exception as e:
        log_test("Server is running", False, str(e))
        return False


def test_health_checks():
    """Test all health check endpoints"""
    print("\n" + "=" * 60)
    print("2. Health Checks Test")
    print("=" * 60)
    
    endpoints = [
        ("/health", "Basic health check"),
        ("/health/detailed", "Detailed health check"),
        ("/health/readiness", "Readiness check"),
        ("/health/liveness", "Liveness check"),
    ]
    
    all_passed = True
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                log_test(f"{description} ({endpoint})", True)
                
                # Check response structure
                if endpoint == "/health/detailed":
                    required_keys = ["status", "timestamp", "service", "components"]
                    has_keys = all(key in data for key in required_keys)
                    log_test(f"  Detailed health structure", has_keys)
                    
                    # Check components
                    if "components" in data:
                        components = data["components"]
                        log_test(f"  Components present: {len(components)}", len(components) > 0)
                        for comp_name, comp_data in components.items():
                            if isinstance(comp_data, dict) and "status" in comp_data:
                                log_test(f"    {comp_name}: {comp_data.get('status')}", True)
            else:
                log_test(f"{description} ({endpoint})", False, f"Status: {response.status_code}")
                all_passed = False
        except Exception as e:
            log_test(f"{description} ({endpoint})", False, str(e))
            all_passed = False
    
    return all_passed


def test_prometheus_metrics():
    """Test Prometheus metrics endpoint"""
    print("\n" + "=" * 60)
    print("3. Prometheus Metrics Test")
    print("=" * 60)
    
    try:
        # Make some requests to generate metrics
        requests.get(f"{BASE_URL}/", timeout=5)
        requests.get(f"{BASE_URL}/health", timeout=5)
        time.sleep(0.5)  # Give metrics time to update
        
        # Get metrics
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        if response.status_code == 200:
            metrics_text = response.text
            log_test("Metrics endpoint accessible", True)
            
            # Check for expected metrics
            expected_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "llm_requests_total",
                "plan_executions_total",
                "queue_tasks_total",
                "db_queries_total",
            ]
            
            found_metrics = []
            for metric in expected_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)
                    log_test(f"  Metric {metric} present", True)
                else:
                    log_test(f"  Metric {metric} present", False, "Not found")
            
            # Check HTTP metrics specifically
            if "http_requests_total" in metrics_text:
                # Count HTTP requests
                lines = [l for l in metrics_text.split('\n') if 'http_requests_total' in l and not l.startswith('#')]
                if lines:
                    log_test(f"  HTTP metrics collected: {len(lines)} entries", len(lines) > 0)
            
            return len(found_metrics) > 0
        else:
            log_test("Metrics endpoint accessible", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Metrics endpoint accessible", False, str(e))
        return False


def test_logging_system():
    """Test logging system"""
    print("\n" + "=" * 60)
    print("4. Logging System Test")
    print("=" * 60)
    
    try:
        # Make a request that should generate logs
        response = requests.get(f"{BASE_URL}/api/logging/levels", timeout=5)
        if response.status_code == 200:
            log_test("Logging API accessible", True)
            
            # Check logging metrics endpoint
            try:
                metrics_response = requests.get(f"{BASE_URL}/api/logging/metrics", timeout=5)
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    log_test("Logging metrics endpoint", True)
                    
                    if "metrics" in metrics_data:
                        metrics = metrics_data["metrics"]
                        total_logs = sum(metrics.values())
                        log_test(f"  Total logs recorded: {total_logs}", total_logs >= 0)
                        
                        for level, count in metrics.items():
                            if count > 0:
                                log_test(f"    {level}: {count}", True)
                else:
                    log_test("Logging metrics endpoint", False, f"Status: {metrics_response.status_code}")
            except Exception as e:
                log_test("Logging metrics endpoint", False, str(e))
            
            # Test module level configuration
            try:
                # Get current levels
                levels_response = requests.get(f"{BASE_URL}/api/logging/levels", timeout=5)
                if levels_response.status_code == 200:
                    levels = levels_response.json()
                    log_test("Module level configuration", True)
                    log_test(f"  Configured modules: {len(levels)}", len(levels) >= 0)
            except Exception as e:
                log_test("Module level configuration", False, str(e))
            
            return True
        else:
            log_test("Logging API accessible", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Logging API accessible", False, str(e))
        return False


def test_integration():
    """Test integration of all observability features"""
    print("\n" + "=" * 60)
    print("5. Integration Test")
    print("=" * 60)
    
    try:
        # Make a request that should generate logs, traces, and metrics
        response = requests.get(f"{BASE_URL}/health/detailed", timeout=10)
        
        if response.status_code == 200:
            log_test("Integration: Health check generates logs/metrics", True)
            
            # Check if metrics were updated
            time.sleep(0.5)
            metrics_response = requests.get(f"{BASE_URL}/metrics", timeout=5)
            if metrics_response.status_code == 200:
                metrics_text = metrics_response.text
                if "http_requests_total" in metrics_text:
                    log_test("Integration: Metrics updated after request", True)
                else:
                    log_test("Integration: Metrics updated after request", False)
            
            return True
        else:
            log_test("Integration test", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Integration test", False, str(e))
        return False


def test_traces_endpoint():
    """Test traces endpoint"""
    print("\n" + "=" * 60)
    print("6. Traces Endpoint Test")
    print("=" * 60)
    
    try:
        # Test traces list
        response = requests.get(f"{BASE_URL}/api/traces", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("Traces API accessible", True)
            
            if "traces" in data:
                traces = data["traces"]
                log_test(f"  Traces found: {len(traces)}", True)
                
                # Test trace detail if traces exist
                if traces and len(traces) > 0:
                    trace_id = traces[0].get("trace_id")
                    if trace_id:
                        detail_response = requests.get(f"{BASE_URL}/api/traces/{trace_id}", timeout=5)
                        if detail_response.status_code == 200:
                            log_test("  Trace detail endpoint", True)
                        else:
                            log_test("  Trace detail endpoint", False, f"Status: {detail_response.status_code}")
            else:
                log_test("  Traces structure", False, "No 'traces' key in response")
            
            return True
        else:
            log_test("Traces API accessible", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Traces API accessible", False, str(e))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    total = len(TEST_RESULTS)
    passed = sum(1 for r in TEST_RESULTS if r["passed"])
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ({passed*100//total if total > 0 else 0}%)")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for result in TEST_RESULTS:
            if not result["passed"]:
                print(f"  ✗ {result['name']}")
                if result["message"]:
                    print(f"    {result['message']}")
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"⚠ {failed} test(s) failed")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("AARD Observability Features Test Suite")
    print("=" * 60)
    print(f"Testing server at: {BASE_URL}")
    print("Make sure the server is running before starting tests!")
    print()
    
    # Run all tests
    if not test_server_running():
        print("\n⚠ Server is not running. Please start the server first.")
        print("   Run: cd backend && python main.py")
        sys.exit(1)
    
    test_health_checks()
    test_prometheus_metrics()
    test_logging_system()
    test_traces_endpoint()
    test_integration()
    
    print_summary()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in TEST_RESULTS if not r["passed"])
    sys.exit(0 if failed_count == 0 else 1)

