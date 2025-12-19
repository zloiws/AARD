"""
Artifact generator service for creating agents and tools
"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.ollama_client import OllamaClient, TaskType
from app.models.approval import ApprovalRequestType
from app.models.artifact import Artifact, ArtifactStatus, ArtifactType
from app.services.agent_approval_agent import AgentApprovalAgent
from app.services.approval_service import ApprovalService
from app.services.artifact_version_service import ArtifactVersionService
from sqlalchemy.orm import Session


class ArtifactGenerator:
    """Service for generating artifacts (agents and tools)"""
    
    def __init__(self, db: Session, ollama_client: OllamaClient):
        self.db = db
        self.ollama_client = ollama_client
        self.approval_service = ApprovalService(db)
        self.agent_approval_agent = AgentApprovalAgent(db)  # Validate-Then-Build механизм
        self.version_service = ArtifactVersionService(db)  # Version control
    
    async def generate_artifact(
        self,
        description: str,
        artifact_type: ArtifactType,
        context: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Artifact:
        """
        Generate an artifact (agent or tool) based on description
        
        Args:
            description: Description of what artifact should do
            artifact_type: Type of artifact (agent or tool)
            context: Additional context (similar artifacts, requirements, etc.)
            created_by: User who requested creation
            
        Returns:
            Created artifact in WAITING_APPROVAL status
        """
        
        # 0. Validate-Then-Build: Проверить необходимость создания агента через AAA
        if artifact_type == ArtifactType.AGENT:
            validation_result = await self.agent_approval_agent.validate_agent_creation(
                proposed_agent={
                    "name": description.split()[0] if description else "NewAgent",  # Временное имя
                    "description": description,
                    "capabilities": context.get("capabilities", []) if context else [],
                    "tools": context.get("tools", []) if context else [],
                    "expected_benefit": context.get("expected_benefit", "") if context else "",
                    "risks": context.get("risks", []) if context else []
                },
                task_description=context.get("task_description") if context else None,
                context=context
            )
            
            # Если не нужен или требуется утверждение, вернуть информацию
            if not validation_result.get("is_needed"):
                raise ValueError(
                    f"Agent creation not needed. {validation_result.get('recommendation', 'Use existing agents.')}"
                )
            
            # Если требуется утверждение, создать артефакт в статусе waiting_approval
            if validation_result.get("requires_approval"):
                # Продолжить создание, но артефакт будет в статусе waiting_approval
                pass
        
        # 1. Analyze requirements
        requirements = await self._analyze_requirements(description, artifact_type, context)
        
        # 2. Search for similar artifacts in memory (if memory system is available)
        similar_artifacts = await self._find_similar_artifacts(description, artifact_type)
        
        # 3. Generate code or prompt
        if artifact_type == ArtifactType.TOOL:
            code = await self._generate_tool_code(requirements, similar_artifacts, context)
            prompt = None
        else:  # AGENT
            prompt = await self._generate_agent_prompt(requirements, similar_artifacts, context)
            code = None
        
        # 4. Validate and test (basic validation)
        validation = await self._validate_artifact(code, prompt, artifact_type)
        
        # 5. Assess security
        security = await self._assess_security(code, prompt, artifact_type)
        
        # 6. Create artifact
        artifact = Artifact(
            type=artifact_type.value.lower(),  # Use lowercase to match DB constraint
            name=requirements.get("name", f"{artifact_type.value}_{uuid4().hex[:8]}"),
            description=requirements.get("description", description),
            code=code,
            prompt=prompt,
            test_results=validation,
            security_rating=security.get("rating", 0.5),
            status="waiting_approval",  # Use lowercase to match DB constraint
            created_by=created_by
        )
        
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        
        # 7. Create initial version snapshot
        changelog = f"Initial version of {artifact.name}. {description[:200]}"
        metrics = {
            "success_rate": 0.0,  # Will be updated after testing
            "avg_execution_time": 0.0,
            "error_rate": 0.0
        }
        self.version_service.create_version(
            artifact=artifact,
            changelog=changelog,
            metrics=metrics,
            created_by=created_by or "system"
        )
        
        # 8. Create approval request
        approval = self.approval_service.create_approval_request(
            request_type=ApprovalRequestType.NEW_ARTIFACT,  # Will be converted to lowercase in service
            request_data={
                "artifact_id": str(artifact.id),
                "type": artifact_type.value,
                "name": artifact.name,
                "description": artifact.description,
                "code": code,
                "prompt": prompt,
                "requirements": requirements,
                "validation": validation,
                "security": security
            },
            artifact_id=artifact.id,
            risk_assessment=security,
            recommendation=self._generate_recommendation(artifact, security)
        )
        
        return artifact
    
    async def _analyze_requirements(
        self,
        description: str,
        artifact_type: ArtifactType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze requirements using LLM"""
        
        system_prompt = f"""You are an expert at analyzing requirements for {artifact_type.value} creation.
Analyze the following description and extract:
1. Name for the {artifact_type.value}
2. Detailed description
3. Key features and capabilities
4. Input/output specifications
5. Dependencies or requirements
6. Potential risks or limitations

Return a structured analysis in JSON format."""

        user_prompt = f"""Description: {description}

Context: {context or 'No additional context'}

Provide a detailed analysis of requirements for creating this {artifact_type.value}."""

        try:
            response = await self.ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.REASONING
            )
            
            # Parse response (simplified - in production use proper JSON parsing)
            # For now, return basic structure
            # TODO: Parse JSON from response.response
            return {
                "name": self._extract_name_from_description(description),
                "description": description,
                "features": [],
                "inputs": [],
                "outputs": [],
                "dependencies": []
            }
        except Exception as e:
            # Fallback to basic analysis
            return {
                "name": self._extract_name_from_description(description),
                "description": description,
                "features": [],
                "inputs": [],
                "outputs": [],
                "dependencies": []
            }
    
    async def _find_similar_artifacts(
        self,
        description: str,
        artifact_type: ArtifactType
    ) -> List[Artifact]:
        """Find similar artifacts in database"""
        # Simple search by type and keywords in description
        # In production, use vector search with embeddings
        artifacts = self.db.query(Artifact).filter(
            Artifact.type == artifact_type.value.lower(),  # Use lowercase
            Artifact.status == "active"  # Use lowercase
        ).limit(5).all()
        
        return artifacts
    
    async def _generate_tool_code(
        self,
        requirements: Dict[str, Any],
        similar_artifacts: List[Artifact],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Python code for a tool"""
        
        system_prompt = """You are an expert Python developer. Generate clean, well-documented Python code for tools.
The code should:
1. Be well-structured and readable
2. Include proper error handling
3. Have type hints where appropriate
4. Include docstrings
5. Follow PEP 8 style guide
6. Be secure (no eval, exec, or dangerous operations without validation)

Return only the Python code, no explanations."""

        similar_examples = "\n\n".join([
            f"Example {i+1}:\n{art.code}" 
            for i, art in enumerate(similar_artifacts[:3]) 
            if art.code
        ])
        
        user_prompt = f"""Generate Python code for a tool with the following requirements:

{requirements.get('description', '')}

Features needed:
{', '.join(requirements.get('features', []))}

Inputs: {', '.join(requirements.get('inputs', []))}
Outputs: {', '.join(requirements.get('outputs', []))}

{f'Similar examples:\n{similar_examples}' if similar_examples else ''}

Generate the complete Python code for this tool."""

        try:
            response = await self.ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.CODE_GENERATION
            )
            return response.response
        except Exception as e:
            # Fallback to template
            return self._generate_template_code(requirements)
    
    async def _generate_agent_prompt(
        self,
        requirements: Dict[str, Any],
        similar_artifacts: List[Artifact],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate prompt for an agent"""
        
        system_prompt = """You are an expert at creating prompts for AI agents.
Create a detailed, structured prompt that defines:
1. Agent's role and purpose
2. Capabilities and limitations
3. Instructions for behavior
4. How to use tools
5. Error handling
6. Communication style

The prompt should be clear, specific, and actionable."""

        similar_examples = "\n\n".join([
            f"Example {i+1}:\n{art.prompt}" 
            for i, art in enumerate(similar_artifacts[:3]) 
            if art.prompt
        ])
        
        user_prompt = f"""Create a prompt for an AI agent with the following requirements:

{requirements.get('description', '')}

Capabilities needed:
{', '.join(requirements.get('features', []))}

{f'Similar examples:\n{similar_examples}' if similar_examples else ''}

Generate the complete prompt for this agent."""

        try:
            response = await self.ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=TaskType.REASONING
            )
            return response.response
        except Exception as e:
            # Fallback to template
            return self._generate_template_prompt(requirements)
    
    async def _validate_artifact(
        self,
        code: Optional[str],
        prompt: Optional[str],
        artifact_type: ArtifactType
    ) -> Dict[str, Any]:
        """Basic validation of artifact"""
        
        validation = {
            "syntax_check": "pending",
            "security_check": "pending",
            "structure_check": "pending"
        }
        
        if artifact_type == ArtifactType.TOOL and code:
            # Basic syntax check (simplified)
            try:
                compile(code, '<string>', 'exec')
                validation["syntax_check"] = "passed"
            except SyntaxError as e:
                validation["syntax_check"] = f"failed: {str(e)}"
        
        return validation
    
    async def _assess_security(
        self,
        code: Optional[str],
        prompt: Optional[str],
        artifact_type: ArtifactType
    ) -> Dict[str, Any]:
        """Assess security of artifact"""
        
        security = {
            "rating": 0.5,
            "risks": [],
            "recommendations": []
        }
        
        if artifact_type == ArtifactType.TOOL and code:
            # Basic security checks
            dangerous_patterns = ['eval(', 'exec(', '__import__', 'os.system', 'subprocess']
            found_risks = []
            
            for pattern in dangerous_patterns:
                if pattern in code:
                    found_risks.append(f"Found potentially dangerous pattern: {pattern}")
            
            if found_risks:
                security["rating"] = 0.3
                security["risks"] = found_risks
                security["recommendations"].append("Review code for security vulnerabilities")
            else:
                security["rating"] = 0.7
                security["recommendations"].append("Code appears safe, but manual review recommended")
        
        return security
    
    def _generate_recommendation(
        self,
        artifact: Artifact,
        security: Dict[str, Any]
    ) -> str:
        """Generate recommendation for approval"""
        
        if security["rating"] < 0.4:
            return "⚠️ HIGH RISK: Review carefully before approval. Security concerns detected."
        elif security["rating"] < 0.7:
            return "⚠️ MEDIUM RISK: Review recommended. Some security concerns."
        else:
            return "✅ LOW RISK: Appears safe. Standard review recommended."
    
    def _extract_name_from_description(self, description: str) -> str:
        """Extract a name from description"""
        # Simple extraction - take first few words
        words = description.split()[:3]
        return "_".join(word.lower().strip(".,!?") for word in words if word)
    
    def _generate_template_code(self, requirements: Dict[str, Any]) -> str:
        """Generate template code as fallback"""
        return f'''"""
{requirements.get("description", "Tool description")}
"""
from typing import Any, Dict, List, Optional


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main execution function
    
    Args:
        input_data: Input parameters
        
    Returns:
        Result dictionary
    """
    # TODO: Implement tool logic
    return {{"status": "success", "result": None}}


if __name__ == "__main__":
    # Example usage
    result = execute({{}})
    print(result)
'''
    
    def _generate_template_prompt(self, requirements: Dict[str, Any]) -> str:
        """Generate template prompt as fallback"""
        return f"""You are an AI agent designed to: {requirements.get("description", "perform tasks")}

Your capabilities:
- {chr(10).join(f"- {feat}" for feat in requirements.get("features", ["General task execution"]))}

Instructions:
1. Understand the task at hand
2. Use available tools when needed
3. Provide clear and helpful responses
4. Handle errors gracefully
5. Ask for clarification when needed

Always prioritize safety and user satisfaction."""

