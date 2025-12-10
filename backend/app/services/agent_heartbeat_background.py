"""
Background task for agent heartbeat monitoring
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.logging_config import LoggingConfig
from app.core.database import get_db
from app.services.agent_heartbeat_service import AgentHeartbeatService
from app.models.agent import Agent, AgentStatus, AgentHealthStatus

logger = LoggingConfig.get_logger(__name__)


class AgentHeartbeatMonitor:
    """Background monitor for agent heartbeats"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # Check every 60 seconds
        self.heartbeat_timeout = 90  # 90 seconds without heartbeat = unhealthy
    
    async def start(self):
        """Start the heartbeat monitor"""
        if self.running:
            logger.warning("Heartbeat monitor is already running")
            return
        
        self.running = True
        logger.info("Starting agent heartbeat monitor...")
        
        # Run monitoring loop
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop the heartbeat monitor"""
        self.running = False
        logger.info("Stopping agent heartbeat monitor...")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_agents(self):
        """Check all active agents"""
        try:
            db = next(get_db())
            
            # Check if agents table exists
            from sqlalchemy import inspect, text
            inspector = inspect(db.bind)
            if 'agents' not in inspector.get_table_names():
                logger.debug("Agents table does not exist, skipping heartbeat check")
                db.close()
                return
            
            heartbeat_service = AgentHeartbeatService(db)
            
            # Get all active agents
            active_agents = db.query(Agent).filter(
                Agent.status == AgentStatus.ACTIVE.value
            ).all()
            
            unhealthy_count = 0
            degraded_count = 0
            
            for agent in active_agents:
                # Check if heartbeat is missing or too old
                if not agent.last_heartbeat:
                    # No heartbeat ever received
                    agent.health_status = AgentHealthStatus.UNKNOWN.value
                    unhealthy_count += 1
                else:
                    time_since_heartbeat = datetime.now(timezone.utc) - agent.last_heartbeat
                    
                    if time_since_heartbeat.total_seconds() > self.heartbeat_timeout:
                        # No heartbeat for too long
                        if agent.health_status != AgentHealthStatus.UNHEALTHY.value:
                            logger.warning(
                                f"Agent {agent.name} ({agent.id}) is unhealthy - no heartbeat for {int(time_since_heartbeat.total_seconds())} seconds"
                            )
                        agent.health_status = AgentHealthStatus.UNHEALTHY.value
                        unhealthy_count += 1
                    elif time_since_heartbeat.total_seconds() > 60:
                        # Heartbeat delayed but not critical
                        agent.health_status = AgentHealthStatus.DEGRADED.value
                        degraded_count += 1
                    else:
                        # Heartbeat is recent
                        if agent.health_status != AgentHealthStatus.HEALTHY.value:
                            agent.health_status = AgentHealthStatus.HEALTHY.value
                
                db.commit()
            
            if unhealthy_count > 0 or degraded_count > 0:
                logger.info(
                    f"Heartbeat check complete: {len(active_agents)} active agents, "
                    f"{unhealthy_count} unhealthy, {degraded_count} degraded"
                )
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error checking agent heartbeats: {e}", exc_info=True)


# Global monitor instance
_heartbeat_monitor: Optional[AgentHeartbeatMonitor] = None


def get_heartbeat_monitor() -> AgentHeartbeatMonitor:
    """Get or create heartbeat monitor instance"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = AgentHeartbeatMonitor()
    return _heartbeat_monitor

