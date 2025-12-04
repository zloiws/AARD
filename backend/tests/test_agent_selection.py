"""
Unit tests for agent selection functionality
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from app.services.agent_service import AgentService
from app.models.agent import Agent, AgentStatus, AgentCapability


class TestAgentSelection:
    """Tests for agent selection in AgentService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def agent_service(self, mock_db):
        """AgentService instance"""
        return AgentService(mock_db)
    
    @pytest.fixture
    def sample_agents(self):
        """Sample agent objects"""
        agent1 = Mock(spec=Agent)
        agent1.id = uuid4()
        agent1.name = "Planning Agent"
        agent1.status = AgentStatus.ACTIVE.value
        agent1.capabilities = [AgentCapability.PLANNING.value]
        agent1.success_rate = "90%"
        agent1.total_tasks_executed = 100
        agent1.successful_tasks = 90
        agent1.average_execution_time = 120
        
        agent2 = Mock(spec=Agent)
        agent2.id = uuid4()
        agent2.name = "Code Agent"
        agent2.status = AgentStatus.ACTIVE.value
        agent2.capabilities = [
            AgentCapability.CODE_GENERATION.value,
            AgentCapability.PLANNING.value
        ]
        agent2.success_rate = "85%"
        agent2.total_tasks_executed = 50
        agent2.successful_tasks = 42
        agent2.average_execution_time = 200
        
        return [agent1, agent2]
    
    def test_select_agent_for_task_no_capabilities(self, agent_service, sample_agents, mock_db):
        """Test selecting agent when no specific capabilities required"""
        # Mock query to return active agents
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = sample_agents
        mock_db.query.return_value = mock_query
        
        selected = agent_service.select_agent_for_task(required_capabilities=None)
        
        assert selected is not None
        assert selected in sample_agents
    
    def test_select_agent_for_task_with_capabilities(self, agent_service, sample_agents, mock_db):
        """Test selecting agent with specific capabilities"""
        from sqlalchemy import or_
        
        # Mock query with capability filtering
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_agents[1]]  # Code Agent has both capabilities
        
        # Mock capability filter
        with patch('app.services.agent_service.or_', return_value=mock_filter):
            mock_db.query.return_value = mock_query
            
            selected = agent_service.select_agent_for_task(
                required_capabilities=[
                    AgentCapability.CODE_GENERATION.value,
                    AgentCapability.PLANNING.value
                ]
            )
            
            assert selected is not None
            assert AgentCapability.CODE_GENERATION.value in selected.capabilities
    
    def test_select_agent_preferred_agent(self, agent_service, sample_agents, mock_db):
        """Test selecting preferred agent"""
        preferred_id = sample_agents[0].id
        
        # Mock get_agent to return preferred agent
        mock_db.query.return_value.filter.return_value.first.return_value = sample_agents[0]
        
        with patch.object(agent_service, 'get_agent', return_value=sample_agents[0]):
            selected = agent_service.select_agent_for_task(
                required_capabilities=[AgentCapability.PLANNING.value],
                preferred_agent_id=preferred_id
            )
            
            assert selected is not None
            assert selected.id == preferred_id
    
    def test_select_agent_no_matching_agents(self, agent_service, mock_db):
        """Test selecting agent when no matching agents exist"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        selected = agent_service.select_agent_for_task(
            required_capabilities=["non_existent_capability"]
        )
        
        assert selected is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

