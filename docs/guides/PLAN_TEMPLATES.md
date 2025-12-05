# Plan Templates System

## Overview

The Plan Templates system allows the AARD platform to extract reusable patterns from successful plans and use them to accelerate future planning. This system learns from past successes and applies proven patterns to new tasks.

## Features

- **Automatic Template Extraction**: Extract templates from successfully completed plans
- **Pattern Abstraction**: Replace specific details with placeholders to create reusable patterns
- **Semantic Search**: Find relevant templates using vector embeddings
- **Template Adaptation**: Adapt templates to new tasks while preserving proven structure

## Architecture

### Components

1. **PlanTemplate Model** (`app/models/plan_template.py`)
   - Stores template structure and metadata
   - Tracks usage statistics and success rates
   - Supports vector embeddings for semantic search

2. **PlanTemplateService** (`app/services/plan_template_service.py`)
   - Extracts templates from successful plans
   - Abstracts specific details into patterns
   - Finds matching templates for new tasks
   - Manages template lifecycle

### Database Schema

```sql
CREATE TABLE plan_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags TEXT[],
    goal_pattern TEXT NOT NULL,
    strategy_template JSONB,
    steps_template JSONB NOT NULL,
    alternatives_template JSONB,
    status VARCHAR(20) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    success_rate FLOAT,
    avg_execution_time INTEGER,
    usage_count INTEGER DEFAULT 0,
    source_plan_ids UUID[],
    source_task_descriptions TEXT[],
    embedding vector(768),  -- For semantic search
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);
```

## Usage

### Automatic Template Extraction

Templates are **automatically extracted** when a plan is successfully completed. The system checks quality criteria before extraction:

**Quality Criteria:**
- Plan must be completed successfully
- Plan must have at least minimum number of steps (default: 2, configurable via `plan_template_min_steps`)
- Plan execution time must be within reasonable bounds:
  - Minimum: 10 seconds (default, configurable via `plan_template_min_duration`)
  - Maximum: 24 hours (default, configurable via `plan_template_max_duration`)
- Plan must have a clear structure (goal, steps, strategy)

**Configuration:**
```python
# In .env or settings
ENABLE_PLAN_TEMPLATE_EXTRACTION=true
PLAN_TEMPLATE_MIN_STEPS=2
PLAN_TEMPLATE_MIN_DURATION=10  # seconds
PLAN_TEMPLATE_MAX_DURATION=86400  # seconds (24 hours)
```

The extraction happens automatically in `ExecutionService` when a plan completes successfully.

### Manual Template Extraction

You can also manually extract templates from completed plans:

```python
from app.services.plan_template_service import PlanTemplateService
from uuid import UUID

service = PlanTemplateService(db)

# Extract template from a completed plan
template = service.extract_template_from_plan(
    plan_id=UUID("..."),
    template_name="API Development Pattern",
    category="api_development",
    tags=["python", "fastapi", "rest"]
)
```

### Finding Matching Templates

Search for templates that match a new task. The system uses semantic search (vector embeddings) if available, otherwise falls back to text-based search. Results are ranked by relevance, success rate, and usage count.

```python
# Using semantic search (vector embeddings) - recommended
templates = service.find_matching_templates(
    task_description="Create a REST API for product management",
    limit=5,
    min_success_rate=0.7,
    use_vector_search=True
)

# Using text-based search (fallback)
templates = service.find_matching_templates(
    task_description="Create a REST API for product management",
    limit=5,
    use_vector_search=False
)

# With category filter
templates = service.find_matching_templates(
    task_description="Create API",
    category="api_development",
    limit=5
)

# With tags filter
templates = service.find_matching_templates(
    task_description="Create Python API",
    tags=["python", "api"],
    limit=5
)
```

**Ranking Algorithm:**
Templates are ranked by a combined score that considers:
- **Success Rate** (40% weight): Higher success rate = better template
- **Usage Count** (30% weight): More frequently used = more proven
- **Text Match** (30% weight): How well template fields match the task description

The system automatically selects the best matching templates and returns them in order of relevance.

### Template Abstraction

The system automatically abstracts specific details from plans:

**Original Goal:**
```
"Create a REST API for user management with PostgreSQL database"
```

**Abstracted Pattern:**
```
"Create a REST API for {domain} management with {database_type} database"
```

**Original Step:**
```json
{
  "step": 1,
  "description": "Create User model in models/user.py",
  "type": "code"
}
```

**Abstracted Step:**
```json
{
  "step": 1,
  "description": "Create {entity} model in models/{file_path}",
  "type": "code"
}
```

## Template Structure

### Goal Pattern

The abstracted goal that describes what the template accomplishes:

```
"Create a REST API for {domain} management"
```

### Strategy Template

Abstracted strategy with placeholders:

```json
{
  "approach": "Use {framework} framework",
  "assumptions": ["{database} database available"],
  "constraints": ["Must be RESTful"]
}
```

### Steps Template

Array of abstracted steps:

```json
[
  {
    "step": 1,
    "description": "Create database models",
    "type": "code"
  },
  {
    "step": 2,
    "description": "Create API endpoints",
    "type": "code"
  },
  {
    "step": 3,
    "description": "Add authentication",
    "type": "code"
  }
]
```

## Template Categories

Templates are automatically categorized based on task description:

- `api_development` - REST APIs, GraphQL, endpoints
- `data_processing` - Database operations, data transformation
- `testing` - Unit tests, integration tests
- `deployment` - Docker, Kubernetes, CI/CD
- `code_refactoring` - Code cleanup, restructuring
- `general` - Other tasks

## Template Status

- `draft` - Template is being created
- `active` - Template is available for use
- `deprecated` - Template is no longer recommended
- `archived` - Template is archived

## Metrics

Templates track several metrics:

- **Success Rate**: Average success rate of plans using this template
- **Average Execution Time**: Average time to complete plans using this template
- **Usage Count**: Number of times this template has been used
- **Last Used**: Timestamp of last usage

## Semantic Search

When vector search is available, templates are indexed with embeddings for semantic similarity search. This allows finding templates even when exact keywords don't match.

Example:
- Task: "Build an HTTP service for customer data"
- Matches: "Create REST API for user management" (semantically similar)

## Best Practices

1. **Extract from Successful Plans Only**: Only extract templates from plans that completed successfully
2. **Use Meaningful Names**: Give templates descriptive names that indicate their purpose
3. **Add Categories and Tags**: Help with organization and discovery
4. **Review Abstracted Patterns**: Ensure placeholders make sense and are reusable
5. **Monitor Usage**: Track which templates are most effective

## Future Enhancements

- Template versioning and evolution
- Template merging from multiple source plans
- Automatic template quality scoring
- Template recommendation engine
- Template adaptation using LLM

