"""
Agent Team Coordination Service
Handles coordination of agent teams through A2A protocol
"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.a2a_protocol import A2AMessage, A2AMessageType, AgentIdentity
from app.core.logging_config import LoggingConfig
from app.models.agent import Agent, AgentStatus
from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus
from app.services.a2a_router import A2ARouter
from app.services.agent_registry import AgentRegistry
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class AgentTeamCoordination:
    """Service for coordinating agent teams through A2A protocol"""
    
    def __init__(self, db: Session):
        """
        Initialize Agent Team Coordination Service
        
        Args:
            db: Database session
        """
        self.db = db
        self.a2a_router = A2ARouter(db)
        self.registry = AgentRegistry(db)
    
    async def distribute_task_to_team(
        self,
        team_id: UUID,
        task_description: str,
        task_context: Optional[Dict[str, Any]] = None,
        assign_to_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Distribute task to team agents based on coordination strategy
        
        Args:
            team_id: Team ID
            task_description: Task description
            task_context: Additional task context
            assign_to_role: Optional role to assign task to (if None, uses strategy)
            
        Returns:
            Dictionary with distribution results
        """
        from app.services.agent_team_service import AgentTeamService
        team_service = AgentTeamService(self.db)
        
        team = team_service.get_team(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
        
        if team.status != TeamStatus.ACTIVE.value:
            raise ValueError(f"Team {team_id} is not active (status: {team.status})")
        
        # Get team agents
        agents = list(team.agents.all())
        if not agents:
            raise ValueError(f"Team {team_id} has no agents")
        
        # Determine which agents to use
        target_agents = []
        if assign_to_role:
            target_agents = team_service.get_agents_by_role(team_id, assign_to_role)
            if not target_agents:
                raise ValueError(f"No agents with role '{assign_to_role}' in team {team_id}")
        else:
            target_agents = self._select_agents_by_strategy(team, agents, task_description)
        
        if not target_agents:
            raise ValueError(f"No suitable agents found for task in team {team_id}")
        
        # Create system identity for team coordination
        system_identity = AgentIdentity(
            agent_id=uuid4(),  # System/team coordinator ID
            version=1,
            capabilities=["team_coordination"]
        )
        
        # Distribute based on coordination strategy
        results = await self._distribute_by_strategy(
            team,
            target_agents,
            system_identity,
            task_description,
            task_context
        )
        
        logger.info(
            f"Distributed task to {len(target_agents)} agents in team {team_id}",
            extra={"team_id": str(team_id), "strategy": team.coordination_strategy}
        )
        
        return results
    
    def _select_agents_by_strategy(
        self,
        team: AgentTeam,
        agents: List[Agent],
        task_description: str
    ) -> List[Agent]:
        """Select agents based on coordination strategy"""
        strategy = team.coordination_strategy
        
        if strategy == CoordinationStrategy.HIERARCHICAL.value:
            from app.services.agent_team_service import AgentTeamService
            team_service = AgentTeamService(self.db)
            lead = team_service.get_team_lead(team.id)
            if lead and lead in agents:
                return [lead]
            return [agents[0]] if agents else []
        
        elif strategy == CoordinationStrategy.SEQUENTIAL.value:
            return [agents[0]] if agents else []
        
        elif strategy == CoordinationStrategy.PARALLEL.value:
            return [a for a in agents if a.status == AgentStatus.ACTIVE.value]
        
        elif strategy == CoordinationStrategy.COLLABORATIVE.value:
            return [a for a in agents if a.status == AgentStatus.ACTIVE.value]
        
        elif strategy == CoordinationStrategy.PIPELINE.value:
            return [a for a in agents if a.status == AgentStatus.ACTIVE.value]
        
        return [a for a in agents if a.status == AgentStatus.ACTIVE.value]
    
    async def _distribute_by_strategy(
        self,
        team: AgentTeam,
        agents: List[Agent],
        sender_identity: AgentIdentity,
        task_description: str,
        task_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Distribute task to agents based on coordination strategy"""
        strategy = team.coordination_strategy
        results = {
            "distributed_to": [str(a.id) for a in agents],
            "strategy_used": strategy,
            "messages_sent": 0,
            "responses": []
        }
        
        if strategy == CoordinationStrategy.SEQUENTIAL.value:
            # Sequential: send to first agent, wait for response, then next
            previous_result = None
            for i, agent in enumerate(agents):
                agent_identity = self.registry.get_agent_identity(agent.id)
                if not agent_identity:
                    continue
                
                message = A2AMessage(
                    sender=sender_identity,
                    recipient=agent.id,
                    type=A2AMessageType.REQUEST,
                    payload={
                        "action": "execute_task",
                        "task": task_description,
                        "context": {
                            **(task_context or {}),
                            "step_number": i + 1,
                            "total_steps": len(agents),
                            "previous_result": previous_result
                        },
                        "team_id": str(team.id),
                        "team_name": team.name
                    },
                    context={
                        "team_id": str(team.id),
                        "task_type": "team_task"
                    }
                )
                
                response = await self.a2a_router.send_message(message, wait_for_response=True)
                results["messages_sent"] += 1
                
                if response:
                    response_payload = response.payload if hasattr(response, 'payload') else {}
                    results["responses"].append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "response": response_payload
                    })
                    previous_result = response_payload
        
        elif strategy == CoordinationStrategy.PARALLEL.value:
            # Parallel: send to all agents simultaneously
            import asyncio
            
            tasks = []
            for agent in agents:
                agent_identity = self.registry.get_agent_identity(agent.id)
                if not agent_identity:
                    continue
                
                message = A2AMessage(
                    sender=sender_identity,
                    recipient=agent.id,
                    type=A2AMessageType.REQUEST,
                    payload={
                        "action": "execute_task",
                        "task": task_description,
                        "context": task_context or {},
                        "team_id": str(team.id),
                        "team_name": team.name
                    },
                    context={"team_id": str(team.id)}
                )
                tasks.append(self._send_to_agent(agent, message))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for agent, response in zip(agents, responses):
                results["messages_sent"] += 1
                if isinstance(response, Exception):
                    results["responses"].append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "error": str(response)
                    })
                elif response:
                    response_payload = response.payload if hasattr(response, 'payload') else {}
                    results["responses"].append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "response": response_payload
                    })
        
        elif strategy == CoordinationStrategy.HIERARCHICAL.value:
            # Hierarchical: send to lead, lead coordinates others
            from app.services.agent_team_service import AgentTeamService
            team_service = AgentTeamService(self.db)
            lead = team_service.get_team_lead(team.id)
            if not lead:
                lead = agents[0] if agents else None
            
            if lead:
                lead_identity = self.registry.get_agent_identity(lead.id)
                if lead_identity:
                    message = A2AMessage(
                        sender=sender_identity,
                        recipient=lead.id,
                        type=A2AMessageType.REQUEST,
                        payload={
                            "action": "coordinate_task",
                            "task": task_description,
                            "context": task_context or {},
                            "team_agents": [
                                {"id": str(a.id), "name": a.name}
                                for a in agents if a.id != lead.id
                            ],
                            "team_id": str(team.id),
                            "team_name": team.name
                        },
                        context={"team_id": str(team.id)}
                    )
                    
                    response = await self.a2a_router.send_message(message, wait_for_response=True)
                    results["messages_sent"] += 1
                    
                    if response:
                        response_payload = response.payload if hasattr(response, 'payload') else {}
                        results["responses"].append({
                            "agent_id": str(lead.id),
                            "agent_name": lead.name,
                            "response": response_payload
                        })
        
        elif strategy == CoordinationStrategy.COLLABORATIVE.value:
            # Collaborative: send to all, collect responses, share results
            import asyncio

            # First round: send to all agents
            tasks = []
            for agent in agents:
                agent_identity = self.registry.get_agent_identity(agent.id)
                if not agent_identity:
                    continue
                
                message = A2AMessage(
                    sender=sender_identity,
                    recipient=agent.id,
                    type=A2AMessageType.REQUEST,
                    payload={
                        "action": "execute_task",
                        "task": task_description,
                        "context": task_context or {},
                        "team_id": str(team.id),
                        "team_name": team.name
                    },
                    context={"team_id": str(team.id)}
                )
                tasks.append(self._send_to_agent(agent, message))
            
            first_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            shared_results = []
            for agent, response in zip(agents, first_responses):
                results["messages_sent"] += 1
                if not isinstance(response, Exception) and response:
                    response_payload = response.payload if hasattr(response, 'payload') else {}
                    shared_results.append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "result": response_payload
                    })
            
            # Second round: share results with all agents for collaboration
            if shared_results:
                collaboration_message = A2AMessage(
                    sender=sender_identity,
                    recipient="broadcast",
                    type=A2AMessageType.NOTIFICATION,
                    payload={
                        "type": "collaboration_update",
                        "results": shared_results,
                        "task": task_description
                    },
                    context={"team_id": str(team.id)}
                )
                
                await self.a2a_router.send_message(collaboration_message, wait_for_response=False)
                results["messages_sent"] += len(agents)
            
            results["responses"] = shared_results
        
        elif strategy == CoordinationStrategy.PIPELINE.value:
            # Pipeline: send to agents in order, each receives previous result
            previous_result = None
            for i, agent in enumerate(agents):
                agent_identity = self.registry.get_agent_identity(agent.id)
                if not agent_identity:
                    continue
                
                message = A2AMessage(
                    sender=sender_identity,
                    recipient=agent.id,
                    type=A2AMessageType.REQUEST,
                    payload={
                        "action": "execute_task",
                        "task": task_description,
                        "context": {
                            **(task_context or {}),
                            "pipeline_stage": i + 1,
                            "total_stages": len(agents),
                            "previous_result": previous_result
                        },
                        "team_id": str(team.id),
                        "team_name": team.name
                    },
                    context={"team_id": str(team.id)}
                )
                
                response = await self.a2a_router.send_message(message, wait_for_response=True)
                results["messages_sent"] += 1
                
                if response:
                    response_payload = response.payload if hasattr(response, 'payload') else {}
                    previous_result = response_payload
                    results["responses"].append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "stage": i + 1,
                        "response": response_payload
                    })
        
        return results
    
    async def _send_to_agent(self, agent: Agent, message: A2AMessage) -> Optional[A2AMessage]:
        """Helper method to send message to agent"""
        return await self.a2a_router.send_message(message, wait_for_response=True)
    
    async def share_result_between_agents(
        self,
        team_id: UUID,
        from_agent_id: UUID,
        result: Dict[str, Any],
        target_agents: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Share result from one agent to others in team
        
        Args:
            team_id: Team ID
            from_agent_id: Agent who produced the result
            result: Result to share
            target_agents: Optional list of agent IDs to share with (if None, shares with all)
            
        Returns:
            Sharing results
        """
        from app.services.agent_team_service import AgentTeamService
        team_service = AgentTeamService(self.db)
        
        team = team_service.get_team(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
        
        # Get sender identity
        sender_identity = self.registry.get_agent_identity(from_agent_id)
        if not sender_identity:
            raise ValueError(f"Agent {from_agent_id} not found or not active")
        
        # Get target agents
        if target_agents:
            agents = self.db.query(Agent).filter(Agent.id.in_(target_agents)).all()
        else:
            agents = list(team.agents.all())
        
        # Remove sender from recipients
        agents = [a for a in agents if a.id != from_agent_id]
        
        if not agents:
            return {"shared_with": [], "messages_sent": 0}
        
        # Create notification message
        message = A2AMessage(
            sender=sender_identity,
            recipient="broadcast" if len(agents) > 1 else agents[0].id,
            type=A2AMessageType.NOTIFICATION,
            payload={
                "type": "result_share",
                "result": result,
                "from_agent_id": str(from_agent_id)
            },
            context={"team_id": str(team_id)}
        )
        
        # Send message
        if len(agents) > 1:
            await self.a2a_router.send_message(message, wait_for_response=False)
            messages_sent = len(agents)
        else:
            message.recipient = agents[0].id
            await self.a2a_router.send_message(message, wait_for_response=False)
            messages_sent = 1
        
        logger.info(
            f"Shared result from agent {from_agent_id} to {len(agents)} agents in team {team_id}"
        )
        
        return {
            "shared_with": [str(a.id) for a in agents],
            "messages_sent": messages_sent
        }

