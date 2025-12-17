"""
Prompt Manager - менеджер промптов для оркестратора
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import time
import random

from app.core.execution_context import ExecutionContext
from app.services.prompt_service import PromptService
from app.models.prompt import Prompt, PromptType, PromptStatus
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PromptUsage:
    """Информация об использовании промпта"""
    
    def __init__(
        self,
        prompt_id: UUID,
        stage: str,
        start_time: float,
        success: Optional[bool] = None,
        execution_time_ms: Optional[float] = None
    ):
        self.prompt_id = prompt_id
        self.stage = stage
        self.start_time = start_time
        self.success = success
        self.execution_time_ms = execution_time_ms


class PromptManager:
    """
    Менеджер промптов для оркестратора
    
    Управляет жизненным циклом промптов в рамках запроса:
    - Получение активных промптов для каждого этапа
    - Отслеживание использования промптов
    - Автоматическая запись метрик
    - Автоматический анализ производительности
    - Автоматическое создание улучшенных версий
    - A/B тестирование версий
    """
    
    # Маппинг этапов на типы промптов
    STAGE_PROMPT_MAPPING = {
        "planning": PromptType.SYSTEM,
        "execution": PromptType.SYSTEM,
        "reflection": PromptType.META,
        "analysis": PromptType.SYSTEM,
        "code_generation": PromptType.SYSTEM
    }
    
    # Маппинг этапов на имена промптов
    STAGE_NAME_MAPPING = {
        "planning": "task_analysis",
        "execution": "execution",
        "reflection": "reflection",
        "analysis": "task_analysis",
        "code_generation": "code_generation"
    }
    
    def __init__(self, context: ExecutionContext):
        """
        Инициализация PromptManager
        
        Args:
            context: ExecutionContext
        """
        self.context = context
        self.prompt_service = PromptService(context.db)
        self._usage_tracking: List[PromptUsage] = []
        self._ab_testing_enabled = True
        self._ab_testing_ratio = 0.1  # 10% запросов для TESTING версий
    
    async def get_prompt_for_stage(
        self,
        stage: str,
        prompt_name: Optional[str] = None
    ) -> Optional[Prompt]:
        """
        Получить активный промпт для этапа
        
        Args:
            stage: Этап выполнения (planning, execution, reflection, etc.)
            prompt_name: Опциональное имя промпта (если не указано, используется маппинг)
            
        Returns:
            Prompt или None если не найден
        """
        # Определить тип промпта
        prompt_type = self.STAGE_PROMPT_MAPPING.get(stage, PromptType.SYSTEM)
        
        # Определить имя промпта
        if not prompt_name:
            prompt_name = self.STAGE_NAME_MAPPING.get(stage, "system")
        
        # Получить промпт
        # First try to resolve runtime assignments via PromptRuntimeSelector (experiment/agent/global)
        try:
            from app.services.prompt_runtime_selector import PromptRuntimeSelector
            selector = PromptRuntimeSelector(self.context.db)
            resolved = selector.resolve(component_role=stage, context_metadata=getattr(self.context, "metadata", None), task_type=stage)
            if resolved and resolved.get("prompt_text"):
                # Build a lightweight Prompt-like object for compatibility
                class _P:
                    def __init__(self, id, prompt_text, version):
                        self.id = id
                        self.prompt_text = prompt_text
                        self.version = version
                prompt = _P(resolved.get("prompt_id"), resolved.get("prompt_text"), resolved.get("prompt_version"))
                return prompt
        except Exception:
            # Fallback to DB lookup if runtime selector fails
            pass

        prompt = self.prompt_service.get_active_prompt(
            name=prompt_name,
            prompt_type=prompt_type,
            level=0
        )
        
        if prompt:
            logger.debug(
                f"Retrieved prompt for stage {stage}",
                extra={
                    "prompt_id": str(prompt.id),
                    "prompt_name": prompt.name,
                    "stage": stage,
                    "workflow_id": self.context.workflow_id
                }
            )
        else:
            logger.warning(
                f"Prompt not found for stage {stage}",
                extra={"stage": stage, "prompt_name": prompt_name}
            )
        
        return prompt
    
    async def get_prompt_with_ab_testing(
        self,
        stage: str,
        prompt_name: Optional[str] = None
    ) -> Optional[Prompt]:
        """
        Получить промпт с A/B тестированием
        
        С вероятностью ab_testing_ratio возвращает TESTING версию,
        иначе возвращает ACTIVE версию.
        
        Args:
            stage: Этап выполнения
            prompt_name: Опциональное имя промпта
            
        Returns:
            Prompt (ACTIVE или TESTING версия)
        """
        # Сначала получаем ACTIVE версию
        active_prompt = await self.get_prompt_for_stage(stage, prompt_name)
        
        if not active_prompt:
            return None
        
        # Если A/B тестирование отключено, возвращаем ACTIVE
        if not self._ab_testing_enabled:
            return active_prompt
        
        # Проверяем, есть ли TESTING версии
        all_prompts = self.prompt_service.list_prompts(
            prompt_type=PromptType(active_prompt.prompt_type),
            name_search=active_prompt.name
        )
        
        testing_versions = [
            p for p in all_prompts
            if p.status == PromptStatus.TESTING.value.lower() and p.name == active_prompt.name
        ]
        
        if not testing_versions:
            # Нет TESTING версий, возвращаем ACTIVE
            return active_prompt
        
        # Выбираем последнюю TESTING версию
        testing_prompt = max(testing_versions, key=lambda p: p.version)
        
        # Решаем, использовать ли TESTING версию
        use_testing = random.random() < self._ab_testing_ratio
        
        if use_testing:
            logger.info(
                f"Using TESTING version for A/B testing",
                extra={
                    "prompt_name": active_prompt.name,
                    "active_version": active_prompt.version,
                    "testing_version": testing_prompt.version,
                    "stage": stage,
                    "workflow_id": self.context.workflow_id
                }
            )
            return testing_prompt
        else:
            return active_prompt
    
    async def record_prompt_usage(
        self,
        prompt_id: UUID,
        success: bool,
        execution_time_ms: float,
        stage: Optional[str] = None
    ) -> None:
        """
        Записать использование промпта
        
        Args:
            prompt_id: ID промпта
            success: Успешно ли использован
            execution_time_ms: Время выполнения в миллисекундах
            stage: Этап выполнения
        """
        try:
            # Записать метрики использования
            self.prompt_service.record_usage(
                prompt_id=prompt_id,
                execution_time_ms=execution_time_ms
            )
            
            # Записать успех/неудачу
            if success:
                self.prompt_service.record_success(prompt_id)
            else:
                self.prompt_service.record_failure(prompt_id)
            
            # Сохранить в трекинг
            usage = PromptUsage(
                prompt_id=prompt_id,
                stage=stage or "unknown",
                start_time=time.time(),
                success=success,
                execution_time_ms=execution_time_ms
            )
            self._usage_tracking.append(usage)
            
            logger.debug(
                f"Recorded prompt usage",
                extra={
                    "prompt_id": str(prompt_id),
                    "success": success,
                    "execution_time_ms": execution_time_ms,
                    "stage": stage,
                    "workflow_id": self.context.workflow_id
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to record prompt usage: {e}",
                exc_info=True,
                extra={"prompt_id": str(prompt_id)}
            )
    
    async def analyze_and_improve_prompts(self) -> Dict[str, Any]:
        """
        Анализировать производительность промптов и создавать улучшенные версии при необходимости
        
        Returns:
            Словарь с результатами анализа
        """
        results = {
            "analyzed": 0,
            "improved": 0,
            "improvements": []
        }
        
        try:
            # Анализируем все использованные промпты
            analyzed_prompt_ids = set()
            
            for usage in self._usage_tracking:
                if usage.prompt_id in analyzed_prompt_ids:
                    continue
                
                analyzed_prompt_ids.add(usage.prompt_id)
                results["analyzed"] += 1
                
                # Получить промпт
                prompt = self.prompt_service.get_prompt(usage.prompt_id)
                if not prompt:
                    continue
                
                # Анализировать производительность
                analysis = await self.prompt_service.analyze_prompt_performance(
                    prompt_id=usage.prompt_id,
                    task_description=f"Stage: {usage.stage}",
                    result="success" if usage.success else "failure",
                    success=usage.success,
                    execution_metadata={
                        "stage": usage.stage,
                        "execution_time_ms": usage.execution_time_ms,
                        "workflow_id": self.context.workflow_id
                    }
                )
                
                # Проверить, нужно ли создавать улучшенную версию
                if prompt.success_rate is not None and prompt.success_rate < 0.5:
                    # Низкая производительность - создать улучшенную версию
                    improved_version = await self.prompt_service.auto_create_improved_version_if_needed(
                        prompt_id=usage.prompt_id,
                        success_rate_threshold=0.5,
                        execution_time_threshold_ms=10000.0
                    )
                    
                    if improved_version:
                        results["improved"] += 1
                        results["improvements"].append({
                            "prompt_id": str(usage.prompt_id),
                            "prompt_name": prompt.name,
                            "old_version": prompt.version,
                            "new_version": improved_version.version,
                            "reason": f"Low success rate: {prompt.success_rate:.1%}"
                        })
                        
                        logger.info(
                            f"Created improved version for prompt {prompt.name}",
                            extra={
                                "prompt_id": str(usage.prompt_id),
                                "old_version": prompt.version,
                                "new_version": improved_version.version
                            }
                        )
                
                elif prompt.avg_execution_time is not None and prompt.avg_execution_time > 10000.0:
                    # Высокое время выполнения - создать улучшенную версию
                    improved_version = await self.prompt_service.auto_create_improved_version_if_needed(
                        prompt_id=usage.prompt_id,
                        success_rate_threshold=0.5,
                        execution_time_threshold_ms=10000.0
                    )
                    
                    if improved_version:
                        results["improved"] += 1
                        results["improvements"].append({
                            "prompt_id": str(usage.prompt_id),
                            "prompt_name": prompt.name,
                            "old_version": prompt.version,
                            "new_version": improved_version.version,
                            "reason": f"High execution time: {prompt.avg_execution_time/1000:.1f}s"
                        })
            
            logger.info(
                f"Analyzed {results['analyzed']} prompts, created {results['improved']} improved versions",
                extra={
                    "workflow_id": self.context.workflow_id,
                    "results": results
                }
            )
            
        except Exception as e:
            logger.error(
                f"Error analyzing and improving prompts: {e}",
                exc_info=True,
                extra={"workflow_id": self.context.workflow_id}
            )
        
        return results
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Получить сводку использования промптов
        
        Returns:
            Словарь со сводкой
        """
        if not self._usage_tracking:
            return {"total_usage": 0, "by_stage": {}, "by_success": {"success": 0, "failure": 0}}
        
        by_stage = {}
        success_count = 0
        failure_count = 0
        
        for usage in self._usage_tracking:
            # По этапам
            if usage.stage not in by_stage:
                by_stage[usage.stage] = {"count": 0, "avg_time_ms": 0.0, "times": []}
            by_stage[usage.stage]["count"] += 1
            if usage.execution_time_ms:
                by_stage[usage.stage]["times"].append(usage.execution_time_ms)
            
            # По успеху
            if usage.success is True:
                success_count += 1
            elif usage.success is False:
                failure_count += 1
        
        # Вычислить средние времена
        for stage_data in by_stage.values():
            if stage_data["times"]:
                stage_data["avg_time_ms"] = sum(stage_data["times"]) / len(stage_data["times"])
            del stage_data["times"]
        
        return {
            "total_usage": len(self._usage_tracking),
            "by_stage": by_stage,
            "by_success": {
                "success": success_count,
                "failure": failure_count
            }
        }
