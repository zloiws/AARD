"""
Tests for plan tree service
"""
import pytest
from app.services.plan_tree_service import PlanTreeService


class TestPlanTreeService:
    """Tests for plan tree building service"""
    
    def test_empty_steps(self):
        """Test building tree from empty steps"""
        tree = PlanTreeService.build_tree([])
        
        assert tree["nodes"] == []
        assert tree["root_nodes"] == []
        assert tree["total_steps"] == 0
        assert tree["total_levels"] == 0
        assert tree["has_hierarchy"] is False
    
    def test_single_step(self):
        """Test building tree from single step"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_steps"] == 1
        assert len(tree["root_nodes"]) == 1
        assert tree["root_nodes"][0]["step_id"] == "step_1"
        assert len(tree["root_nodes"][0]["children"]) == 0
        assert tree["total_levels"] == 1
    
    def test_linear_steps(self):
        """Test building tree from linear steps (chain)"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Third step",
                "type": "action",
                "dependencies": ["step_2"]
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_steps"] == 3
        assert len(tree["root_nodes"]) == 1
        assert tree["root_nodes"][0]["step_id"] == "step_1"
        assert tree["total_levels"] == 3
        
        # Check hierarchy
        root = tree["root_nodes"][0]
        assert len(root["children"]) == 1
        assert root["children"][0]["step_id"] == "step_2"
        assert len(root["children"][0]["children"]) == 1
        assert root["children"][0]["children"][0]["step_id"] == "step_3"
    
    def test_branched_steps(self):
        """Test building tree from branched steps"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Third step",
                "type": "action",
                "dependencies": ["step_1"]
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_steps"] == 3
        assert len(tree["root_nodes"]) == 1
        root = tree["root_nodes"][0]
        assert root["step_id"] == "step_1"
        assert len(root["children"]) == 2
        assert tree["total_levels"] == 2
        
        # Check both branches
        child_ids = [child["step_id"] for child in root["children"]]
        assert "step_2" in child_ids
        assert "step_3" in child_ids
    
    def test_multiple_roots(self):
        """Test building tree with multiple root nodes"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_3",
                "description": "Third step",
                "type": "action",
                "dependencies": ["step_1"]
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_steps"] == 3
        assert len(tree["root_nodes"]) == 2
        root_ids = [root["step_id"] for root in tree["root_nodes"]]
        assert "step_1" in root_ids
        assert "step_2" in root_ids
    
    def test_complex_hierarchy(self):
        """Test building tree from complex hierarchy"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Third step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_4",
                "description": "Fourth step",
                "type": "action",
                "dependencies": ["step_2", "step_3"]
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_steps"] == 4
        assert len(tree["root_nodes"]) == 1
        assert tree["total_levels"] == 3
        
        # Check structure
        root = tree["root_nodes"][0]
        assert root["step_id"] == "step_1"
        assert len(root["children"]) == 2
        
        # Find step_4 (should be child of both step_2 and step_3)
        step_2 = next(child for child in root["children"] if child["step_id"] == "step_2")
        step_3 = next(child for child in root["children"] if child["step_id"] == "step_3")
        
        # step_4 should be in children of step_2 or step_3
        all_children = step_2["children"] + step_3["children"]
        step_4_ids = [child["step_id"] for child in all_children]
        assert "step_4" in step_4_ids
    
    def test_include_metadata(self):
        """Test building tree with metadata included"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": [],
                "timeout": 30,
                "risk_level": "low"
            }
        ]
        
        tree = PlanTreeService.build_tree(steps, include_metadata=True)
        
        root = tree["root_nodes"][0]
        assert "timeout" in root
        assert "risk_level" in root
        assert root["timeout"] == 30
        assert root["risk_level"] == "low"
    
    def test_exclude_metadata(self):
        """Test building tree without metadata"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": [],
                "timeout": 30,
                "risk_level": "low"
            }
        ]
        
        tree = PlanTreeService.build_tree(steps, include_metadata=False)
        
        root = tree["root_nodes"][0]
        assert "timeout" not in root or root.get("timeout") is None
        assert "risk_level" not in root or root.get("risk_level") is None
    
    def test_build_flat_tree(self):
        """Test building flat tree structure"""
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": ["step_1"]
            }
        ]
        
        flat_tree = PlanTreeService.build_flat_tree(steps)
        
        assert len(flat_tree) == 2
        assert flat_tree[0]["step_id"] == "step_1"
        assert flat_tree[0]["level"] == 0
        assert flat_tree[1]["step_id"] == "step_2"
        assert flat_tree[1]["level"] == 1
    
    def test_level_calculation(self):
        """Test that levels are calculated correctly"""
        steps = [
            {
                "step_id": "step_1",
                "description": "Root",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Level 1",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Level 2",
                "type": "action",
                "dependencies": ["step_2"]
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        
        assert tree["total_levels"] == 3
        
        root = tree["root_nodes"][0]
        assert root["level"] == 0
        assert root["children"][0]["level"] == 1
        assert root["children"][0]["children"][0]["level"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
