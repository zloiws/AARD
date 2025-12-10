"""
Service for benchmarking and testing LLM models
Тестирование моделей для реального выбора на основе производительности
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.ollama_client import OllamaClient, TaskType
from app.models.ollama_model import OllamaModel
from app.models.ollama_server import OllamaServer
from app.services.ollama_service import OllamaService
from app.core.logging_config import LoggingConfig
from app.core.config import get_settings

logger = LoggingConfig.get_logger(__name__)
settings = get_settings()


class ModelBenchmarkService:
    """
    Service for benchmarking LLM models
    
    Тестирует модели на реальных задачах и сохраняет результаты
    для использования в выборе моделей
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = OllamaClient()
    
    async def benchmark_model(
        self,
        model: OllamaModel,
        server: OllamaServer,
        task_type: TaskType = TaskType.PLANNING,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Бенчмарк одной модели на задаче
        
        Args:
            model: Модель для тестирования
            server: Сервер с моделью
            task_type: Тип задачи (PLANNING, CODE_GENERATION)
            timeout: Таймаут в секундах
            
        Returns:
            Результаты бенчмарка:
            {
                "model_id": str,
                "model_name": str,
                "task_type": str,
                "success": bool,
                "response_time": float,
                "tokens_generated": int,
                "quality_score": float,
                "error": str | None
            }
        """
        server_url = server.get_api_url()
        
        # Тестовые промпты для разных типов задач
        test_prompts = {
            TaskType.PLANNING: "Составь план из 3 шагов для задачи: написать функцию на Python, которая возвращает 'Привет, мир!'",
            TaskType.CODE_GENERATION: "Напиши функцию на Python, которая возвращает строку 'Привет, мир!'",
        }
        
        prompt = test_prompts.get(task_type, test_prompts[TaskType.PLANNING])
        
        start_time = time.time()
        success = False
        response_time = 0.0
        tokens_generated = 0
        quality_score = 0.0
        error = None
        response_text = ""
        
        try:
            # Выполнить запрос с таймаутом
            response = await asyncio.wait_for(
                self.ollama_client.generate(
                    prompt=prompt,
                    task_type=task_type,
                    model=model.model_name,
                    server_url=server_url,
                    num_predict=200  # Ограничение для быстрого теста
                ),
                timeout=timeout
            )
            
            response_time = time.time() - start_time
            response_text = response.response if hasattr(response, 'response') else str(response)
            
            # Подсчитать токены (приблизительно)
            tokens_generated = len(response_text.split()) * 1.3  # Примерная оценка
            
            # Оценить качество ответа
            quality_score = self._evaluate_response_quality(
                response_text, 
                task_type
            )
            
            success = True
            
            logger.info(
                f"Benchmark успешен: {model.model_name}",
                extra={
                    "model_id": str(model.id),
                    "model_name": model.model_name,
                    "task_type": task_type.value,
                    "response_time": response_time,
                    "quality_score": quality_score
                }
            )
            
        except asyncio.TimeoutError:
            response_time = timeout
            error = f"Timeout after {timeout}s"
            logger.warning(
                f"Benchmark timeout: {model.model_name}",
                extra={"model_id": str(model.id), "timeout": timeout}
            )
        except Exception as e:
            response_time = time.time() - start_time
            error = str(e)
            logger.error(
                f"Benchmark error: {model.model_name}",
                exc_info=True,
                extra={"model_id": str(model.id), "error": str(e)}
            )
        
        return {
            "model_id": str(model.id),
            "model_name": model.model_name,
            "task_type": task_type.value,
            "success": success,
            "response_time": response_time,
            "tokens_generated": int(tokens_generated),
            "quality_score": quality_score,
            "error": error,
            "response_preview": response_text[:100] if response_text else None
        }
    
    def _evaluate_response_quality(
        self,
        response: str,
        task_type: TaskType
    ) -> float:
        """
        Оценить качество ответа (0.0 - 1.0)
        
        Простая эвристика на основе содержания ответа
        """
        if not response or len(response.strip()) < 10:
            return 0.0
        
        score = 0.5  # Базовый балл за наличие ответа
        
        # Проверки для planning
        if task_type == TaskType.PLANNING:
            if any(word in response.lower() for word in ["шаг", "план", "этап", "step", "plan"]):
                score += 0.2
            if any(word in response.lower() for word in ["функция", "function", "python", "код"]):
                score += 0.2
            if len(response) > 50:  # Достаточно подробный ответ
                score += 0.1
        
        # Проверки для code generation
        elif task_type == TaskType.CODE_GENERATION:
            if "def " in response or "function" in response.lower():
                score += 0.2
            if "return" in response.lower():
                score += 0.2
            if "привет" in response.lower() or "hello" in response.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    async def benchmark_all_models(
        self,
        server: OllamaServer,
        task_type: TaskType = TaskType.PLANNING,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Протестировать все активные модели на сервере
        
        Args:
            server: Сервер для тестирования
            task_type: Тип задачи
            timeout: Таймаут для каждого теста
            
        Returns:
            Список результатов бенчмарков
        """
        models = OllamaService.get_models_for_server(self.db, str(server.id))
        
        # Фильтровать embedding модели
        from app.core.model_selector import ModelSelector
        model_selector = ModelSelector(self.db)
        models = model_selector._filter_embedding_models(models)
        
        logger.info(
            f"Начинаем бенчмарк {len(models)} моделей на сервере {server.name}",
            extra={
                "server_id": str(server.id),
                "server_name": server.name,
                "task_type": task_type.value,
                "models_count": len(models)
            }
        )
        
        results = []
        
        for i, model in enumerate(models, 1):
            logger.info(f"Тестируем модель {i}/{len(models)}: {model.model_name}")
            
            result = await self.benchmark_model(
                model=model,
                server=server,
                task_type=task_type,
                timeout=timeout
            )
            
            results.append(result)
            
            # Небольшая задержка между тестами
            if i < len(models):
                await asyncio.sleep(1)
        
        # Сохранить результаты в метаданные моделей
        self._save_benchmark_results(models, results, task_type)
        
        return results
    
    def _save_benchmark_results(
        self,
        models: List[OllamaModel],
        results: List[Dict[str, Any]],
        task_type: TaskType
    ):
        """
        Сохранить результаты бенчмарка в метаданные моделей
        """
        for model, result in zip(models, results):
            if not model.details:
                model.details = {}
            
            if "benchmarks" not in model.details:
                model.details["benchmarks"] = {}
            
            benchmark_key = f"{task_type.value}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            model.details["benchmarks"][benchmark_key] = {
                "success": result["success"],
                "response_time": result["response_time"],
                "quality_score": result["quality_score"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Обновить средние показатели
            if "avg_response_time" not in model.details:
                model.details["avg_response_time"] = {}
            if "avg_quality_score" not in model.details:
                model.details["avg_quality_score"] = {}
            
            task_key = task_type.value
            if result["success"]:
                # Обновить средние значения
                if task_key in model.details["avg_response_time"]:
                    # Взвешенное среднее
                    old_avg = model.details["avg_response_time"][task_key]
                    old_count = model.details.get("benchmark_count", {}).get(task_key, 1)
                    new_avg = (old_avg * old_count + result["response_time"]) / (old_count + 1)
                    model.details["avg_response_time"][task_key] = new_avg
                    model.details["avg_quality_score"][task_key] = (
                        model.details["avg_quality_score"].get(task_key, 0) * old_count + result["quality_score"]
                    ) / (old_count + 1)
                    model.details.setdefault("benchmark_count", {})[task_key] = old_count + 1
                else:
                    model.details["avg_response_time"][task_key] = result["response_time"]
                    model.details["avg_quality_score"][task_key] = result["quality_score"]
                    model.details.setdefault("benchmark_count", {})[task_key] = 1
        
        self.db.commit()
        
        logger.info(f"Сохранены результаты бенчмарка для {len(results)} моделей")
    
    def get_best_model_for_task(
        self,
        server: OllamaServer,
        task_type: TaskType
    ) -> Optional[OllamaModel]:
        """
        Выбрать лучшую модель для задачи на основе результатов бенчмарков
        
        Args:
            server: Сервер для поиска
            task_type: Тип задачи
            
        Returns:
            Лучшая модель или None
        """
        models = OllamaService.get_models_for_server(self.db, str(server.id))
        
        # Фильтровать embedding
        from app.core.model_selector import ModelSelector
        model_selector = ModelSelector(self.db)
        models = model_selector._filter_embedding_models(models)
        
        if not models:
            return None
        
        best_model = None
        best_score = -1.0
        
        task_key = task_type.value
        
        for model in models:
            if not model.details or "avg_quality_score" not in model.details:
                continue
            
            quality_score = model.details["avg_quality_score"].get(task_key, 0)
            response_time = model.details["avg_response_time"].get(task_key, float('inf'))
            
            # Комбинированный score: качество / время (чем быстрее и качественнее, тем лучше)
            if response_time > 0:
                combined_score = quality_score / (response_time / 10.0)  # Нормализация времени
            else:
                combined_score = quality_score
            
            if combined_score > best_score:
                best_score = combined_score
                best_model = model
        
        # Если нет результатов бенчмарков, вернуть первую модель
        if not best_model:
            best_model = models[0]
            logger.warning(
                f"Нет результатов бенчмарков, используем первую модель: {best_model.model_name}"
            )
        
        return best_model

