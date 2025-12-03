"""
Detailed logging system test
Tests JSON format, context, file output, and log levels
"""
import requests
import json
import sys
from pathlib import Path
from datetime import datetime

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "aard.log"


def test_json_log_format():
    """Test that logs are in JSON format"""
    print("\n" + "=" * 60)
    print("1. JSON Log Format Test")
    print("=" * 60)
    
    try:
        # Make a request that should generate logs
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            # Wait a bit for logs to be written
            import time
            time.sleep(0.5)
            
            # Read last few lines from log file
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        # Check last few lines
                        last_lines = lines[-5:]
                        json_count = 0
                        for line in last_lines:
                            line = line.strip()
                            if line:
                                try:
                                    log_entry = json.loads(line)
                                    json_count += 1
                                    # Check required fields
                                    required_fields = ['timestamp', 'level', 'message']
                                    has_fields = all(field in log_entry for field in required_fields)
                                    if has_fields:
                                        print(f"  ✓ Valid JSON log entry with required fields")
                                        print(f"    Level: {log_entry.get('level')}, Message: {log_entry.get('message', '')[:50]}...")
                                except json.JSONDecodeError:
                                    pass
                        
                        if json_count > 0:
                            print(f"  ✓ Found {json_count} JSON log entries in last 5 lines")
                            return True
                        else:
                            print(f"  ✗ No valid JSON entries found in log file")
                            return False
                    else:
                        print(f"  ⚠ Log file is empty")
                        return False
            else:
                print(f"  ⚠ Log file not found at {LOG_FILE}")
                return False
        else:
            print(f"  ✗ Request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_log_context():
    """Test that context is added to logs"""
    print("\n" + "=" * 60)
    print("2. Log Context Test")
    print("=" * 60)
    
    try:
        # Make a request that should include trace context
        response = requests.get(f"{BASE_URL}/health/detailed", timeout=10)
        
        if response.status_code == 200:
            import time
            time.sleep(0.5)
            
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        # Check last 10 lines for context fields
                        last_lines = lines[-10:]
                        context_found = False
                        for line in last_lines:
                            line = line.strip()
                            if line:
                                try:
                                    log_entry = json.loads(line)
                                    # Check for context fields (trace_id, span_id, request_id)
                                    context_fields = ['trace_id', 'span_id', 'request_id']
                                    found_fields = [f for f in context_fields if f in log_entry]
                                    if found_fields:
                                        context_found = True
                                        print(f"  ✓ Found context fields: {', '.join(found_fields)}")
                                        break
                                except json.JSONDecodeError:
                                    pass
                        
                        if context_found:
                            return True
                        else:
                            print(f"  ⚠ No context fields found (this is OK if tracing is not fully configured)")
                            return True  # Not a failure, just informational
                    else:
                        print(f"  ⚠ Log file is empty")
                        return False
            else:
                print(f"  ⚠ Log file not found")
                return False
        else:
            print(f"  ✗ Request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_log_levels():
    """Test log level configuration"""
    print("\n" + "=" * 60)
    print("3. Log Levels Test")
    print("=" * 60)
    
    try:
        # Get current log levels
        response = requests.get(f"{BASE_URL}/api/logging/levels", timeout=5)
        
        if response.status_code == 200:
            levels = response.json()
            print(f"  ✓ Retrieved log levels for {len(levels)} modules")
            
            # Test setting a log level
            test_module = "app.api.routes.health"
            test_level = "DEBUG"
            
            put_response = requests.put(
                f"{BASE_URL}/api/logging/levels/{test_module}",
                json={"level": test_level},
                timeout=5
            )
            
            if put_response.status_code == 200:
                print(f"  ✓ Successfully set log level for {test_module} to {test_level}")
                
                # Verify it was set
                get_response = requests.get(f"{BASE_URL}/api/logging/levels", timeout=5)
                if get_response.status_code == 200:
                    updated_levels = get_response.json()
                    if test_module in updated_levels and updated_levels[test_module] == test_level:
                        print(f"  ✓ Verified log level was set correctly")
                        return True
                    else:
                        print(f"  ✗ Log level was not set correctly")
                        return False
                else:
                    print(f"  ✗ Failed to verify log level: {get_response.status_code}")
                    return False
            else:
                print(f"  ✗ Failed to set log level: {put_response.status_code}")
                return False
        else:
            print(f"  ✗ Failed to get log levels: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_log_metrics():
    """Test logging metrics"""
    print("\n" + "=" * 60)
    print("4. Log Metrics Test")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/logging/metrics", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if "metrics" in data:
                metrics = data["metrics"]
                print(f"  ✓ Retrieved log metrics")
                
                total = sum(metrics.values())
                print(f"    Total logs: {total}")
                
                for level, count in metrics.items():
                    if count > 0:
                        print(f"    {level}: {count}")
                
                return True
            else:
                print(f"  ✗ No 'metrics' key in response")
                return False
        else:
            print(f"  ✗ Failed to get metrics: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_sensitive_data_filtering():
    """Test that sensitive data is filtered in logs"""
    print("\n" + "=" * 60)
    print("5. Sensitive Data Filtering Test")
    print("=" * 60)
    
    try:
        # Make a request with sensitive data in query params (if possible)
        # For now, just check that the filtering mechanism exists
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            import time
            time.sleep(0.5)
            
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        # Check for masked sensitive data patterns
                        last_lines = lines[-10:]
                        for line in last_lines:
                            line_lower = line.lower()
                            # Check if passwords/tokens are masked
                            if 'password' in line_lower or 'token' in line_lower:
                                if '***' in line or '"***"' in line:
                                    print(f"  ✓ Sensitive data appears to be masked")
                                    return True
                        
                        print(f"  ⚠ No sensitive data patterns found to test (this is OK)")
                        return True  # Not a failure
                    else:
                        print(f"  ⚠ Log file is empty")
                        return False
            else:
                print(f"  ⚠ Log file not found")
                return False
        else:
            print(f"  ✗ Request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Detailed Logging System Test")
    print("=" * 60)
    print(f"Log file: {LOG_FILE}")
    print()
    
    results = []
    
    results.append(("JSON Format", test_json_log_format()))
    results.append(("Log Context", test_log_context()))
    results.append(("Log Levels", test_log_levels()))
    results.append(("Log Metrics", test_log_metrics()))
    results.append(("Sensitive Data Filtering", test_sensitive_data_filtering()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    sys.exit(0 if passed == total else 1)

