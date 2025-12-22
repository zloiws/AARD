# Backend entities catalog (Phase 0)

This file is a human-readable summary of `backend/docs/entities/catalog.json`. Each `backend/app/*.py` file has exactly one classification. Files without clear classification would be marked `Legacy/Unknown` (none in this listing).

## Module (core, api, models, utils, security, ops, memory)
- `__init__.py`
- `main.py`

API routes (module):
- `api/__init__.py`
- `api/routes/__init__.py`
- `api/routes/a2a.py`
- `api/routes/agent_dialogs.py`
- `api/routes/agent_gym_pages.py`
- `api/routes/agent_gym.py`
- `api/routes/agent_memory.py`
- `api/routes/agents_pages.py`
- `api/routes/agents.py`
- `api/routes/approvals_pages.py`
- `api/routes/approvals.py`
- `api/routes/artifacts_pages.py`
- `api/routes/artifacts.py`
- `api/routes/audit_reports_pages.py`
- `api/routes/audit_reports.py`
- `api/routes/auth_pages.py`
- `api/routes/auth.py`
- `api/routes/benchmarks_pages.py`
- `api/routes/benchmarks.py`
- `api/routes/chat.py`
- `api/routes/checkpoints.py`
- `api/routes/current_work.py`
- `api/routes/dashboard_pages.py`
- `api/routes/dashboard.py`
- `api/routes/events.py`
- `api/routes/execution_graph.py`
- `api/routes/execution.py`
- `api/routes/experiments.py`
- `api/routes/health.py`
- `api/routes/logging.py`
- `api/routes/meta.py`
- `api/routes/metrics.py`
- `api/routes/model_logs.py`
- `api/routes/models_management.py`
- `api/routes/models.py`
- `api/routes/pages.py`
- `api/routes/plan_templates.py`
- `api/routes/plans_pages.py`
- `api/routes/plans.py`
- `api/routes/project_metrics_pages.py`
- `api/routes/project_metrics.py`
- `api/routes/prompts.py`
- `api/routes/queues.py`
- `api/routes/registry.py`
- `api/routes/requests.py`
- `api/routes/servers.py`
- `api/routes/settings_pages.py`
- `api/routes/settings.py`
- `api/routes/tools_pages.py`
- `api/routes/tools.py`
- `api/routes/traces_pages.py`
- `api/routes/traces.py`
- `api/routes/websocket_events.py`
- `api/routes/workflow_events.py`
- `api/routes/workflow.py`

Core modules:
- `core/__init__.py`
- `core/a2a_protocol.py`
- `core/auth.py`
- `core/chat_session.py`
- `core/config.py`
- `core/database.py`
- `core/decision_framework.py`
- `core/execution_context.py`
- `core/execution_error_types.py`
- `core/function_calling.py`
- `core/logging_config.py`
- `core/meta_tracker.py`
- `core/metrics.py`
- `core/middleware_metrics.py`
- `core/middleware.py`
- `core/model_selector.py`
- `core/ollama_client.py`
- `core/ollama_db_client.py`
- `core/ollama_manager.py`
- `core/permissions.py`
- `core/prompt_manager.py`
- `core/request_orchestrator.py`
- `core/request_router.py`
- `core/service_registry.py`
- `core/templates.py`
- `core/trace_exporter.py`
- `core/tracing.py`
- `core/utils.py`
- `core/workflow_engine.py`
- `core/workflow_tracker.py`

Models:
- `models/__init__.py`
- `models/agent_conversation.py`
- `models/agent_experiment.py`
- `models/agent_memory.py`
- `models/agent_team.py`
- `models/agent_test.py`
- `models/agent.py`
- `models/approval.py`
- `models/artifact_version.py`
- `models/artifact.py`
- `models/audit_report.py`
- `models/benchmark_result.py`
- `models/benchmark_task.py`
- `models/chat_session.py`
- `models/checkpoint.py`
- `models/evolution.py`
- `models/execution_graph.py`
- `models/interpretation.py`
- `models/learning_pattern.py`
- `models/ollama_model.py`
- `models/ollama_server.py`
- `models/plan_template.py`
- `models/plan.py`
- `models/planning.py`
- `models/project_metric.py`
- `models/prompt_assignment.py`
- `models/prompt.py`
- `models/request_log.py`
- `models/system_parameter.py`
- `models/system_setting.py`
- `models/task_queue.py`
- `models/task.py`
- `models/test_table.py`
- `models/tool.py`
- `models/trace.py`
- `models/uncertainty_parameters.py`
- `models/uncertainty_types.py`
- `models/user.py`
- `models/workflow_event.py`

Misc modules:
- `ops/__init__.py`
- `memory/__init__.py`
- `security/__init__.py`
- `utils/__init__.py`
- `utils/datetime_utils.py`

## Service
- `planning/__init__.py`
- `planning/lifecycle.py`

Services (service-layer domain logic):
- `services/__init__.py`
- `services/workflow_event_service.py`
- `services/uncertainty_service.py`
- `services/uncertainty_learning_service.py`
- `services/tool_service.py`
- `services/task_queue_manager.py`
- `services/task_lifecycle_manager.py`
- `services/task_digital_twin_service.py`
- `services/system_setting_service.py`
- `services/self_audit_service.py`
- `services/request_logger.py`
- `services/reflection_service.py`
- `services/quota_management_service.py`
- `services/prompt_service.py`
- `services/prompt_runtime_selector.py`
- `services/project_metrics_service.py`
- `services/plan_template_service.py`
- `services/plan_evaluation_service.py`
- `services/planning_service_dialog_integration.py`
- `services/planning_service.py`
- `services/planning_metrics_service.py`
- `services/planning_hypothesis_service.py`
- `services/parameter_manager.py`
- `services/ollama_service.py`
- `services/model_benchmark_service.py`
- `services/meta_learning_service.py`
- `services/memory_service.py`
- `services/interpretation_service.py`
- `services/interactive_execution_service.py`
- `services/feedback_learning_service.py`
- `services/execution_service.py`
- `services/execution_graph_service.py`
- `services/evolution_graph_service.py`
- `services/embedding_service.py`
- `services/decision_router.py`
- `services/decision_pipeline.py`
- `services/critic_service.py`
- `services/conflict_resolution_service.py`
- `services/checkpoint_service.py`
- `services/benchmark_service.py`
- `services/auth_service.py`
- `services/artifact_version_service.py`
- `services/artifact_generator.py`
- `services/approval_service.py`
- `services/agent_team_service.py`
- `services/agent_team_coordination.py`
- `services/agent_service.py`
- `services/agent_registry.py`
- `services/agent_heartbeat_service.py`
- `services/agent_gym_service.py`
- `services/agent_experiment_service.py`
- `services/agent_evolution_service.py`
- `services/agent_dialog_service.py`
- `services/agent_approval_agent.py`
- `services/agent_aging_monitor.py`
- `services/adaptive_approval_service.py`
- `services/a2a_router.py`
- `services/plan_tree_service.py`
- `services/agent_heartbeat_background.py`
- `services/audit_scheduler.py`
- `services/code_execution_sandbox.py`

## Agent
- `agents/__init__.py`
- `agents/base_agent.py`
- `agents/coder_agent.py`
- `agents/planner_agent.py`
- `agents/simple_agent.py`

## Capability/Tool
- `tools/__init__.py`
- `tools/base_tool.py`
- `tools/python_tool.py`
- `tools/web_search_tool.py`

## Registry
- `registry/__init__.py`
- `registry/service.py`

## Component (LLM components)
- `components/__init__.py`
- `components/contracts.py`
- `components/decision_routing.py`
- `components/execution_validator.py`
- `components/interpretation_service.py`
- `components/planning_service.py`
- `components/prompt_repository.py`
- `components/reflection_service.py`
- `components/semantic_validator.py`

---

Phase 0 completion criteria:
- every `backend/app/**.py` file has exactly one classification (as above)
- files without clear classification must be explicitly archived as `Legacy/Unknown`


