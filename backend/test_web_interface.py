"""Test web interface"""
import sys
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

BASE_URL = "http://localhost:8000"

print("Testing Web Interface...\n")

# Test main page
print("1. Testing GET /")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        if "<!DOCTYPE html>" in response.text:
            print("   ✓ HTML page returned")
        if "AARD Chat" in response.text:
            print("   ✓ Page title found")
        if "htmx.org" in response.text:
            print("   ✓ HTMX library included")
    else:
        print(f"   ✗ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n2. Testing chat form submission (simulated)")
print("   The web interface should be accessible at http://localhost:8000/")
print("   Open in browser to test chat functionality")

print("\n✓ Web interface test complete!")

