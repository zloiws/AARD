# Отчет аудита кода AARD

*Сгенерировано: 1764918729.477309*


## Сводка


- Дублированных функций: 9

- Дублированных блоков кода: 59

- Неиспользуемых импортов: 555

- Неиспользуемых функций: 322

- Устаревших компонентов: 97


## Дублированные функции


### init_servers()

Найдено в 2 местах:

- `init_servers.py:20` - init_servers

- `scripts\init_ollama_servers.py:20` - init_servers



### print_separator(title)

Найдено в 9 местах:

- `scripts\run_test1.py:19` - print_separator

- `scripts\run_test2.py:21` - print_separator

- `scripts\run_test3.py:21` - print_separator

- `scripts\run_test4.py:19` - print_separator

- `scripts\run_test5.py:21` - print_separator

- `scripts\run_test6_complex_decomposition.py:20` - print_separator

- `tests\scripts\test_branching.py:22` - print_separator

- `tests\scripts\test_branching_endpoints.py:16` - print_separator

- `tests\scripts\test_planning_step_by_step.py:20` - print_separator



### db()

Найдено в 6 местах:

- `tests\conftest.py:18` - db

- `tests\test_plan_tree_api.py:18` - db

- `tests\integration\test_checkpoint_api_integration.py:18` - db

- `tests\integration\test_planning_digital_twin.py:17` - db

- `tests\integration\test_planning_system_complete.py:19` - db

- `tests\integration\test_plan_visualization.py:18` - db



### mock_db(self)

Найдено в 4 местах:

- `tests\test_agent_selection.py:17` - mock_db

- `tests\test_planning_service_unit.py:18` - mock_db

- `tests\test_plan_execution.py:19` - mock_db

- `tests\test_plan_execution.py:132` - mock_db



### __init__(self, db)

Найдено в 27 местах:

- `app\core\model_selector.py:30` - __init__

- `app\core\ollama_db_client.py:16` - __init__

- `app\core\ollama_manager.py:16` - __init__

- `app\services\a2a_router.py:30` - __init__

- `app\services\adaptive_approval_service.py:37` - __init__

- `app\services\agent_experiment_service.py:23` - __init__

- `app\services\agent_gym_service.py:31` - __init__

- `app\services\agent_heartbeat_service.py:24` - __init__

- `app\services\agent_registry.py:27` - __init__

- `app\services\agent_service.py:20` - __init__

- `app\services\approval_service.py:24` - __init__

- `app\services\auth_service.py:20` - __init__

- `app\services\checkpoint_service.py:25` - __init__

- `app\services\decision_pipeline.py:26` - __init__

- `app\services\decision_router.py:23` - __init__

- `app\services\execution_service.py:47` - __init__

- `app\services\execution_service.py:623` - __init__

- `app\services\feedback_learning_service.py:27` - __init__

- `app\services\interactive_execution_service.py:36` - __init__

- `app\services\memory_service.py:27` - __init__

- `app\services\meta_learning_service.py:31` - __init__

- `app\services\planning_metrics_service.py:29` - __init__

- `app\services\planning_service.py:25` - __init__

- `app\services\request_logger.py:18` - __init__

- `app\services\task_queue_manager.py:26` - __init__

- `app\services\tool_service.py:20` - __init__

- `app\services\workflow_event_service.py:23` - __init__



### test_task(db)

Найдено в 3 местах:

- `tests\integration\test_adaptive_approval.py:17` - test_task

- `tests\integration\test_feedback_learning.py:17` - test_task

- `tests\integration\test_planning_metrics.py:16` - test_task



### test_plan(db, test_task)

Найдено в 3 местах:

- `tests\integration\test_adaptive_approval.py:34` - test_plan

- `tests\integration\test_feedback_learning.py:34` - test_plan

- `tests\integration\test_planning_metrics.py:33` - test_plan



### db_session()

Найдено в 2 местах:

- `tests\integration\test_agent_planning.py:18` - db_session

- `tests\integration\test_full_plan_execution.py:22` - db_session



### print_response(response, title)

Найдено в 2 местах:

- `tests\integration\test_planning_api.py:16` - print_response

- `tests\integration\test_planning_api_simple.py:13` - print_response



## Неиспользуемые импорты


### init_servers.py

Импорты: app, pathlib


### main.py

Импорты: contextlib, fastapi


### run.py

Импорты: pathlib


### run_migration.py

Импорты: pathlib


### run_migration_fixed.py

Импорты: pathlib


### alembic\env.py

Импорты: *, pathlib


### scripts\apply_migration_019.py

Импорты: sqlalchemy, pathlib


### scripts\apply_migration_020.py

Импорты: sqlalchemy, pathlib


### scripts\check_logs_after_test.py

Импорты: app, sqlalchemy, pathlib


### scripts\check_plan_details.py

Импорты: sqlalchemy, pathlib


### scripts\clear_and_restore.py

Импорты: scripts, pathlib


### scripts\clear_database.py

Импорты: app, sqlalchemy, pathlib


### scripts\code_audit.py

Импорты: collections, pathlib


### scripts\consolidate_plans.py

Импорты: collections, defaultdict, pathlib


### scripts\init_ollama_servers.py

Импорты: app, OllamaModel, pathlib


### scripts\reorganize_project.py

Импорты: pathlib


### scripts\restore_servers.py

Импорты: app, pathlib


### scripts\run_planning_tests.py

Импорты: pathlib


### scripts\run_test1.py

Импорты: app, pathlib


### scripts\run_test2.py

Импорты: app, pathlib


### scripts\run_test3.py

Импорты: app, pathlib


### scripts\run_test4.py

Импорты: pathlib


### scripts\run_test5.py

Импорты: app, pathlib


### scripts\run_test6_complex_decomposition.py

Импорты: pathlib


### scripts\setup_main_models.py

Импорты: app, sqlalchemy, pathlib


### scripts\switch_model_for_tests.py

Импорты: sqlalchemy, pathlib


### tests\conftest.py

Импорты: fastapi, sqlalchemy, pathlib


### tests\test_agent_selection.py

Импорты: unittest, sqlalchemy


### tests\test_auto_replan_service.py

Импорты: unittest, ErrorSeverity, sqlalchemy


### tests\test_execution_error_detection.py

Импорты: app


## Неиспользуемые функции


- `tests\conftest.py:18` - db

- `tests\conftest.py:34` - client

- `tests\conftest.py:55` - override_get_db

- `tests\test_agent_selection.py:17` - mock_db

- `tests\test_agent_selection.py:22` - agent_service

- `tests\test_agent_selection.py:27` - sample_agents

- `tests\test_agent_selection.py:54` - test_select_agent_for_task_no_capabilities

- `tests\test_agent_selection.py:67` - test_select_agent_for_task_with_capabilities

- `tests\test_agent_selection.py:91` - test_select_agent_preferred_agent

- `tests\test_agent_selection.py:107` - test_select_agent_no_matching_agents

- `tests\test_execution_error_detection.py:18` - test_critical_plan_structure_error

- `tests\test_execution_error_detection.py:26` - test_critical_dependency_error

- `tests\test_execution_error_detection.py:34` - test_critical_environment_error

- `tests\test_execution_error_detection.py:42` - test_high_severity_agent_error

- `tests\test_execution_error_detection.py:50` - test_high_severity_validation_error

- `tests\test_execution_error_detection.py:58` - test_timeout_error

- `tests\test_execution_error_detection.py:66` - test_timeout_after_retries

- `tests\test_execution_error_detection.py:77` - test_medium_severity_unknown_error

- `tests\test_execution_error_detection.py:85` - test_requires_replanning_function

- `tests\test_execution_error_detection.py:91` - test_error_with_context

- `tests\test_execution_error_detection.py:109` - test_error_with_type

- `tests\test_execution_error_detection.py:120` - test_error_to_dict

- `tests\test_execution_error_detection.py:133` - test_case_insensitive_patterns

- `tests\test_execution_error_detection.py:143` - test_multiple_pattern_matching

- `tests\test_execution_error_detection.py:151` - test_resource_error_detection

- `tests\test_execution_error_detection.py:159` - test_circular_dependency_error

- `tests\test_ollama_client.py:9` - ollama_client

- `tests\test_ollama_client.py:14` - test_model_selection

- `tests\test_ollama_client.py:26` - test_cache_key_generation

- `tests\test_planning_service_unit.py:18` - mock_db



## Устаревшие компоненты


- `init_servers.py:39` - remove

  # Remove /v1 if present to get base URL


- `init_servers.py:62` - remove

  # Remove /v1 if present to get base URL


- `scripts\clear_database.py:41` - temp

  # Disable foreign key checks temporarily


- `scripts\consolidate_plans.py:1142` - todo

  output.append(f"#### Не начато ({len(area_todo)})\n\n")


- `scripts\init_ollama_servers.py:39` - remove

  # Remove /v1 if present to get base URL


- `scripts\init_ollama_servers.py:62` - remove

  # Remove /v1 if present to get base URL


- `scripts\restore_servers.py:51` - remove

  # Remove /v1 if present to get base URL


- `scripts\restore_servers.py:75` - remove

  # Remove /v1 if present to get base URL


- `scripts\run_test2.py:62` - todo

  # Check active_todos


- `scripts\run_test2.py:80` - todo

  # Show active todos


- `tests\test_planning_service_unit.py:92` - legacy

  """Test legacy parse_json_from_response method"""


- `tests\test_replan_config.py:86` - temp

  "AUTO_REPLANNING_MAX_ATTEMPTS": "0"  # Invalid: should be >= 1


- `tests\test_replan_config.py:108` - temp

  "AUTO_REPLANNING_MAX_ATTEMPTS": "15"  # Invalid: should be <= 10


- `alembic\versions\017_extend_task_lifecycle.py:34` - remove

  # Remove columns


- `alembic\versions\018_add_task_digital_twin.py:25` - todo

  # - active and historical ToDo lists


- `alembic\versions\018_add_task_digital_twin.py:50` - remove

  # Remove index


- `alembic\versions\018_add_task_digital_twin.py:53` - remove

  # Remove context column


- `app\agents\base_agent.py:145` - temp

  # Use agent's temperature if not specified


- `app\core\logging_config.py:68` - remove

  # Remove format string if provided (we don't use it for JSON)


- `app\core\middleware_metrics.py:49` - remove

  # Remove UUIDs and IDs from path for better aggregation


- `app\core\ollama_client.py:162` - remove

  # Remove /v1 from base URL for client


- `app\core\ollama_client.py:185` - remove

  base_url = base_url[:-3]  # Remove /v1


- `app\core\ollama_client.py:187` - remove

  base_url = base_url[:-4]  # Remove /v1/


- `app\core\ollama_client.py:189` - temporary

  # Create a temporary client for health check


- `app\core\ollama_client.py:218` - temporary

  # Create temporary client for check


- `app\core\ollama_client.py:438` - remove

  # Prepare request URL (remove /v1 for API calls)


- `app\core\templates.py:9` - temp

  # Get templates directory


- `app\core\templates.py:20` - temp

  # Create FastAPI templates instance


- `app\core\templates.py:25` - temp

  """Render template with context"""


- `app\core\workflow_tracker.py:118` - temporary

  # No active workflow, create a temporary one

