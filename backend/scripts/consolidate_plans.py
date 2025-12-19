"""
Скрипт для консолидации всех планов проекта
Собирает планы из файлов и БД, анализирует их, проверяет выполнение и генерирует единый план
"""
import asyncio
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.core.ollama_client import OllamaClient, TaskType
from app.models.plan import Plan
from app.models.task import Task, TaskStatus

logger = LoggingConfig.get_logger(__name__)


class PlanConsolidator:
    """Класс для консолидации всех планов проекта"""
    
    def __init__(self):
        self.project_root = backend_dir.parent
        self.plans_dir = self.project_root / ".cursor" / "plans"
        self.archive_dir = self.project_root / "docs" / "archive"
        self.backend_dir = self.project_root / "backend"
        self.ollama_client = OllamaClient()
        self.all_tasks = []
        self.all_plans = []
        
    def collect_file_plans(self) -> List[Dict]:
        """Собрать все планы из файлов"""
        plans = []
        
        # Планы из .cursor/plans/
        if self.plans_dir.exists():
            for plan_file in self.plans_dir.glob("*.md"):
                try:
                    content = plan_file.read_text(encoding="utf-8")
                    plans.append({
                        "source": "cursor_plans",
                        "file": str(plan_file.relative_to(self.project_root)),
                        "content": content,
                        "name": plan_file.stem,
                        "size": len(content),
                        "modified": datetime.fromtimestamp(plan_file.stat().st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Ошибка чтения {plan_file}: {e}")
        
        # Планы из docs/archive/ (только файлы с PLAN/ROADMAP в названии)
        if self.archive_dir.exists():
            for plan_file in self.archive_dir.glob("*.md"):
                if any(keyword in plan_file.name.upper() for keyword in ["PLAN", "ROADMAP", "ROAD"]):
                    try:
                        content = plan_file.read_text(encoding="utf-8")
                        plans.append({
                            "source": "archive",
                            "file": str(plan_file.relative_to(self.project_root)),
                            "content": content,
                            "name": plan_file.stem,
                            "size": len(content),
                            "modified": datetime.fromtimestamp(plan_file.stat().st_mtime).isoformat()
                        })
                    except Exception as e:
                        logger.warning(f"Ошибка чтения {plan_file}: {e}")
        
        return plans
    
    def collect_db_plans(self) -> List[Dict]:
        """Собрать все планы из БД"""
        db = SessionLocal()
        try:
            plans = db.query(Plan).order_by(Plan.created_at.desc()).all()
            return [{
                "source": "database",
                "id": str(p.id),
                "task_id": str(p.task_id) if p.task_id else None,
                "version": p.version,
                "goal": p.goal,
                "strategy": p.strategy,
                "steps": p.steps,
                "alternatives": p.alternatives,
                "status": p.status,
                "current_step": p.current_step,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            } for p in plans]
        except Exception as e:
            logger.error(f"Ошибка получения планов из БД: {e}")
            return []
        finally:
            db.close()
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Вычислить схожесть двух текстов (простая метрика)"""
        # Нормализовать тексты
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        # Если тексты идентичны
        if text1_lower == text2_lower:
            return 1.0
        
        # Вычислить пересечение слов
        words1 = set(re.findall(r'\w+', text1_lower))
        words2 = set(re.findall(r'\w+', text2_lower))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        # Jaccard similarity
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Проверка на подстроку
        if text1_lower in text2_lower or text2_lower in text1_lower:
            substring_bonus = 0.3
        else:
            substring_bonus = 0.0
        
        return min(jaccard + substring_bonus, 1.0)
    
    def deduplicate_tasks(self, tasks: List[Dict], similarity_threshold: float = 0.7) -> List[Dict]:
        """Дедуплицировать задачи с похожим текстом"""
        if not tasks:
            return tasks
        
        # Группировать похожие задачи
        task_groups = []
        processed = set()
        
        for i, task1 in enumerate(tasks):
            if i in processed:
                continue
            
            # Найти похожие задачи
            similar_tasks = [task1]
            similar_indices = [i]
            
            for j, task2 in enumerate(tasks[i+1:], start=i+1):
                if j in processed:
                    continue
                
                similarity = self.calculate_text_similarity(
                    task1.get('text', ''),
                    task2.get('text', '')
                )
                
                if similarity >= similarity_threshold:
                    similar_tasks.append(task2)
                    similar_indices.append(j)
            
            # Объединить похожие задачи
            if len(similar_tasks) > 1:
                # Выбрать задачу с наибольшим completion_score как основную
                main_task = max(similar_tasks, key=lambda t: t.get('completion', {}).get('completion_score', 0))
                
                # Объединить источники
                all_sources = list(set(t.get('plan_source', 'unknown') for t in similar_tasks))
                main_task['plan_source'] = ', '.join(all_sources)
                main_task['merged_from'] = [t.get('id') for t in similar_tasks if t.get('id') != main_task.get('id')]
                main_task['is_merged'] = True
                main_task['merge_count'] = len(similar_tasks)
                
                task_groups.append(main_task)
                processed.update(similar_indices)
            else:
                task_groups.append(task1)
                processed.add(i)
        
        logger.info(f"Дедупликация: {len(tasks)} -> {len(task_groups)} задач")
        return task_groups
    
    def categorize_task(self, task_text: str) -> Dict[str, str]:
        """Определить категорию и сложность задачи"""
        task_lower = task_text.lower()
        
        # Определить тип задачи
        task_type = "feature"
        if any(word in task_lower for word in ['исправить', 'fix', 'bug', 'ошибка', 'error']):
            task_type = "bugfix"
        elif any(word in task_lower for word in ['рефакторинг', 'refactor', 'улучшить', 'improve', 'оптимизировать']):
            task_type = "refactoring"
        elif any(word in task_lower for word in ['документация', 'documentation', 'docs', 'guide', 'readme']):
            task_type = "documentation"
        elif any(word in task_lower for word in ['исследование', 'research', 'эксперимент', 'experiment', 'прототип']):
            task_type = "research"
        
        # Определить сложность
        complexity = "medium"
        simple_keywords = ['добавить', 'создать', 'добавь', 'create', 'add', 'simple', 'простой']
        complex_keywords = ['реализовать', 'разработать', 'архитектура', 'система', 'интеграция', 'implement', 'develop', 'architecture', 'system']
        
        simple_count = sum(1 for kw in simple_keywords if kw in task_lower)
        complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
        
        if simple_count > complex_count and len(task_text) < 100:
            complexity = "simple"
        elif complex_count > simple_count or len(task_text) > 200:
            complexity = "complex"
        
        # Оценка времени (в часах)
        estimated_hours = 4  # по умолчанию
        if complexity == "simple":
            estimated_hours = 1
        elif complexity == "medium":
            estimated_hours = 4
        else:
            estimated_hours = 8
        
        return {
            "type": task_type,
            "complexity": complexity,
            "estimated_hours": estimated_hours
        }
    
    def parse_tasks_from_markdown(self, content: str, plan_name: str) -> List[Dict]:
        """Парсить задачи из markdown"""
        tasks = []
        lines = content.split('\n')
        
        current_section = None
        current_subsection = None
        task_counter = 0
        
        for i, line in enumerate(lines):
            # Определить секцию (##)
            if line.startswith('##') and not line.startswith('###'):
                current_section = line.strip('#').strip()
                current_subsection = None
            # Определить подсекцию (###)
            elif line.startswith('###'):
                current_subsection = line.strip('#').strip()
            
            # Найти задачи с чекбоксами [x] или [ ]
            checkbox_match = re.match(r'^[-*]\s*\[([ xX])\]\s*(.+)', line)
            if checkbox_match:
                is_done = checkbox_match.group(1).lower() == 'x'
                task_text = checkbox_match.group(2).strip()
                task_counter += 1
                
                # Категоризировать задачу
                category_info = self.categorize_task(task_text)
                
                tasks.append({
                    "id": f"{plan_name}_task_{task_counter}",
                    "section": current_section,
                    "subsection": current_subsection,
                    "text": task_text,
                    "status": "done" if is_done else "todo",
                    "line_number": i + 1,
                    "plan_source": plan_name,
                    "task_type": category_info["type"],
                    "complexity": category_info["complexity"],
                    "estimated_hours": category_info["estimated_hours"]
                })
            
            # Найти задачи без чекбоксов (пронумерованные списки или просто пункты)
            elif re.match(r'^\d+\.\s+(.+)', line) or re.match(r'^[-*]\s+(.+)', line):
                # Проверить, что это не заголовок и не пустая строка
                task_text = re.sub(r'^\d+\.\s+', '', line).strip()
                task_text = re.sub(r'^[-*]\s+', '', task_text).strip()
                
                if task_text and not task_text.startswith('#') and len(task_text) > 10:
                    # Проверить, не является ли это уже обработанной задачей
                    if not any(t['text'] == task_text for t in tasks):
                        task_counter += 1
                        # Категоризировать задачу
                        category_info = self.categorize_task(task_text)
                        
                        tasks.append({
                            "id": f"{plan_name}_task_{task_counter}",
                            "section": current_section,
                            "subsection": current_subsection,
                            "text": task_text,
                            "status": "unknown",
                            "line_number": i + 1,
                            "plan_source": plan_name,
                            "task_type": category_info["type"],
                            "complexity": category_info["complexity"],
                            "estimated_hours": category_info["estimated_hours"]
                        })
        
        return tasks
    
    def check_file_exists(self, file_path: str) -> bool:
        """Проверить существование файла"""
        # Попробовать разные варианты путей
        paths_to_check = [
            self.backend_dir / file_path,
            self.project_root / file_path,
            self.backend_dir / "app" / file_path,
        ]
        
        for path in paths_to_check:
            if path.exists():
                return True
        return False
    
    def check_class_exists(self, class_name: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Проверить существование класса и его ключевых методов"""
        result = {
            "exists": False,
            "file": None,
            "methods": [],
            "has_key_methods": False
        }
        
        if file_path:
            full_path = self.backend_dir / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    pattern = rf'class\s+{re.escape(class_name)}\s*[\(:]'
                    if re.search(pattern, content):
                        result["exists"] = True
                        result["file"] = str(full_path.relative_to(self.backend_dir))
                        # Найти методы класса
                        class_start = content.find(f"class {class_name}")
                        if class_start != -1:
                            # Найти конец класса (следующий класс или конец файла)
                            next_class = content.find("\nclass ", class_start + 1)
                            class_content = content[class_start:next_class] if next_class != -1 else content[class_start:]
                            # Найти все методы
                            method_pattern = r'def\s+(\w+)\s*\('
                            methods = re.findall(method_pattern, class_content)
                            result["methods"] = methods
                            # Проверить наличие ключевых методов (async def, def с определенными именами)
                            key_methods = ['generate', 'execute', 'create', 'update', 'delete', 'get', 'save', 'load']
                            result["has_key_methods"] = any(m in methods for m in key_methods)
                        return result
                except:
                    pass
        
        # Поиск по всему проекту
        for py_file in self.backend_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                pattern = rf'class\s+{re.escape(class_name)}\s*[\(:]'
                if re.search(pattern, content):
                    result["exists"] = True
                    result["file"] = str(py_file.relative_to(self.backend_dir))
                    # Найти методы класса
                    class_start = content.find(f"class {class_name}")
                    if class_start != -1:
                        next_class = content.find("\nclass ", class_start + 1)
                        class_content = content[class_start:next_class] if next_class != -1 else content[class_start:]
                        method_pattern = r'def\s+(\w+)\s*\('
                        methods = re.findall(method_pattern, class_content)
                        result["methods"] = methods
                        key_methods = ['generate', 'execute', 'create', 'update', 'delete', 'get', 'save', 'load']
                        result["has_key_methods"] = any(m in methods for m in key_methods)
                    return result
            except:
                continue
        
        return result
    
    def check_migration_exists(self, migration_name: str) -> bool:
        """Проверить существование миграции"""
        migrations_dir = self.backend_dir / "alembic" / "versions"
        if not migrations_dir.exists():
            return False
        
        # Искать по части имени или номеру ревизии
        migration_name_lower = migration_name.lower()
        for migration_file in migrations_dir.glob("*.py"):
            file_name_lower = migration_file.name.lower()
            # Проверка по имени или номеру ревизии (например, "017" или "017_extend")
            if migration_name_lower in file_name_lower:
                return True
            # Проверка по номеру ревизии в начале файла
            try:
                content = migration_file.read_text(encoding="utf-8")
                # Искать revision ID в файле
                revision_match = re.search(r'revision\s*:\s*str\s*=\s*[\'\"](\d+)[\'\"]', content)
                if revision_match:
                    revision_id = revision_match.group(1)
                    if revision_id in migration_name or migration_name in revision_id:
                        return True
            except:
                continue
        
        return False
    
    def check_api_endpoint_exists(self, endpoint_path: str) -> bool:
        """Проверить наличие API endpoint"""
        # Поиск в routes файлах
        routes_dir = self.backend_dir / "app" / "api" / "routes"
        if not routes_dir.exists():
            return False
        
        for route_file in routes_dir.glob("*.py"):
            try:
                content = route_file.read_text(encoding="utf-8")
                # Искать декораторы @router.get, @router.post и т.д.
                endpoint_pattern = rf'@router\.(get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']'
                matches = re.findall(endpoint_pattern, content)
                for method, path in matches:
                    if endpoint_path in path or path in endpoint_path:
                        return True
            except:
                continue
        
        return False
    
    def check_template_exists(self, template_path: str) -> bool:
        """Проверить наличие шаблона"""
        templates_dir = self.project_root / "frontend" / "templates"
        if not templates_dir.exists():
            return False
        
        # Нормализовать путь
        template_path = template_path.replace("\\\\", "/")
        if template_path.startswith("frontend/templates/"):
            template_path = template_path.replace("frontend/templates/", "")
        
        template_file = templates_dir / template_path
        return template_file.exists()
    
    def check_router_in_main(self, router_name: str) -> bool:
        """Проверить наличие роутера в main.py"""
        main_file = self.backend_dir / "main.py"
        if not main_file.exists():
            return False
        
        try:
            content = main_file.read_text(encoding="utf-8")
            # Искать импорт или использование роутера
            patterns = [
                rf'from\s+app\.api\.routes\.{re.escape(router_name)}\s+import',
                rf'import\s+{re.escape(router_name)}',
                rf'app\.include_router.*{re.escape(router_name)}'
            ]
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        except:
            pass
        
        return False
    
    def check_test_exists(self, component_name: str) -> bool:
        """Проверить наличие тестов для компонента"""
        tests_dir = self.backend_dir / "tests"
        if not tests_dir.exists():
            return False
        
        # Поиск тестовых файлов
        test_patterns = [
            f"test_{component_name.lower()}",
            f"test_{component_name.lower().replace('_service', '')}",
            component_name.lower()
        ]
        
        for test_file in tests_dir.rglob("test_*.py"):
            file_name_lower = test_file.stem.lower()
            for pattern in test_patterns:
                if pattern in file_name_lower:
                    return True
        
        return False
    
    def check_documentation_exists(self, component_name: str) -> bool:
        """Проверить наличие документации"""
        docs_dir = self.project_root / "docs"
        if not docs_dir.exists():
            return False
        
        # Поиск документации
        component_lower = component_name.lower()
        for doc_file in docs_dir.rglob("*.md"):
            file_name_lower = doc_file.stem.lower()
            if component_lower in file_name_lower or component_lower.replace("_", " ") in file_name_lower:
                return True
        
        return False
    
    def analyze_task_completion(self, task: Dict) -> Dict[str, Any]:
        """Анализировать выполнение задачи с расширенной проверкой"""
        task_text = task['text']
        completion_info = {
            "files_mentioned": [],
            "classes_mentioned": [],
            "migrations_mentioned": [],
            "endpoints_mentioned": [],
            "templates_mentioned": [],
            "files_exist": {},
            "classes_exist": {},
            "migrations_exist": {},
            "endpoints_exist": {},
            "templates_exist": {},
            "routers_in_main": {},
            "tests_exist": {},
            "docs_exist": {},
            "completion_score": 0.0,
            "completion_details": []
        }
        
        # Найти упоминания файлов
        file_patterns = re.findall(r'`([^`]+\.py)`', task_text)
        file_patterns.extend(re.findall(r'([a-z_/]+\.py)', task_text, re.IGNORECASE))
        
        for file_pattern in file_patterns:
            if file_pattern not in completion_info["files_mentioned"]:
                completion_info["files_mentioned"].append(file_pattern)
                exists = self.check_file_exists(file_pattern)
                completion_info["files_exist"][file_pattern] = exists
                if exists:
                    completion_info["completion_score"] += 0.25
                    completion_info["completion_details"].append(f"Файл {file_pattern} существует")
                    # Проверить наличие тестов для этого файла
                    component_name = Path(file_pattern).stem
                    has_tests = self.check_test_exists(component_name)
                    completion_info["tests_exist"][component_name] = has_tests
                    if has_tests:
                        completion_info["completion_score"] += 0.1
                        completion_info["completion_details"].append(f"Тесты для {component_name} найдены")
        
        # Найти упоминания классов
        class_patterns = re.findall(r'класс\s+(\w+)|class\s+(\w+)', task_text, re.IGNORECASE)
        for match in class_patterns:
            class_name = match[0] or match[1]
            if class_name and class_name not in completion_info["classes_mentioned"]:
                completion_info["classes_mentioned"].append(class_name)
                class_info = self.check_class_exists(class_name)
                completion_info["classes_exist"][class_name] = class_info
                if class_info["exists"]:
                    completion_info["completion_score"] += 0.15
                    completion_info["completion_details"].append(f"Класс {class_name} существует")
                    if class_info["has_key_methods"]:
                        completion_info["completion_score"] += 0.1
                        completion_info["completion_details"].append(f"Класс {class_name} имеет ключевые методы")
        
        # Найти упоминания миграций
        migration_patterns = re.findall(r'миграци[яи]\s+(\d+[a-z_]+)', task_text, re.IGNORECASE)
        migration_patterns.extend(re.findall(r'migration\s+(\d+[a-z_]+)', task_text, re.IGNORECASE))
        migration_patterns.extend(re.findall(r'(\d{3}_[a-z_]+)', task_text, re.IGNORECASE))  # 017_extend_task_lifecycle
        
        for migration_pattern in migration_patterns:
            if migration_pattern not in completion_info["migrations_mentioned"]:
                completion_info["migrations_mentioned"].append(migration_pattern)
                exists = self.check_migration_exists(migration_pattern)
                completion_info["migrations_exist"][migration_pattern] = exists
                if exists:
                    completion_info["completion_score"] += 0.15
                    completion_info["completion_details"].append(f"Миграция {migration_pattern} найдена")
        
        # Найти упоминания API endpoints
        endpoint_patterns = re.findall(r'/(api/[^"\'\s]+)', task_text, re.IGNORECASE)
        endpoint_patterns.extend(re.findall(r'endpoint[:\s]+([/a-z_]+)', task_text, re.IGNORECASE))
        
        for endpoint in endpoint_patterns:
            if endpoint not in completion_info["endpoints_mentioned"]:
                completion_info["endpoints_mentioned"].append(endpoint)
                exists = self.check_api_endpoint_exists(endpoint)
                completion_info["endpoints_exist"][endpoint] = exists
                if exists:
                    completion_info["completion_score"] += 0.1
                    completion_info["completion_details"].append(f"API endpoint {endpoint} найден")
        
        # Найти упоминания шаблонов
        template_patterns = re.findall(r'`([^`]+\.html)`', task_text)
        template_patterns.extend(re.findall(r'(frontend/templates/[^"\'\s]+\.html)', task_text, re.IGNORECASE))
        
        for template in template_patterns:
            if template not in completion_info["templates_mentioned"]:
                completion_info["templates_mentioned"].append(template)
                exists = self.check_template_exists(template)
                completion_info["templates_exist"][template] = exists
                if exists:
                    completion_info["completion_score"] += 0.1
                    completion_info["completion_details"].append(f"Шаблон {template} найден")
        
        # Проверить интеграцию роутеров в main.py
        router_patterns = re.findall(r'router[:\s]+([a-z_]+)', task_text, re.IGNORECASE)
        router_patterns.extend(re.findall(r'([a-z_]+_pages?|plans|approvals|artifacts)', task_text, re.IGNORECASE))
        
        for router_name in router_patterns:
            if router_name not in completion_info["routers_in_main"]:
                exists = self.check_router_in_main(router_name)
                completion_info["routers_in_main"][router_name] = exists
                if exists:
                    completion_info["completion_score"] += 0.1
                    completion_info["completion_details"].append(f"Роутер {router_name} интегрирован в main.py")
        
        # Проверить документацию
        doc_keywords = re.findall(r'документаци[яи]|docs?/|guides?/', task_text, re.IGNORECASE)
        if doc_keywords:
            # Попробовать найти название компонента для проверки документации
            for class_name in completion_info["classes_mentioned"]:
                has_docs = self.check_documentation_exists(class_name)
                completion_info["docs_exist"][class_name] = has_docs
                if has_docs:
                    completion_info["completion_score"] += 0.05
                    completion_info["completion_details"].append(f"Документация для {class_name} найдена")
        
        # Если задача помечена как выполненная в плане
        if task.get('status') == 'done':
            completion_info["completion_score"] = max(completion_info["completion_score"], 0.8)
        
        # Нормализовать score
        completion_info["completion_score"] = min(completion_info["completion_score"], 1.0)
        
        return completion_info
    
    async def analyze_with_llm(self, all_tasks: List[Dict], all_plans: List[Dict]) -> Dict[str, Any]:
        """Использовать LLM для глубокого анализа связей и приоритизации"""
        # Подготовить данные для анализа - увеличиваем лимит до 500
        tasks_summary = []
        for task in all_tasks[:500]:  # Увеличено с 100 до 500
            completion = task.get("completion", {})
            tasks_summary.append({
                "id": task.get("id", ""),
                "text": task.get("text", "")[:300],  # Увеличено с 200 до 300
                "section": task.get("section", ""),
                "status": task.get("status", ""),
                "completion_score": completion.get("completion_score", 0.0),
                "files_exist": sum(1 for v in completion.get("files_exist", {}).values() if v),
                "classes_exist": sum(1 for v in completion.get("classes_exist", {}).values() if isinstance(v, dict) and v.get("exists")),
                "has_tests": any(completion.get("tests_exist", {}).values()),
                "has_docs": any(completion.get("docs_exist", {}).values())
            })
        
        # Подготовить информацию о реализованных компонентах
        implemented_components = {
            "services": [],
            "models": [],
            "routes": [],
            "templates": []
        }
        
        # Собрать информацию о реализованных компонентах
        services_dir = self.backend_dir / "app" / "services"
        if services_dir.exists():
            for service_file in services_dir.glob("*.py"):
                if service_file.stem != "__init__":
                    implemented_components["services"].append(service_file.stem)
        
        models_dir = self.backend_dir / "app" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.py"):
                if model_file.stem != "__init__":
                    implemented_components["models"].append(model_file.stem)
        
        routes_dir = self.backend_dir / "app" / "api" / "routes"
        if routes_dir.exists():
            for route_file in routes_dir.glob("*.py"):
                if route_file.stem != "__init__":
                    implemented_components["routes"].append(route_file.stem)
        
        plans_summary = []
        for plan in all_plans[:30]:  # Увеличено с 20 до 30
            plans_summary.append({
                "name": plan.get("name", ""),
                "source": plan.get("source", ""),
                "size": plan.get("size", 0)
            })
        
        # Многоэтапный анализ: Этап 1 - Группировка и категоризация
        prompt_stage1 = f"""Ты анализируешь планы развития проекта AARD (автономная агентная система).

РЕАЛИЗОВАННЫЕ КОМПОНЕНТЫ:
Сервисы: {', '.join(implemented_components['services'][:20])}
Модели: {', '.join(implemented_components['models'][:20])}
API Routes: {', '.join(implemented_components['routes'][:20])}

СТАТИСТИКА:
- Всего планов: {len(all_plans)}
- Всего задач: {len(all_tasks)}
- Выполнено задач: {sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8)}
- В процессе: {sum(1 for t in all_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8)}
- Не начато: {sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3)}

ЗАДАЧИ ДЛЯ АНАЛИЗА:
{json.dumps(tasks_summary[:200], indent=2, ensure_ascii=False)}

ЭТАП 1: Группировка и категоризация
Сгруппируй задачи по функциональным областям и ответь в формате JSON:
{{
  "functional_areas": [
    {{
      "name": "название области (Core Infrastructure, Planning System, Execution Engine, Human-in-the-Loop, Learning & Improvement, Security & Safety, UI & UX, Agent System, Observability, Testing & Quality)",
      "description": "описание области",
      "task_ids": ["id1", "id2"],
      "priority": "high/medium/low",
      "completion_rate": 0.0-1.0
    }}
  ],
  "task_categories": [
    {{
      "task_id": "id",
      "category": "feature/bugfix/refactoring/documentation/research",
      "complexity": "simple/medium/complex",
      "estimated_hours": число
    }}
  ]
}}

Ответь ТОЛЬКО JSON, без дополнительного текста."""

        try:
            # Получить настройки для доступа к Ollama инстансам
            settings = get_settings()
            instance = settings.ollama_instance_1
            server_url = instance.url
            model = instance.model
            
            # ЭТАП 1: Группировка и категоризация
            logger.info("LLM анализ: Этап 1 - Группировка и категоризация")
            response1 = await self.ollama_client.generate(
                prompt=prompt_stage1,
                task_type=TaskType.REASONING,
                model=model,
                server_url=server_url,
                temperature=0.3
            )
            
            response_text1 = response1.response.strip()
            if response_text1.startswith("```"):
                response_text1 = re.sub(r'^```(?:json)?\s*\n', '', response_text1)
                response_text1 = re.sub(r'\n```\s*$', '', response_text1)
            
            stage1_result = json.loads(response_text1)
            
            # ЭТАП 2: Анализ зависимостей
            logger.info("LLM анализ: Этап 2 - Анализ зависимостей")
            prompt_stage2 = f"""ЭТАП 2: Анализ технических зависимостей и блокеров

РЕЗУЛЬТАТЫ ЭТАПА 1:
{json.dumps(stage1_result, indent=2, ensure_ascii=False)}

ЗАДАЧИ:
{json.dumps(tasks_summary[:300], indent=2, ensure_ascii=False)}

Проанализируй зависимости между задачами и выяви блокеры. Ответь в формате JSON:
{{
  "dependencies": [
    {{
      "task_id": "id задачи",
      "depends_on": ["id зависимых задач"],
      "reason": "техническая причина зависимости",
      "is_blocker": true/false
    }}
  ],
  "blockers": [
    {{
      "task_id": "id блокера",
      "blocks": ["id заблокированных задач"],
      "priority": "critical/high/medium"
    }}
  ],
  "critical_path": [
    "id задачи в порядке критического пути"
  ],
  "technical_debt": [
    {{
      "task_id": "id",
      "debt_type": "code_quality/architecture/testing/documentation",
      "severity": "high/medium/low",
      "description": "описание технического долга"
    }}
  ]
}}

Ответь ТОЛЬКО JSON, без дополнительного текста."""
            
            response2 = await self.ollama_client.generate(
                prompt=prompt_stage2,
                task_type=TaskType.REASONING,
                model=model,
                server_url=server_url,
                temperature=0.3
            )
            
            response_text2 = response2.response.strip()
            if response_text2.startswith("```"):
                response_text2 = re.sub(r'^```(?:json)?\s*\n', '', response_text2)
                response_text2 = re.sub(r'\n```\s*$', '', response_text2)
            
            stage2_result = json.loads(response_text2)
            
            # ЭТАП 3: Приоритизация и рекомендации
            logger.info("LLM анализ: Этап 3 - Приоритизация и рекомендации")
            prompt_stage3 = f"""ЭТАП 3: Приоритизация и стратегические рекомендации

РЕЗУЛЬТАТЫ ЭТАПА 1:
{json.dumps(stage1_result, indent=2, ensure_ascii=False)}

РЕЗУЛЬТАТЫ ЭТАПА 2:
{json.dumps(stage2_result, indent=2, ensure_ascii=False)}

РЕАЛИЗОВАННЫЕ КОМПОНЕНТЫ:
{json.dumps(implemented_components, indent=2, ensure_ascii=False)}

Проанализируй и создай приоритизированный roadmap. Ответь в формате JSON:
{{
  "analysis": {{
    "total_plans": {len(all_plans)},
    "total_tasks": {len(all_tasks)},
    "completed_tasks": {sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8)},
    "in_progress_tasks": {sum(1 for t in all_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8)},
    "todo_tasks": {sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3)}
  }},
  "roadmap": {{
    "immediate_goals": [
      {{
        "task_id": "id",
        "goal": "описание цели",
        "timeframe": "1-2 недели",
        "priority": "critical/high"
      }}
    ],
    "short_term_goals": [
      {{
        "task_id": "id",
        "goal": "описание цели",
        "timeframe": "1-3 месяца",
        "priority": "high/medium"
      }}
    ],
    "long_term_goals": [
      {{
        "task_id": "id",
        "goal": "описание цели",
        "timeframe": "3+ месяца",
        "priority": "medium/low"
      }}
    ]
  }},
  "recommendations": [
    {{
      "type": "architecture/priority/technical_debt/process",
      "priority": "high/medium/low",
      "description": "рекомендация",
      "impact": "описание влияния"
    }}
  ],
  "priority_order": [
    "id задачи в порядке приоритета выполнения"
  ],
  "themes": [
    {{
      "name": "название темы",
      "description": "описание",
      "tasks_count": число,
      "priority": "high/medium/low",
      "completion_rate": 0.0-1.0
    }}
  ]
}}

Ответь ТОЛЬКО JSON, без дополнительного текста."""
            
            response3 = await self.ollama_client.generate(
                prompt=prompt_stage3,
                task_type=TaskType.REASONING,
                model=model,
                server_url=server_url,
                temperature=0.3
            )
            
            response_text3 = response3.response.strip()
            if response_text3.startswith("```"):
                response_text3 = re.sub(r'^```(?:json)?\s*\n', '', response_text3)
                response_text3 = re.sub(r'\n```\s*$', '', response_text3)
            
            stage3_result = json.loads(response_text3)
            
            # Объединить результаты всех этапов
            analysis = {
                **stage3_result,
                "functional_areas": stage1_result.get("functional_areas", []),
                "task_categories": stage1_result.get("task_categories", []),
                "dependencies": stage2_result.get("dependencies", []),
                "blockers": stage2_result.get("blockers", []),
                "critical_path": stage2_result.get("critical_path", []),
                "technical_debt": stage2_result.get("technical_debt", [])
            }
            
            return analysis
        except Exception as e:
            logger.error(f"Ошибка анализа через LLM: {e}", exc_info=True)
            return {
                "analysis": {
                    "total_plans": len(all_plans),
                    "total_tasks": len(all_tasks),
                    "error": str(e)
                },
                "themes": [],
                "dependencies": [],
                "recommendations": [],
                "priority_order": [],
                "functional_areas": [],
                "task_categories": [],
                "blockers": [],
                "critical_path": [],
                "technical_debt": [],
                "roadmap": {}
            }
    
    def generate_consolidated_plan(self, all_tasks: List[Dict], all_plans: List[Dict], 
                                   llm_analysis: Dict) -> str:
        """Генерировать единый консолидированный план с улучшенной структурой"""
        output = []
        
        # Executive Summary
        output.append("# Единый консолидированный план развития AARD\n")
        output.append(f"*Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Статистика
        completed = [t for t in all_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8]
        in_progress = [t for t in all_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8]
        todo = [t for t in all_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3]
        
        total_tasks = len(all_tasks)
        completion_rate = len(completed) / total_tasks if total_tasks > 0 else 0
        
        output.append("## Executive Summary\n\n")
        output.append(f"**Всего планов проанализировано:** {len(all_plans)}\n")
        output.append(f"**Всего задач найдено:** {total_tasks}\n")
        output.append(f"**Общий прогресс:** {completion_rate:.1%}\n\n")
        
        # Прогресс-бар
        progress_bar_length = 50
        filled = int(completion_rate * progress_bar_length)
        progress_bar = "█" * filled + "░" * (progress_bar_length - filled)
        output.append(f"`{progress_bar}` {completion_rate:.1%}\n\n")
        
        output.append("### Статистика по статусам\n\n")
        output.append(f"- ✅ **Выполнено:** {len(completed)} задач ({len(completed)/total_tasks*100:.1f}%)\n")
        output.append(f"- ⏳ **В процессе:** {len(in_progress)} задач ({len(in_progress)/total_tasks*100:.1f}%)\n")
        output.append(f"- ❌ **Не начато:** {len(todo)} задач ({len(todo)/total_tasks*100:.1f}%)\n\n")
        
        # Текущий статус проекта
        output.append("## Текущий статус проекта\n\n")
        
        # Группировка задач по функциональным областям из LLM анализа
        functional_areas = llm_analysis.get("functional_areas", [])
        if functional_areas:
            output.append("### Реализованные компоненты по областям\n\n")
            for area in functional_areas:
                area_tasks = [t for t in all_tasks if t.get("id") in area.get("task_ids", [])]
                area_completed = [t for t in area_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8]
                area_rate = len(area_completed) / len(area_tasks) if area_tasks else 0
                
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(area.get("priority", "medium"), "⚪")
                output.append(f"#### {priority_emoji} {area.get('name', 'Unknown')}\n")
                output.append(f"{area.get('description', '')}\n")
                output.append(f"- **Задач:** {len(area_tasks)}\n")
                output.append(f"- **Выполнено:** {len(area_completed)} ({area_rate:.1%})\n")
                output.append(f"- **Приоритет:** {area.get('priority', 'medium')}\n\n")
        
        # Критические задачи и блокеры
        blockers = llm_analysis.get("blockers", [])
        if blockers:
            output.append("### Критические задачи и блокеры\n\n")
            for blocker in blockers[:10]:
                task_id = blocker.get("task_id")
                task = next((t for t in all_tasks if t.get("id") == task_id), None)
                if task:
                    priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(blocker.get("priority", "medium"), "⚪")
                    output.append(f"- {priority_emoji} **{task.get('text', '')[:150]}**\n")
                    output.append(f"  - Блокирует: {len(blocker.get('blocks', []))} задач\n")
                    output.append(f"  - Приоритет: {blocker.get('priority', 'medium')}\n\n")
        
        # Roadmap
        roadmap = llm_analysis.get("roadmap", {})
        if roadmap:
            output.append("## Roadmap\n\n")
            
            # Ближайшие цели (1-2 недели)
            immediate = roadmap.get("immediate_goals", [])
            if immediate:
                output.append("### Ближайшие цели (1-2 недели)\n\n")
                for goal in immediate[:10]:
                    task_id = goal.get("task_id")
                    task = next((t for t in all_tasks if t.get("id") == task_id), None)
                    if task:
                        priority_emoji = {"critical": "🔴", "high": "🟠"}.get(goal.get("priority", "high"), "🟡")
                        output.append(f"- {priority_emoji} **{goal.get('goal', task.get('text', ''))[:150]}**\n")
                        output.append(f"  - Время: {goal.get('timeframe', '1-2 недели')}\n")
                        output.append(f"  - Приоритет: {goal.get('priority', 'high')}\n\n")
            
            # Среднесрочные цели (1-3 месяца)
            short_term = roadmap.get("short_term_goals", [])
            if short_term:
                output.append("### Среднесрочные цели (1-3 месяца)\n\n")
                for goal in short_term[:10]:
                    task_id = goal.get("task_id")
                    task = next((t for t in all_tasks if t.get("id") == task_id), None)
                    if task:
                        priority_emoji = {"high": "🟠", "medium": "🟡"}.get(goal.get("priority", "medium"), "🟢")
                        output.append(f"- {priority_emoji} **{goal.get('goal', task.get('text', ''))[:150]}**\n")
                        output.append(f"  - Время: {goal.get('timeframe', '1-3 месяца')}\n")
                        output.append(f"  - Приоритет: {goal.get('priority', 'medium')}\n\n")
            
            # Долгосрочные цели (3+ месяца)
            long_term = roadmap.get("long_term_goals", [])
            if long_term:
                output.append("### Долгосрочные цели (3+ месяца)\n\n")
                for goal in long_term[:10]:
                    task_id = goal.get("task_id")
                    task = next((t for t in all_tasks if t.get("id") == task_id), None)
                    if task:
                        priority_emoji = {"medium": "🟡", "low": "🟢"}.get(goal.get("priority", "low"), "⚪")
                        output.append(f"- {priority_emoji} **{goal.get('goal', task.get('text', ''))[:150]}**\n")
                        output.append(f"  - Время: {goal.get('timeframe', '3+ месяца')}\n")
                        output.append(f"  - Приоритет: {goal.get('priority', 'low')}\n\n")
        
        # Технический долг
        technical_debt = llm_analysis.get("technical_debt", [])
        if technical_debt:
            output.append("## Технический долг\n\n")
            for debt in technical_debt[:15]:
                task_id = debt.get("task_id")
                task = next((t for t in all_tasks if t.get("id") == task_id), None)
                if task:
                    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(debt.get("severity", "medium"), "⚪")
                    output.append(f"- {severity_emoji} **{debt.get('description', task.get('text', ''))[:150]}**\n")
                    output.append(f"  - Тип: {debt.get('debt_type', 'unknown')}\n")
                    output.append(f"  - Серьезность: {debt.get('severity', 'medium')}\n\n")
        
        # Граф зависимостей (упрощенный ASCII)
        dependencies = llm_analysis.get("dependencies", [])
        critical_path = llm_analysis.get("critical_path", [])
        if critical_path:
            output.append("## Критический путь выполнения\n\n")
            output.append("```\n")
            task_map = {t.get("id"): t for t in all_tasks}
            for i, task_id in enumerate(critical_path[:15]):
                task = task_map.get(task_id)
                if task:
                    arrow = " -> " if i < len(critical_path) - 1 else ""
                    output.append(f"[{i+1}] {task.get('text', '')[:80]}{arrow}\n")
            output.append("```\n\n")
        
        # Рекомендации
        recommendations = llm_analysis.get("recommendations", [])
        if recommendations:
            output.append("## Рекомендации\n\n")
            for i, rec in enumerate(recommendations, 1):
                rec_type = rec.get("type", "general") if isinstance(rec, dict) else "general"
                priority = rec.get("priority", "medium") if isinstance(rec, dict) else "medium"
                description = rec.get("description", rec) if isinstance(rec, dict) else rec
                impact = rec.get("impact", "") if isinstance(rec, dict) else ""
                
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                output.append(f"{i}. {priority_emoji} **{description}**\n")
                if isinstance(rec, dict):
                    output.append(f"   - Тип: {rec_type}\n")
                    if impact:
                        output.append(f"   - Влияние: {impact}\n")
                output.append("\n")
        
        # Выполненные задачи
        if completed:
            output.append("## ✅ Выполненные задачи\n\n")
            for task in completed[:50]:  # Ограничить вывод
                output.append(f"- ✅ {task.get('text', '')[:100]}\n")
                output.append(f"  *Из плана: {task.get('plan_source', 'unknown')}*\n")
            if len(completed) > 50:
                output.append(f"\n*... и еще {len(completed) - 50} выполненных задач*\n")
            output.append("\n")
        
        # Задачи в процессе
        if in_progress:
            output.append("## ⏳ Задачи в процессе\n\n")
            for task in in_progress[:30]:
                score = task.get('completion', {}).get('completion_score', 0)
                output.append(f"- ⏳ [{score:.0%}] {task.get('text', '')[:100]}\n")
                output.append(f"  *Из плана: {task.get('plan_source', 'unknown')}*\n")
            if len(in_progress) > 30:
                output.append(f"\n*... и еще {len(in_progress) - 30} задач в процессе*\n")
            output.append("\n")
        
        # Приоритетные задачи (из LLM анализа)
        if llm_analysis.get('priority_order'):
            output.append("## 🎯 Приоритетные задачи для выполнения\n\n")
            priority_task_ids = llm_analysis['priority_order'][:20]
            task_map = {t.get('id'): t for t in all_tasks}
            
            for i, task_id in enumerate(priority_task_ids, 1):
                task = task_map.get(task_id)
                if task:
                    output.append(f"{i}. **{task.get('text', '')[:150]}**\n")
                    output.append(f"   - План: {task.get('plan_source', 'unknown')}\n")
                    if task.get('section'):
                        output.append(f"   - Секция: {task.get('section')}\n")
                    output.append("\n")
        
        # Детальные задачи по функциональным областям
        output.append("## Детальные задачи по функциональным областям\n\n")
        
        # Группировка задач по функциональным областям
        if functional_areas:
            for area in functional_areas:
                area_name = area.get('name', 'Unknown')
                area_task_ids = area.get('task_ids', [])
                area_tasks = [t for t in all_tasks if t.get("id") in area_task_ids]
                
                if area_tasks:
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(area.get("priority", "medium"), "⚪")
                    output.append(f"### {priority_emoji} {area_name}\n\n")
                    output.append(f"{area.get('description', '')}\n\n")
                    
                    # Группировать задачи по статусу
                    area_completed = [t for t in area_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8]
                    area_in_progress = [t for t in area_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8]
                    area_todo = [t for t in area_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3]
                    
                    if area_completed:
                        output.append(f"#### Выполнено ({len(area_completed)})\n\n")
                        for task in area_completed[:10]:
                            output.append(f"- ✅ {task.get('text', '')[:150]}\n")
                        if len(area_completed) > 10:
                            output.append(f"*... и еще {len(area_completed) - 10} выполненных задач*\n")
                        output.append("\n")
                    
                    if area_in_progress:
                        output.append(f"#### В процессе ({len(area_in_progress)})\n\n")
                        for task in area_in_progress[:10]:
                            score = task.get('completion', {}).get('completion_score', 0)
                            output.append(f"- ⏳ [{score:.0%}] {task.get('text', '')[:150]}\n")
                        if len(area_in_progress) > 10:
                            output.append(f"*... и еще {len(area_in_progress) - 10} задач в процессе*\n")
                        output.append("\n")
                    
                    if area_todo:
                        output.append(f"#### Не начато ({len(area_todo)})\n\n")
                        for task in area_todo[:15]:
                            output.append(f"- ❌ {task.get('text', '')[:150]}\n")
                        if len(area_todo) > 15:
                            output.append(f"*... и еще {len(area_todo) - 15} не начатых задач*\n")
                        output.append("\n")
        
        # История планов
        output.append("## История планов\n\n")
        for plan in all_plans[:30]:  # Ограничить вывод
            source_emoji = "📁" if plan['source'] == 'cursor_plans' else "📦" if plan['source'] == 'archive' else "💾"
            output.append(f"- {source_emoji} **{plan.get('name', 'Unknown')}** ({plan.get('source', 'unknown')})")
            if plan.get('modified'):
                output.append(f" - {plan['modified'][:10]}")
            output.append("\n")
        if len(all_plans) > 30:
            output.append(f"\n*... и еще {len(all_plans) - 30} планов*\n")
        output.append("\n")
        
        # Приоритетные задачи для выполнения
        priority_order = llm_analysis.get('priority_order', [])
        if priority_order:
            output.append("## Приоритетные задачи для выполнения\n\n")
            task_map = {t.get('id'): t for t in all_tasks}
            for i, task_id in enumerate(priority_order[:30], 1):
                task = task_map.get(task_id)
                if task:
                    completion_score = task.get('completion', {}).get('completion_score', 0)
                    if completion_score < 0.8:  # Показывать только незавершенные
                        status_emoji = "✅" if completion_score >= 0.8 else \
                                      "⏳" if completion_score >= 0.3 else "❌"
                        output.append(f"{i}. {status_emoji} **{task.get('text', '')[:150]}**\n")
                        output.append(f"   - Прогресс: {completion_score:.0%}\n")
                        output.append(f"   - План: {task.get('plan_source', 'unknown')}\n")
                        if task.get('section'):
                            output.append(f"   - Секция: {task.get('section')}\n")
                        output.append("\n")
        
        return "\n".join(output)
    
    def export_to_json(self, all_tasks: List[Dict], all_plans: List[Dict], 
                      llm_analysis: Dict) -> Dict[str, Any]:
        """Экспортировать данные в JSON формат"""
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_plans": len(all_plans),
                "total_tasks": len(all_tasks)
            },
            "plans": all_plans,
            "tasks": all_tasks,
            "analysis": llm_analysis,
            "statistics": {
                "completed": sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8),
                "in_progress": sum(1 for t in all_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8),
                "todo": sum(1 for t in all_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3)
            }
        }
    
    async def consolidate(self) -> tuple[str, Dict]:
        """Основной метод консолидации. Возвращает (план, llm_analysis)"""
        logger.info("Начало консолидации планов...")
        
        # 1. Собрать планы из файлов
        logger.info("Сбор планов из файлов...")
        file_plans = self.collect_file_plans()
        logger.info(f"Найдено планов в файлах: {len(file_plans)}")
        
        # 2. Собрать планы из БД
        logger.info("Сбор планов из БД...")
        db_plans = self.collect_db_plans()
        logger.info(f"Найдено планов в БД: {len(db_plans)}")
        
        self.all_plans = file_plans + db_plans
        
        # 3. Парсить задачи из файловых планов
        logger.info("Парсинг задач из планов...")
        for plan in file_plans:
            tasks = self.parse_tasks_from_markdown(plan['content'], plan['name'])
            self.all_tasks.extend(tasks)
        
        # 4. Парсить задачи из планов БД
        for plan in db_plans:
            if plan.get('steps'):
                for i, step in enumerate(plan.get('steps', []), 1):
                    if isinstance(step, dict):
                        step_text = step.get('description', '') or step.get('action', '') or str(step)
                    else:
                        step_text = str(step)
                    
                    if step_text:
                        category_info = self.categorize_task(step_text)
                        self.all_tasks.append({
                            "id": f"db_{plan.get('id', 'unknown')}_step_{i}",
                            "section": f"План: {plan.get('goal', 'Unknown')[:50]}",
                            "text": step_text,
                            "status": "unknown",
                            "plan_source": f"db_plan_{plan.get('id', 'unknown')[:8]}",
                            "task_type": category_info["type"],
                            "complexity": category_info["complexity"],
                            "estimated_hours": category_info["estimated_hours"]
                        })
        
        logger.info(f"Всего задач найдено: {len(self.all_tasks)}")
        
        # 5. Дедупликация задач
        logger.info("Дедупликация задач...")
        self.all_tasks = self.deduplicate_tasks(self.all_tasks)
        logger.info(f"После дедупликации: {len(self.all_tasks)} задач")
        
        # 6. Анализ выполнения задач
        logger.info("Анализ выполнения задач...")
        for task in self.all_tasks:
            completion = self.analyze_task_completion(task)
            task['completion'] = completion
        
        # 7. Анализ через LLM
        logger.info("Анализ через LLM...")
        llm_analysis = await self.analyze_with_llm(self.all_tasks, self.all_plans)
        
        # 8. Генерация единого плана
        logger.info("Генерация единого плана...")
        consolidated_plan = self.generate_consolidated_plan(self.all_tasks, self.all_plans, llm_analysis)
        
        return consolidated_plan, llm_analysis


async def main():
    """Главная функция"""
    print("=" * 70)
    print(" Консолидация планов проекта AARD")
    print("=" * 70 + "\n")
    
    consolidator = PlanConsolidator()
    
    try:
        consolidated_plan, llm_analysis = await consolidator.consolidate()
        
        # Сохранить результат в Markdown
        output_file = consolidator.project_root / ".cursor" / "plans" / "consolidated_master_plan.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(consolidated_plan, encoding="utf-8")
        
        # Экспортировать в JSON
        json_data = consolidator.export_to_json(
            consolidator.all_tasks,
            consolidator.all_plans,
            llm_analysis
        )
        json_file = consolidator.project_root / ".cursor" / "plans" / "consolidated_master_plan.json"
        json_file.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        
        print(f"\n✅ Консолидированный план сохранен:")
        print(f"   Markdown: {output_file}")
        print(f"   JSON: {json_file}")
        print(f"\n📊 Статистика:")
        print(f"   - Планов проанализировано: {len(consolidator.all_plans)}")
        print(f"   - Задач найдено: {len(consolidator.all_tasks)}")
        
        # Статистика по статусам
        completed = sum(1 for t in consolidator.all_tasks if t.get('completion', {}).get('completion_score', 0) >= 0.8)
        in_progress = sum(1 for t in consolidator.all_tasks if 0.3 <= t.get('completion', {}).get('completion_score', 0) < 0.8)
        todo = sum(1 for t in consolidator.all_tasks if t.get('completion', {}).get('completion_score', 0) < 0.3)
        
        print(f"   - Выполнено: {completed}")
        print(f"   - В процессе: {in_progress}")
        print(f"   - Не начато: {todo}")
        
    except Exception as e:
        logger.error(f"Ошибка консолидации: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

