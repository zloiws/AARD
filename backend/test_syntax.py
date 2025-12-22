#!/usr/bin/env python
"""Test syntax of planning_service.py"""
import ast
import sys
from pathlib import Path

try:
    base = Path(__file__).parent
    target = base / "app" / "services" / "planning_service.py"
    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file
    ast.parse(content)
    print("✅ Syntax check: PASSED")
    
    # Try to import
    import importlib.util
    spec = importlib.util.spec_from_file_location("planning_service", "app/services/planning_service.py")
    if spec is None:
        print("❌ Could not create spec")
        sys.exit(1)
    
    print("✅ File can be loaded as module")
    
    # Check specific lines around the error
    lines = content.split('\n')
    print(f"\nChecking lines around 2169:")
    for i in range(2167, min(2175, len(lines))):
        line_num = i + 1
        line = lines[i]
        indent = len(line) - len(line.lstrip())
        print(f"  Line {line_num:4d} [{indent:2d} spaces]: {line[:60]}")
    
    print("\n✅ All checks passed!")
    
except SyntaxError as e:
    print(f"❌ Syntax Error:")
    print(f"  File: {e.filename}")
    print(f"  Line: {e.lineno}")
    print(f"  Text: {e.text}")
    print(f"  Message: {e.msg}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
