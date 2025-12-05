"""
Реальные тесты бенчмарка моделей
Проводит реальное тестирование всех моделей на сервере
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Настройка кодировки
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.model_benchmark_service import ModelBenchmarkService
from app.services.ollama_service import OllamaService
from app.core.ollama_client import TaskType
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(600)  # 10 минут на все тесты
async def test_benchmark_all_models_planning(db):
    """
    Реальный бенчмарк всех моделей на задаче планирования
    
    Тестирует каждую модель и сохраняет результаты
    """
    logger.info("\n" + "="*80)
    logger.info("НАЧАЛО БЕНЧМАРКА МОДЕЛЕЙ: Planning Task")
    logger.info("="*80)
    
    # Найти сервер 10.39.0.6
    servers = OllamaService.get_all_active_servers(db)
    server_10_39 = None
    for s in servers:
        if "10.39.0.6" in s.url:
            server_10_39 = s
            break
    
    if not server_10_39:
        pytest.skip("Сервер 10.39.0.6 не найден")
    
    logger.info(f"Сервер: {server_10_39.name} ({server_10_39.url})")
    
    # Получить модели
    models = OllamaService.get_models_for_server(db, str(server_10_39.id))
    from app.core.model_selector import ModelSelector
    model_selector = ModelSelector(db)
    models = model_selector._filter_embedding_models(models)
    
    logger.info(f"Будет протестировано моделей: {len(models)}")
    for i, m in enumerate(models, 1):
        logger.info(f"  {i}. {m.model_name}")
    
    # Запустить бенчмарк
    benchmark_service = ModelBenchmarkService(db)
    
    logger.info("\n" + "-"*80)
    logger.info("НАЧАЛО ТЕСТИРОВАНИЯ")
    logger.info("-"*80)
    
    results = await benchmark_service.benchmark_all_models(
        server=server_10_39,
        task_type=TaskType.PLANNING,
        timeout=30
    )
    
    # Вывести результаты
    logger.info("\n" + "="*80)
    logger.info("РЕЗУЛЬТАТЫ БЕНЧМАРКА")
    logger.info("="*80)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    logger.info(f"\nУспешных тестов: {len(successful)}/{len(results)}")
    logger.info(f"Провалившихся: {len(failed)}/{len(results)}")
    
    if successful:
        logger.info("\n" + "-"*80)
        logger.info("УСПЕШНЫЕ МОДЕЛИ (отсортированы по качеству):")
        logger.info("-"*80)
        
        # Сортировать по quality_score
        successful_sorted = sorted(
            successful,
            key=lambda x: x["quality_score"],
            reverse=True
        )
        
        for i, result in enumerate(successful_sorted, 1):
            logger.info(f"\n{i}. {result['model_name']}")
            logger.info(f"   Качество: {result['quality_score']:.2f}/1.0")
            logger.info(f"   Время ответа: {result['response_time']:.2f}с")
            logger.info(f"   Токенов: {result['tokens_generated']}")
            if result.get('response_preview'):
                logger.info(f"   Ответ: {result['response_preview']}...")
    
    if failed:
        logger.info("\n" + "-"*80)
        logger.info("ПРОВАЛИВШИЕСЯ МОДЕЛИ:")
        logger.info("-"*80)
        for result in failed:
            logger.info(f"  - {result['model_name']}: {result.get('error', 'Unknown error')}")
    
    # Проверить выбор лучшей модели
    logger.info("\n" + "-"*80)
    logger.info("ВЫБОР ЛУЧШЕЙ МОДЕЛИ:")
    logger.info("-"*80)
    
    best_model = benchmark_service.get_best_model_for_task(
        server=server_10_39,
        task_type=TaskType.PLANNING
    )
    
    if best_model:
        logger.info(f"✓ Выбрана лучшая модель: {best_model.model_name}")
        if best_model.details and "avg_quality_score" in best_model.details:
            quality = best_model.details["avg_quality_score"].get("planning", 0)
            time_avg = best_model.details["avg_response_time"].get("planning", 0)
            logger.info(f"  Среднее качество: {quality:.2f}")
            logger.info(f"  Среднее время: {time_avg:.2f}с")
    else:
        logger.warning("Не удалось выбрать лучшую модель")
    
    # Проверки
    assert len(results) > 0, "Должен быть хотя бы один результат"
    assert len(successful) > 0, "Должна быть хотя бы одна успешная модель"
    
    logger.info("\n" + "="*80)
    logger.info("БЕНЧМАРК ЗАВЕРШЕН")
    logger.info("="*80)


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(600)
async def test_benchmark_all_models_code_generation(db):
    """
    Реальный бенчмарк всех моделей на задаче генерации кода
    """
    logger.info("\n" + "="*80)
    logger.info("НАЧАЛО БЕНЧМАРКА МОДЕЛЕЙ: Code Generation Task")
    logger.info("="*80)
    
    servers = OllamaService.get_all_active_servers(db)
    server_10_39 = None
    for s in servers:
        if "10.39.0.6" in s.url:
            server_10_39 = s
            break
    
    if not server_10_39:
        pytest.skip("Сервер 10.39.0.6 не найден")
    
    benchmark_service = ModelBenchmarkService(db)
    
    results = await benchmark_service.benchmark_all_models(
        server=server_10_39,
        task_type=TaskType.CODE_GENERATION,
        timeout=30
    )
    
    successful = [r for r in results if r["success"]]
    
    logger.info(f"\nУспешных тестов: {len(successful)}/{len(results)}")
    
    if successful:
        successful_sorted = sorted(
            successful,
            key=lambda x: x["quality_score"],
            reverse=True
        )
        
        logger.info("\nТОП-3 МОДЕЛИ ДЛЯ CODE GENERATION:")
        for i, result in enumerate(successful_sorted[:3], 1):
            logger.info(f"{i}. {result['model_name']} (качество: {result['quality_score']:.2f})")
    
    assert len(successful) > 0

