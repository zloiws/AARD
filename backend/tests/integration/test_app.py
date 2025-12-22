"""Test application endpoints"""
import sys
import time
from pathlib import Path

# Setup path and env
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

import requests

BASE_URL = "http://localhost:8000"

print("Testing AARD API endpoints...\n")

# Test root endpoint
print("1. Testing GET /")
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print("   ✓ Root endpoint OK\n")
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed - is the server running?\n")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

# Test health endpoint
print("2. Testing GET /health")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print("   ✓ Health endpoint OK\n")
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed - is the server running?\n")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

# Test docs endpoint
print("3. Testing GET /docs")
try:
    response = requests.get(f"{BASE_URL}/docs", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ API docs available at http://localhost:8000/docs\n")
    else:
        print(f"   ⚠ Unexpected status: {response.status_code}\n")
except requests.exceptions.ConnectionError:
    print("   ✗ Connection failed\n")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

print("Testing complete!")

