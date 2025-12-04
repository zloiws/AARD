"""
Service for building plan tree structure from steps
"""
from typing import Dict, Any, List, Optional
from uuid import UUID


class PlanTreeService:
    """Service for building hierarchical tree structure from plan steps"""
    
    @staticmethod
    def build_tree(
        steps: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Build hierarchical tree structure from plan steps based on dependencies
        
        Args:
            steps: List of plan steps (each with step_id, dependencies, etc.)
            include_metadata: Whether to include full step metadata in tree nodes
            
        Returns:
            Dictionary with tree structure:
            {
                "nodes": [...],  # All nodes with children arrays
                "root_nodes": [...],  # Top-level nodes (no dependencies)
                "total_steps": int,
                "total_levels": int
            }
        """
        if not steps:
            return {
                "nodes": [],
                "root_nodes": [],
                "total_steps": 0,
                "total_levels": 0
            }
        
        # Parse steps if they are JSON strings
        if isinstance(steps, str):
            import json
            steps = json.loads(steps)
        
        # Create step index by step_id
        step_index: Dict[str, Dict[str, Any]] = {}
        for step in steps:
            step_id = step.get("step_id", "")
            if step_id:
                step_index[step_id] = step
        
        # Build tree nodes
        nodes = []
        root_nodes = []
        
        # Track which nodes have been processed
        processed = set()
        
        # First pass: create all nodes
        node_map: Dict[str, Dict[str, Any]] = {}
        for step in steps:
            step_id = step.get("step_id", "")
            if not step_id:
                continue
            
            dependencies = step.get("dependencies", [])
            if not isinstance(dependencies, list):
                dependencies = []
            
            node_data = {
                "step_id": step_id,
                "description": step.get("description", ""),
                "type": step.get("type", "action"),
                "children": [],
                "level": 0,  # Will be calculated later
                "has_children": False
            }
            
            if include_metadata:
                node_data.update({
                    "inputs": step.get("inputs", {}),
                    "expected_outputs": step.get("expected_outputs", {}),
                    "timeout": step.get("timeout"),
                    "retry_policy": step.get("retry_policy", {}),
                    "approval_required": step.get("approval_required", False),
                    "risk_level": step.get("risk_level", "low"),
                    "function_call": step.get("function_call"),
                    "dependencies": dependencies
                })
            
            node_map[step_id] = node_data
        
        # Second pass: build parent-child relationships and find root nodes
        for step_id, node in node_map.items():
            # Get step data to access dependencies
            step = step_index.get(step_id, {})
            dependencies = step.get("dependencies", [])
            if not isinstance(dependencies, list):
                dependencies = []
            
            # Find parent nodes (steps that this step depends on)
            parent_added = False
            for dep_id in dependencies:
                if dep_id in node_map:
                    parent_node = node_map[dep_id]
                    parent_node["children"].append(node)
                    parent_node["has_children"] = True
                    parent_added = True
            
            # If no dependencies, this is a root node
            if not dependencies or not any(dep_id in node_map for dep_id in dependencies):
                root_nodes.append(node)
        
        # Third pass: calculate levels (distance from root)
        def calculate_level(node: Dict[str, Any], level: int = 0):
            """Recursively calculate level for node and children"""
            node["level"] = max(node.get("level", 0), level)
            for child in node.get("children", []):
                calculate_level(child, level + 1)
        
        for root_node in root_nodes:
            calculate_level(root_node, 0)
        
        # Collect all nodes in depth-first order
        def collect_nodes(node: Dict[str, Any], collected: List[Dict[str, Any]]):
            """Recursively collect all nodes"""
            if node["step_id"] not in processed:
                collected.append(node)
                processed.add(node["step_id"])
            for child in node.get("children", []):
                collect_nodes(child, collected)
        
        for root_node in root_nodes:
            collect_nodes(root_node, nodes)
        
        # Calculate total levels
        total_levels = max((node.get("level", 0) for node in nodes), default=0) + 1
        
        return {
            "nodes": nodes,
            "root_nodes": root_nodes,
            "total_steps": len(steps),
            "total_levels": total_levels,
            "has_hierarchy": total_levels > 1
        }
    
    @staticmethod
    def build_flat_tree(
        steps: List[Dict[str, Any]],
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build flat tree structure with indentation levels
        
        Args:
            steps: List of plan steps
            include_metadata: Whether to include full step metadata
            
        Returns:
            Flat list of nodes with level information
        """
        tree = PlanTreeService.build_tree(steps, include_metadata)
        
        flat_list = []
        
        def flatten_node(node: Dict[str, Any], level: int = 0):
            """Recursively flatten tree nodes"""
            node_copy = {
                "step_id": node["step_id"],
                "description": node["description"],
                "type": node["type"],
                "level": level,
                "has_children": node.get("has_children", False)
            }
            
            if include_metadata:
                node_copy.update({
                    key: value for key, value in node.items()
                    if key not in ["children", "level"]
                })
            
            flat_list.append(node_copy)
            
            for child in node.get("children", []):
                flatten_node(child, level + 1)
        
        for root_node in tree["root_nodes"]:
            flatten_node(root_node, 0)
        
        return flat_list
