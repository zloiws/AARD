# TEST_MATRIX — inventory of backend tests

Columns: File | Category | Markers | DB | LLM | Notes

| File | Category | Markers | DB | LLM | Notes | | SuggestedMarkers |
| --- | --- | --- | ---: | ---: | --- |  | --- |
| backend/tests/cli/test_migrations_cli.py | cli |  | no | no |  |  |
| backend/tests/components/test_component_contracts.py | unit | asyncio,parametrize | no | no |  |  |
| backend/tests/conftest.py | unit | skip | yes | yes |  | integration,real_llm |
| backend/tests/debug_service_registry.py | unit | integration | yes | no |  | integration |
| backend/tests/docs/test_service_docs_present.py | docs |  | no | no |  |  |
| backend/tests/execute_phase3_tests.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/integration/test_adaptive_approval.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_agent_dialog_workflow.py | integration | asyncio,slow | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_agent_dialogs.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_agent_dialogs_complete.py | integration | asyncio,slow,timeout | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_agent_dialogs_real_llm.py | integration | asyncio,slow,timeout | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_agent_planning.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_agent_teams.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_agent_teams_consistency.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_agent_teams_llm.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_agent_teams_real_llm.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_alternative_plans.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_api.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_app.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_auto_approval_transition.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_auto_replan_trigger.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_auto_replanning.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_benchmark_models.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_chat_api.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_chat_with_model.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_chat_with_planning.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_checkpoint_api_integration.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_code_sandbox.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_config.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_dashboard_api.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_db_connection.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_env_loading.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_execution_engine.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_feedback_learning.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_full_plan_execution.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_full_system_e2e.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_function_calling.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_instance_selection.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_interactive_execution.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_logging_api.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_logging_system.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_migration.py | integration | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_model_benchmark_real.py | integration | asyncio,slow,timeout | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_model_generation.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_model_selector.py | integration | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_new_components.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_new_features.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_ollama_connection.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_ollama_integration.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_orchestrator_integration.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_phase3_full_integration.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_phase3_orchestrator_integration.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_phase4_integration.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_phase5_e2e_workflows.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_phase6_api_consistency.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_phase6_consistency.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_plan_approval_integration.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_plan_memory_integration.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_plan_visualization.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_planning_api.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_planning_api_simple.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_planning_digital_twin.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_planning_metrics.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_planning_system_complete.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_planning_with_dialogs.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_planning_with_dialogs_real_llm.py | integration | asyncio,slow,timeout | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_planning_with_prompts.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_project_metrics_integration.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_prompt_ab_testing.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_prompt_auto_improvement.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_prompt_create.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_prompt_improvement_cycle.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_prompt_manager_integration.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_prompt_service_integration.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_real_llm_full_workflow.py | integration | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_real_modules_interaction.py | integration | asyncio,slow,timeout | yes | yes |  | integration,real_llm |
| backend/tests/integration/test_startup.py | integration | integration,real_llm | no | yes |  | integration,real_llm |
| backend/tests/integration/test_task_lifecycle.py | integration | integration | yes | no |  | integration |
| backend/tests/integration/test_tracing.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_vector_search.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_vector_search_complete.py | integration | asyncio | yes | no |  | integration |
| backend/tests/integration/test_web_interface.py | integration | integration | no | no |  | integration |
| backend/tests/integration/test_workflow_engine.py | integration | integration | yes | no |  | integration |
| backend/tests/planning/test_plan_lifecycle.py | integration | integration | yes | no |  |  |
| backend/tests/quick_test.py | unit | integration | yes | no |  | integration |
| backend/tests/run_all_levels.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/run_all_phase3_tests.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/run_all_phase_tests.py | unit | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/run_all_tests.py | unit | integration | yes | no |  | integration |
| backend/tests/run_full_phase3_test.py | unit |  | no | no |  |  |
| backend/tests/run_orchestrator_integration_tests.py | integration | integration | no | no |  | integration |
| backend/tests/run_phase3_integration_test.py | integration | integration | no | no |  | integration |
| backend/tests/run_phase3_sequential.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/run_phase3_tests_detailed.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/run_phase5_comprehensive_tests.py | unit | integration | yes | no |  | integration |
| backend/tests/run_phase_tests.py | unit | integration | yes | no |  | integration |
| backend/tests/run_tests_fixed.py | unit |  | no | no |  |  |
| backend/tests/run_tests_sequentially.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/run_tests_simple.py | unit |  | no | no |  |  |
| backend/tests/run_tests_summary.py | unit |  | no | no |  |  |
| backend/tests/scripts/test_branching.py | scripts | integration | yes | no |  | integration |
| backend/tests/scripts/test_branching_endpoints.py | scripts |  | no | no |  |  |
| backend/tests/scripts/test_planning_step_by_step.py | scripts | integration | yes | no |  | integration |
| backend/tests/scripts/test_real_integration_chat.py | integration | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/scripts/test_real_integration_planning.py | integration | integration | yes | no |  | integration |
| backend/tests/scripts/test_websocket_integration.py | integration | integration | yes | no |  | integration |
| backend/tests/scripts/test_websocket_simple.py | scripts |  | no | no |  |  |
| backend/tests/scripts/test_workflow_events.py | scripts | integration | yes | no |  | integration |
| backend/tests/scripts/test_workflow_events_detailed.py | scripts | integration | yes | no |  | integration |
| backend/tests/test_agent_conversation_model.py | unit | integration | yes | no |  | integration |
| backend/tests/test_agent_dialog_api.py | api | integration | yes | no |  | integration |
| backend/tests/test_agent_dialog_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_agent_selection.py | unit | integration | yes | no |  | integration |
| backend/tests/test_agent_team_coordination.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_agent_team_model.py | unit | integration | yes | no |  | integration |
| backend/tests/test_agent_team_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_alternative_plan_generation.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_audit_scheduler.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_audit_trends_analysis.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_auto_replan_service.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_benchmark_api.py | api | integration | yes | no |  | integration |
| backend/tests/test_benchmark_evaluation.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_benchmark_execution.py | unit | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/test_benchmark_result_model.py | unit | integration | yes | no |  | integration |
| backend/tests/test_benchmark_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_benchmark_task_model.py | unit | integration | yes | no |  | integration |
| backend/tests/test_contracts_api.py | api | integration | yes | no |  | integration |
| backend/tests/test_contracts_negative.py | unit |  | no | no |  |  |
| backend/tests/test_embedding_service.py | unit | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/test_execution_context.py | unit | integration | yes | no |  | integration |
| backend/tests/test_execution_error_detection.py | unit |  | no | no |  |  |
| backend/tests/test_integration_basic.py | integration | asyncio,integration | yes | yes |  | real_llm |
| backend/tests/test_integration_code_generation.py | integration | asyncio,integration,slow | yes | yes |  | real_llm |
| backend/tests/test_integration_complex_task.py | integration | asyncio,integration,slow | yes | yes |  | real_llm |
| backend/tests/test_integration_comprehensive.py | integration | asyncio | yes | no |  | integration |
| backend/tests/test_integration_prompt_improvement.py | integration | asyncio,integration,slow | yes | yes |  | real_llm |
| backend/tests/test_integration_simple_question.py | integration | asyncio,integration | yes | yes |  | real_llm |
| backend/tests/test_interpretation_llm_integration.py | integration | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/test_memory_service_integration.py | integration | integration | yes | no |  | integration |
| backend/tests/test_memory_vector_search.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_meta_learning_service_integration.py | integration | asyncio | yes | no |  | integration |
| backend/tests/test_ollama_client.py | cli | asyncio | no | yes |  | real_llm |
| backend/tests/test_phase1_critical_fixes.py | unit | integration | yes | no |  | integration |
| backend/tests/test_phase2_dual_model.py | unit | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/test_phase3_autonomy_levels.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_phase4_workflow_engine.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_plan_evaluation.py | unit | integration | yes | no |  | integration |
| backend/tests/test_plan_execution.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_plan_template_extraction.py | unit | integration | yes | no |  | integration |
| backend/tests/test_plan_template_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_plan_tree_api.py | api | integration | yes | no |  | integration |
| backend/tests/test_plan_tree_service.py | unit |  | no | no |  |  |
| backend/tests/test_planning_service_unit.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_planning_with_teams.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_project_metrics_api.py | api | integration | yes | no |  | integration |
| backend/tests/test_project_metrics_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_assignments.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_improvement_suggestions.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_prompt_manager.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_prompt_metrics.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_reflection.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_prompt_runtime_selector.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_runtime_selector_edges.py | unit | integration,real_llm | yes | yes |  | integration,real_llm |
| backend/tests/test_prompt_service.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_success_rate.py | unit | integration | yes | no |  | integration |
| backend/tests/test_prompt_version_creation.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_prompts_api.py | api |  | no | no |  |  |
| backend/tests/test_reflection_service_integration.py | integration | asyncio | yes | no |  | integration |
| backend/tests/test_replan_config.py | unit | real_llm | no | yes |  | real_llm |
| backend/tests/test_request_orchestrator.py | unit | asyncio | yes | yes |  | integration,real_llm |
| backend/tests/test_runner.py | unit |  | no | no |  |  |
| backend/tests/test_self_audit_service.py | unit | asyncio | yes | no |  | integration |
| backend/tests/test_service_registry.py | unit | integration | yes | no |  | integration |
| backend/tests/test_vector_migration.py | unit | skipif | yes | no |  | integration |
| backend/tests/test_workflow_event_contract.py | unit |  | no | no |  |  |
