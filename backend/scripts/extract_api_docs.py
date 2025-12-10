"""
Script to extract API endpoints documentation from route files
"""
import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Any

def extract_endpoints_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Extract endpoint information from a route file"""
    endpoints = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file
    try:
        tree = ast.parse(content)
    except SyntaxError:
        print(f"Warning: Could not parse {file_path}")
        return endpoints
    
    # Find router decorators and function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for router decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            method = decorator.func.attr.upper()
                            
                            # Get path from decorator
                            path = "/"
                            if decorator.args:
                                if isinstance(decorator.args[0], ast.Constant):
                                    path = decorator.args[0].value
                                elif isinstance(decorator.args[0], ast.Str):
                                    path = decorator.args[0].s
                            
                            # Get docstring
                            docstring = ast.get_docstring(node) or ""
                            
                            # Get function name
                            func_name = node.name
                            
                            endpoints.append({
                                'method': method,
                                'path': path,
                                'name': func_name,
                                'docstring': docstring,
                                'file': os.path.basename(file_path)
                            })
    
    return endpoints

def get_router_prefix(file_path: str) -> str:
    """Extract router prefix from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for router = APIRouter(prefix=...)
    match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    
    return ""

def generate_endpoint_doc(endpoint: Dict[str, Any], prefix: str) -> str:
    """Generate markdown documentation for an endpoint"""
    full_path = prefix + endpoint['path']
    
    doc = f"## {endpoint['method']} {full_path}\n\n"
    
    if endpoint['docstring']:
        doc += f"{endpoint['docstring']}\n\n"
    else:
        doc += f"### Описание\n\n{endpoint['name']}\n\n"
    
    return doc

def main():
    """Main function to extract all endpoints"""
    routes_dir = Path(__file__).parent.parent / "app" / "api" / "routes"
    
    all_endpoints = {}
    
    for route_file in routes_dir.glob("*.py"):
        if route_file.name.startswith("_") or route_file.name == "__init__.py":
            continue
        
        if route_file.name.endswith("_pages.py"):
            continue  # Skip page routes
        
        print(f"Processing {route_file.name}...")
        prefix = get_router_prefix(str(route_file))
        endpoints = extract_endpoints_from_file(str(route_file))
        
        # Group by file
        file_key = route_file.stem.replace("_pages", "")
        if file_key not in all_endpoints:
            all_endpoints[file_key] = {
                'prefix': prefix,
                'endpoints': []
            }
        
        for endpoint in endpoints:
            endpoint['full_path'] = prefix + endpoint['path']
            all_endpoints[file_key]['endpoints'].append(endpoint)
    
    # Print summary
    print("\n=== Summary ===")
    for file_key, data in sorted(all_endpoints.items()):
        print(f"{file_key}: {len(data['endpoints'])} endpoints")
        for ep in data['endpoints']:
            print(f"  {ep['method']} {ep['full_path']}")
    
    return all_endpoints

if __name__ == "__main__":
    main()

