"""
Plan Template Service for extracting and managing reusable plan templates
"""
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import json
import re
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.plan_template import PlanTemplate, TemplateStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.core.ollama_client import OllamaClient, TaskType
from app.services.ollama_service import OllamaService
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PlanTemplateService:
    """
    Service for extracting and managing plan templates from successful plans.
    
    Features:
    - Extract templates from successful plans
    - Abstract specific details into patterns
    - Search templates by semantic similarity
    - Adapt templates to new tasks
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService()
        self.embedding_service = EmbeddingService(db) if hasattr(EmbeddingService, 'generate_embedding') else None
    
    def extract_template_from_plan(
        self,
        plan_id: UUID,
        template_name: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[PlanTemplate]:
        """
        Extract a template from a successful plan.
        
        Args:
            plan_id: ID of the plan to extract template from
            template_name: Optional name for the template (auto-generated if not provided)
            category: Optional category for the template
            tags: Optional tags for categorization
            
        Returns:
            PlanTemplate if extraction successful, None otherwise
        """
        try:
            # Get plan with task
            plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return None
            
            # Only extract from successful plans
            if plan.status != PlanStatus.COMPLETED.value:
                logger.warning(f"Plan {plan_id} is not completed (status: {plan.status}), skipping template extraction")
                return None
            
            task = self.db.query(Task).filter(Task.id == plan.task_id).first()
            if not task:
                logger.error(f"Task {plan.task_id} not found for plan {plan_id}")
                return None
            
            # Generate template name if not provided
            if not template_name:
                template_name = self._generate_template_name(plan, task)
            
            # Abstract plan structure
            goal_pattern = self._abstract_goal(plan.goal, task.description)
            strategy_template = self._abstract_strategy(plan.strategy)
            steps_template = self._abstract_steps(plan.steps)
            alternatives_template = self._abstract_alternatives(plan.alternatives) if plan.alternatives else None
            
            # Calculate metrics
            success_rate = 1.0  # This plan was successful
            avg_execution_time = plan.actual_duration or plan.estimated_duration
            
            # Check if similar template exists (for versioning)
            # Look for templates with same category and similar goal pattern
            similar_template = None
            if category:
                existing_templates = self.list_templates(category=category, limit=100)
                for existing in existing_templates:
                    # Check if goal patterns are similar (simple check)
                    if existing.goal_pattern and goal_pattern:
                        # If goal patterns share significant words, consider it similar
                        existing_words = set(existing.goal_pattern.lower().split())
                        new_words = set(goal_pattern.lower().split())
                        common_words = existing_words.intersection(new_words)
                        # If more than 30% words are common, consider it similar
                        if len(common_words) > 0 and len(common_words) / max(len(existing_words), len(new_words)) > 0.3:
                            similar_template = existing
                            break
            
            # Create template (new version if similar exists)
            if similar_template:
                # Create new version of existing template with unique name
                new_version = similar_template.version + 1
                # Make name unique by adding version suffix
                base_name = similar_template.name
                # Remove existing version suffix if present
                if base_name.endswith(f" v{similar_template.version}"):
                    base_name = base_name[:-len(f" v{similar_template.version}")]
                versioned_name = f"{base_name} v{new_version}"
                
                # Ensure uniqueness by adding timestamp if needed
                final_name = versioned_name
                # Use raw SQL to check existence (avoid vector type issues)
                from sqlalchemy import text
                check_sql = text("SELECT id FROM plan_templates WHERE name = :name LIMIT 1")
                existing_check = self.db.execute(check_sql, {"name": final_name}).fetchone()
                if existing_check:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    final_name = f"{versioned_name}_{timestamp}"
                
                template = PlanTemplate(
                    name=final_name,
                    description=f"Template v{new_version} extracted from plan {plan_id} for task: {task.description[:200]}",
                    category=category or self._infer_category(task.description, plan.goal),
                    tags=tags or self._infer_tags(task.description, plan.goal),
                    goal_pattern=goal_pattern,
                    strategy_template=strategy_template,
                    steps_template=steps_template,
                    alternatives_template=alternatives_template,
                    status=TemplateStatus.ACTIVE.value,
                    version=new_version,
                    success_rate=success_rate,
                    avg_execution_time=avg_execution_time,
                    usage_count=0,
                    source_plan_ids=similar_template.source_plan_ids + [plan_id] if similar_template.source_plan_ids else [plan_id],
                    source_task_descriptions=(similar_template.source_task_descriptions or []) + [task.description]
                )
                logger.info(f"Creating new version {template.version} of template {similar_template.name} as {final_name}")
            else:
                # Create new template
                template = PlanTemplate(
                    name=template_name,
                    description=f"Template extracted from plan {plan_id} for task: {task.description[:200]}",
                    category=category or self._infer_category(task.description, plan.goal),
                    tags=tags or self._infer_tags(task.description, plan.goal),
                    goal_pattern=goal_pattern,
                    strategy_template=strategy_template,
                    steps_template=steps_template,
                    alternatives_template=alternatives_template,
                    status=TemplateStatus.ACTIVE.value,
                    version=1,
                    success_rate=success_rate,
                    avg_execution_time=avg_execution_time,
                    usage_count=0,
                    source_plan_ids=[plan_id],
                    source_task_descriptions=[task.description]
                )
            
            self.db.add(template)
            self.db.flush()  # Flush to get ID without committing (avoids vector type issues)
            template_id = template.id
            
            self.db.commit()
            # Don't refresh - SQLAlchemy can't read vector type directly
            
            # Generate embedding for semantic search (async, don't wait)
            if self.embedding_service:
                try:
                    # Schedule async task (will run in background)
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._generate_template_embedding_by_id(template_id))
                    else:
                        loop.run_until_complete(self._generate_template_embedding_by_id(template_id))
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for template {template_id}: {e}")
            
            # Fetch template again to return (without embedding field)
            template = self.get_template(template_id)
            
            logger.info(f"Extracted template {template.id} from plan {plan_id}")
            return template
            
        except Exception as e:
            logger.error(f"Error extracting template from plan {plan_id}: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _generate_template_name(self, plan: Plan, task: Task) -> str:
        """Generate a template name from plan and task"""
        # Try to extract a meaningful name from task description
        description = task.description[:100]
        # Remove special characters and create a readable name
        name = re.sub(r'[^\w\s-]', '', description)
        name = re.sub(r'\s+', '_', name.strip())
        name = name[:40]  # Limit length
        
        # Add timestamp with microseconds to ensure uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        unique_id = str(uuid4())[:8]  # Add short UUID for extra uniqueness
        return f"{name}_{timestamp}_{unique_id}"
    
    def _abstract_goal(self, goal: str, task_description: str) -> str:
        """
        Abstract the goal by replacing specific details with placeholders.
        
        Example:
        "Create a REST API for user management" -> "Create a REST API for {domain} management"
        """
        # For now, use LLM to abstract the goal
        # In the future, we can use pattern matching or more sophisticated NLP
        try:
            abstracted = self._abstract_with_llm(
                text=goal,
                context=task_description,
                abstraction_type="goal"
            )
            return abstracted if abstracted else goal
        except Exception as e:
            logger.warning(f"Failed to abstract goal with LLM: {e}, using original")
            return goal
    
    def _abstract_strategy(self, strategy: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Abstract strategy by replacing specific details with placeholders"""
        if not strategy:
            return None
        
        abstracted = {}
        for key, value in strategy.items():
            if isinstance(value, str):
                # Try to abstract string values
                abstracted[key] = self._abstract_text(value)
            elif isinstance(value, (dict, list)):
                # Recursively abstract nested structures
                abstracted[key] = self._abstract_nested(value)
            else:
                abstracted[key] = value
        
        return abstracted
    
    def _abstract_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Abstract steps by replacing specific details with placeholders"""
        abstracted_steps = []
        for step in steps:
            abstracted_step = {}
            for key, value in step.items():
                if isinstance(value, str):
                    abstracted_step[key] = self._abstract_text(value)
                elif isinstance(value, (dict, list)):
                    abstracted_step[key] = self._abstract_nested(value)
                else:
                    abstracted_step[key] = value
            abstracted_steps.append(abstracted_step)
        
        return abstracted_steps
    
    def _abstract_alternatives(self, alternatives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Abstract alternatives by replacing specific details with placeholders"""
        return self._abstract_steps(alternatives)  # Same structure as steps
    
    def _abstract_text(self, text: str) -> str:
        """Abstract a text string by replacing specific details"""
        # Simple pattern-based abstraction for now
        # Replace specific values with placeholders
        
        # Replace URLs
        text = re.sub(r'https?://[^\s]+', '{url}', text)
        
        # Replace file paths
        text = re.sub(r'[a-zA-Z]:\\[^\s]+|/[^\s]+', '{file_path}', text)
        
        # Replace specific numbers (but keep step numbers)
        text = re.sub(r'\b\d{3,}\b', '{number}', text)
        
        # Replace email addresses
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '{email}', text)
        
        return text
    
    def _abstract_nested(self, value: Any) -> Any:
        """Recursively abstract nested structures"""
        if isinstance(value, dict):
            return {k: self._abstract_nested(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._abstract_nested(item) for item in value]
        elif isinstance(value, str):
            return self._abstract_text(value)
        else:
            return value
    
    def _abstract_with_llm(
        self,
        text: str,
        context: Optional[str] = None,
        abstraction_type: str = "goal"
    ) -> Optional[str]:
        """
        Use LLM to abstract text by replacing specific details with placeholders.
        
        This is a more sophisticated approach than pattern matching.
        Note: For now, we use synchronous pattern matching. LLM abstraction can be added later.
        """
        # For now, use pattern-based abstraction
        # LLM abstraction requires async handling which is complex in this context
        # TODO: Implement async LLM abstraction if needed
        return self._abstract_text(text)
    
    def _infer_category(self, task_description: str, goal: str) -> str:
        """Infer category from task description and goal"""
        text = (task_description + " " + goal).lower()
        
        # Simple keyword-based categorization
        if any(word in text for word in ["api", "rest", "endpoint", "route"]):
            return "api_development"
        elif any(word in text for word in ["database", "sql", "query", "data"]):
            return "data_processing"
        elif any(word in text for word in ["test", "testing", "unit", "integration"]):
            return "testing"
        elif any(word in text for word in ["deploy", "deployment", "docker", "kubernetes"]):
            return "deployment"
        elif any(word in text for word in ["refactor", "refactoring", "code", "clean"]):
            return "code_refactoring"
        else:
            return "general"
    
    def _infer_tags(self, task_description: str, goal: str) -> List[str]:
        """Infer tags from task description and goal"""
        text = (task_description + " " + goal).lower()
        tags = []
        
        # Extract common tags
        tag_keywords = {
            "python": ["python", "py"],
            "javascript": ["javascript", "js", "node"],
            "api": ["api", "rest", "graphql"],
            "database": ["database", "sql", "postgres", "mysql"],
            "testing": ["test", "testing", "unit", "integration"],
            "frontend": ["frontend", "react", "vue", "angular"],
            "backend": ["backend", "server", "api"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        return tags[:5]  # Limit to 5 tags
    
    async def _generate_template_embedding_by_id(self, template_id: UUID):
        """Generate embedding for template by ID (avoids SQLAlchemy vector type issues)"""
        try:
            # Get template data for embedding
            template = self.get_template(template_id)
            if not template:
                logger.warning(f"Template {template_id} not found for embedding generation")
                return
            
            # Combine template fields for embedding
            text_for_embedding = f"{template.name} {template.description or ''} {template.goal_pattern}"
            if template.category:
                text_for_embedding += f" {template.category}"
            if template.tags:
                text_for_embedding += " " + " ".join(template.tags)
            
            embedding = await self.embedding_service.generate_embedding(text_for_embedding)
            
            # Update template with embedding (using raw SQL to avoid SQLAlchemy vector type issues)
            from sqlalchemy import text
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            sql = text(f"UPDATE plan_templates SET embedding = '{embedding_str}'::vector WHERE id = CAST(:id AS uuid)")
            self.db.execute(sql, {"id": str(template_id)})
            self.db.commit()
            
            logger.debug(f"Generated embedding for template {template_id}")
            
        except Exception as e:
            logger.warning(f"Failed to generate embedding for template {template_id}: {e}")
            self.db.rollback()
    
    def find_matching_templates(
        self,
        task_description: str,
        limit: int = 5,
        min_success_rate: float = 0.7,
        use_vector_search: bool = True,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[PlanTemplate]:
        """
        Find matching templates for a given task description.
        
        Uses semantic search (vector embeddings) if available, otherwise falls back to text search.
        Results are ranked by relevance, success rate, and usage count.
        
        Args:
            task_description: Description of the task to find templates for
            limit: Maximum number of templates to return
            min_success_rate: Minimum success rate for templates
            use_vector_search: Whether to use vector search (if available)
            category: Optional category filter
            tags: Optional tags filter (templates must have at least one matching tag)
            
        Returns:
            List of matching PlanTemplate objects, sorted by relevance (best matches first)
        """
        try:
            # Build base conditions for filtering
            base_conditions = {
                "status": TemplateStatus.ACTIVE.value,
                "min_success_rate": min_success_rate,
                "category": category,
                "tags": tags
            }
            
            if use_vector_search and self.embedding_service:
                # Use vector search for semantic similarity
                templates = self._find_templates_vector_search(
                    base_conditions, task_description, limit
                )
            else:
                # Use text-based search
                templates = self._find_templates_text_search_with_filters(
                    base_conditions, task_description, limit
                )
            
            # Re-rank templates by combined score (relevance + quality metrics)
            return self._rank_templates(templates, task_description)
                
        except Exception as e:
            logger.error(f"Error finding matching templates: {e}", exc_info=True)
            return []
    
    def _find_templates_vector_search(
        self,
        base_conditions: Dict[str, Any],
        task_description: str,
        limit: int
    ) -> List[PlanTemplate]:
        """Find templates using vector search"""
        try:
            # Generate embedding for task description
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a different approach
                # For now, fall back to text search
                return self._find_templates_text_search_with_filters(
                    base_conditions, task_description, limit
                )
            else:
                embedding = loop.run_until_complete(
                    self.embedding_service.generate_embedding(task_description)
                )
            
            # Convert to PostgreSQL array format
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            # Raw SQL query for vector similarity search
            from sqlalchemy import text
            sql_query = text(f"""
                SELECT 
                    id,
                    1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM plan_templates
                WHERE embedding IS NOT NULL
                    AND status = 'active'
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT :limit
            """)
            
            result = self.db.execute(sql_query, {"limit": limit})
            rows = result.fetchall()
            
            # Get template IDs and fetch full objects
            template_ids = []
            for row in rows:
                template_id = row[0]
                if isinstance(template_id, str):
                    template_ids.append(UUID(template_id))
                elif isinstance(template_id, UUID):
                    template_ids.append(template_id)
                else:
                    template_ids.append(UUID(str(template_id)))
            
            # Fetch templates using raw SQL (to avoid vector type issues)
            if not template_ids:
                return []
            
            # Build IN clause for template IDs
            id_placeholders = ", ".join([f"CAST(:id_{i} AS uuid)" for i in range(len(template_ids))])
            id_params = {f"id_{i}": str(tid) for i, tid in enumerate(template_ids)}
            
            fetch_sql = text(f"""
                SELECT id, name, description, category, tags, goal_pattern, 
                       strategy_template, steps_template, alternatives_template,
                       status, version, success_rate, avg_execution_time, usage_count,
                       source_plan_ids, source_task_descriptions,
                       created_at, updated_at, last_used_at
                FROM plan_templates
                WHERE id IN ({id_placeholders})
            """)
            
            fetch_result = self.db.execute(fetch_sql, id_params)
            fetch_rows = fetch_result.fetchall()
            
            # Reconstruct templates and maintain order from vector search
            template_dict = {}
            for row in fetch_rows:
                template = PlanTemplate()
                template.id = row[0]
                template.name = row[1]
                template.description = row[2]
                template.category = row[3]
                template.tags = row[4]
                template.goal_pattern = row[5]
                template.strategy_template = row[6]
                template.steps_template = row[7]
                template.alternatives_template = row[8]
                template.status = row[9]
                template.version = row[10]
                template.success_rate = row[11]
                template.avg_execution_time = row[12]
                template.usage_count = row[13]
                template.source_plan_ids = row[14]
                template.source_task_descriptions = row[15]
                template.created_at = row[16]
                template.updated_at = row[17]
                template.last_used_at = row[18]
                template.embedding = None
                template_dict[template.id] = template
            
            # Return in order from vector search
            return [template_dict[tid] for tid in template_ids if tid in template_dict]
            
        except Exception as e:
            logger.warning(f"Vector search failed: {e}, falling back to text search")
            # Fallback to text search with filters
            return self._find_templates_text_search_with_filters(
                base_conditions, task_description, limit
            )
    
    def _find_templates_text_search(
        self,
        base_query,
        task_description: str,
        limit: int
    ) -> List[PlanTemplate]:
        """Find templates using text-based search (using raw SQL to avoid vector type issues)"""
        from sqlalchemy import text
        
        # Search in name, description, goal_pattern, category, tags
        search_terms = task_description.lower().split()[:5]  # Limit to 5 terms
        
        # Build SQL conditions
        conditions = ["status = 'active'"]
        params = {}
        
        if search_terms:
            term_conditions = []
            for i, term in enumerate(search_terms):
                param_name = f"term_{i}"
                term_conditions.append(
                    f"(LOWER(name) LIKE :{param_name} OR "
                    f"LOWER(description) LIKE :{param_name} OR "
                    f"LOWER(goal_pattern) LIKE :{param_name} OR "
                    f"LOWER(category) LIKE :{param_name})"
                )
                params[param_name] = f"%{term}%"
            
            if term_conditions:
                conditions.append(f"({' OR '.join(term_conditions)})")
        
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        
        sql = text(f"""
            SELECT id, name, description, category, tags, goal_pattern, 
                   strategy_template, steps_template, alternatives_template,
                   status, version, success_rate, avg_execution_time, usage_count,
                   source_plan_ids, source_task_descriptions,
                   created_at, updated_at, last_used_at
            FROM plan_templates
            WHERE {where_clause}
            ORDER BY usage_count DESC, success_rate DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, params)
        rows = result.fetchall()
        
        # Reconstruct PlanTemplate objects from rows
        templates = []
        for row in rows:
            template = PlanTemplate()
            template.id = row[0]
            template.name = row[1]
            template.description = row[2]
            template.category = row[3]
            template.tags = row[4]
            template.goal_pattern = row[5]
            template.strategy_template = row[6]
            template.steps_template = row[7]
            template.alternatives_template = row[8]
            template.status = row[9]
            template.version = row[10]
            template.success_rate = row[11]
            template.avg_execution_time = row[12]
            template.usage_count = row[13]
            template.source_plan_ids = row[14]
            template.source_task_descriptions = row[15]
            template.created_at = row[16]
            template.updated_at = row[17]
            template.last_used_at = row[18]
            template.embedding = None  # Not loaded to avoid vector type issues
            templates.append(template)
        
        return templates
    
    def _find_templates_text_search_with_filters(
        self,
        base_conditions: Dict[str, Any],
        task_description: str,
        limit: int
    ) -> List[PlanTemplate]:
        """Find templates using text-based search with filters (using raw SQL to avoid vector type issues)"""
        from sqlalchemy import text
        
        # Build WHERE conditions
        conditions = ["status = :status"]
        params = {"status": base_conditions["status"], "limit": limit}
        
        if base_conditions.get("min_success_rate"):
            conditions.append(
                "(success_rate IS NULL OR success_rate >= :min_success_rate)"
            )
            params["min_success_rate"] = base_conditions["min_success_rate"]
        
        if base_conditions.get("category"):
            conditions.append("category = :category")
            params["category"] = base_conditions["category"]
        
        # Search in name, description, goal_pattern, category, tags
        search_terms = task_description.lower().split()[:5]  # Limit to 5 terms
        
        if search_terms:
            term_conditions = []
            for i, term in enumerate(search_terms):
                param_name = f"term_{i}"
                term_conditions.append(
                    f"(LOWER(name) LIKE :{param_name} OR "
                    f"LOWER(description) LIKE :{param_name} OR "
                    f"LOWER(goal_pattern) LIKE :{param_name} OR "
                    f"LOWER(category) LIKE :{param_name})"
                )
                params[param_name] = f"%{term}%"
            
            if term_conditions:
                conditions.append(f"({' OR '.join(term_conditions)})")
        
        where_clause = " AND ".join(conditions)
        
        sql = text(f"""
            SELECT id, name, description, category, tags, goal_pattern, 
                   strategy_template, steps_template, alternatives_template,
                   status, version, success_rate, avg_execution_time, usage_count,
                   source_plan_ids, source_task_descriptions,
                   created_at, updated_at, last_used_at
            FROM plan_templates
            WHERE {where_clause}
            ORDER BY usage_count DESC, success_rate DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, params)
        rows = result.fetchall()
        
        # Reconstruct PlanTemplate objects from rows
        templates = []
        for row in rows:
            template = PlanTemplate()
            template.id = row[0]
            template.name = row[1]
            template.description = row[2]
            template.category = row[3]
            template.tags = row[4]
            template.goal_pattern = row[5]
            template.strategy_template = row[6]
            template.steps_template = row[7]
            template.alternatives_template = row[8]
            template.status = row[9]
            template.version = row[10]
            template.success_rate = row[11]
            template.avg_execution_time = row[12]
            template.usage_count = row[13]
            template.source_plan_ids = row[14]
            template.source_task_descriptions = row[15]
            template.created_at = row[16]
            template.updated_at = row[17]
            template.last_used_at = row[18]
            template.embedding = None  # Not loaded to avoid vector type issues
            templates.append(template)
        
        return templates
    
    def get_template(self, template_id: UUID) -> Optional[PlanTemplate]:
        """Get a template by ID (excluding embedding field to avoid vector type issues)"""
        # Use raw SQL to avoid SQLAlchemy vector type issues
        from sqlalchemy import text
        sql = text("""
            SELECT id, name, description, category, tags, goal_pattern, 
                   strategy_template, steps_template, alternatives_template,
                   status, version, success_rate, avg_execution_time, usage_count,
                   source_plan_ids, source_task_descriptions,
                   created_at, updated_at, last_used_at
            FROM plan_templates
            WHERE id = CAST(:id AS uuid)
        """)
        result = self.db.execute(sql, {"id": str(template_id)})
        row = result.fetchone()
        
        if not row:
            return None
        
        # Reconstruct PlanTemplate object from row
        template = PlanTemplate()
        template.id = row[0]
        template.name = row[1]
        template.description = row[2]
        template.category = row[3]
        template.tags = row[4]
        template.goal_pattern = row[5]
        template.strategy_template = row[6]
        template.steps_template = row[7]
        template.alternatives_template = row[8]
        template.status = row[9]
        template.version = row[10]
        template.success_rate = row[11]
        template.avg_execution_time = row[12]
        template.usage_count = row[13]
        template.source_plan_ids = row[14]
        template.source_task_descriptions = row[15]
        template.created_at = row[16]
        template.updated_at = row[17]
        template.last_used_at = row[18]
        template.embedding = None  # Not loaded to avoid vector type issues
        
        return template
    
    def list_templates(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PlanTemplate]:
        """List templates with optional filters (using raw SQL to avoid vector type issues)"""
        from sqlalchemy import text
        
        conditions = ["1=1"]  # Always true base condition
        params = {}
        
        if category:
            conditions.append("category = :category")
            params["category"] = category
        
        if status:
            conditions.append("status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        
        sql = text(f"""
            SELECT id, name, description, category, tags, goal_pattern, 
                   strategy_template, steps_template, alternatives_template,
                   status, version, success_rate, avg_execution_time, usage_count,
                   source_plan_ids, source_task_descriptions,
                   created_at, updated_at, last_used_at
            FROM plan_templates
            WHERE {where_clause}
            ORDER BY usage_count DESC, created_at DESC
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, params)
        rows = result.fetchall()
        
        # Reconstruct PlanTemplate objects from rows
        templates = []
        for row in rows:
            template = PlanTemplate()
            template.id = row[0]
            template.name = row[1]
            template.description = row[2]
            template.category = row[3]
            template.tags = row[4]
            template.goal_pattern = row[5]
            template.strategy_template = row[6]
            template.steps_template = row[7]
            template.alternatives_template = row[8]
            template.status = row[9]
            template.version = row[10]
            template.success_rate = row[11]
            template.avg_execution_time = row[12]
            template.usage_count = row[13]
            template.source_plan_ids = row[14]
            template.source_task_descriptions = row[15]
            template.created_at = row[16]
            template.updated_at = row[17]
            template.last_used_at = row[18]
            template.embedding = None  # Not loaded to avoid vector type issues
            templates.append(template)
        
        return templates
    
    def _rank_templates(
        self,
        templates: List[PlanTemplate],
        task_description: str
    ) -> List[PlanTemplate]:
        """
        Rank templates by combined relevance score.
        
        Score factors:
        - Text similarity (if available from search)
        - Success rate (higher is better)
        - Usage count (more used = more proven)
        - Recency (newer templates might be more relevant)
        
        Args:
            templates: List of templates to rank
            task_description: Task description for additional scoring
            
        Returns:
            List of templates sorted by relevance score (best first)
        """
        if not templates:
            return []
        
        # Calculate scores for each template
        scored_templates = []
        task_lower = task_description.lower()
        
        for template in templates:
            score = 0.0
            
            # Base score from success rate (0.0 to 1.0, weighted 0.4)
            if template.success_rate:
                score += template.success_rate * 0.4
            else:
                score += 0.2  # Default score for templates without success rate
            
            # Usage count score (normalized, weighted 0.3)
            # Normalize usage count (assume max 100 uses = full score)
            usage_score = min(template.usage_count / 100.0, 1.0) if template.usage_count else 0.0
            score += usage_score * 0.3
            
            # Text match score (weighted 0.3)
            # Check how many task words appear in template fields
            task_words = set(task_lower.split())
            template_text = f"{template.name} {template.description or ''} {template.goal_pattern or ''} {template.category or ''}".lower()
            template_words = set(template_text.split())
            
            if task_words:
                match_ratio = len(task_words & template_words) / len(task_words)
                score += match_ratio * 0.3
            
            scored_templates.append((score, template))
        
        # Sort by score (descending)
        scored_templates.sort(key=lambda x: x[0], reverse=True)
        
        # Return templates in ranked order
        return [template for _, template in scored_templates]
    
    def update_template_usage(self, template_id: UUID):
        """Update template usage statistics"""
        template = self.get_template(template_id)
        if template:
            template.usage_count += 1
            template.last_used_at = datetime.utcnow()
            self.db.commit()
            logger.debug(f"Updated usage for template {template_id}")

