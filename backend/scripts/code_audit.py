"""
Скрипт для аудита кода на дублирование, неиспользуемые функции и устаревшие компоненты
Этап 9.1.1: Провести аудит кода на дублирование
"""
import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Any
from collections import defaultdict
import json

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class CodeAuditor:
    """Аудитор кода для поиска дублирования, неиспользуемых функций и устаревших компонентов"""
    
    def __init__(self):
        self.project_root = backend_dir.parent
        self.backend_dir = backend_dir
        self.duplicated_code = []
        self.unused_functions = []
        self.unused_imports = []
        self.deprecated_components = []
        self.all_functions = {}  # {file: {function_name: function_info}}
        self.all_imports = {}  # {file: [imports]}
        self.all_classes = {}  # {file: [classes]}
        
    def find_duplicated_functions(self) -> List[Dict]:
        """Найти дублированные функции"""
        duplicates = []
        function_signatures = defaultdict(list)
        
        # Собрать все функции
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Получить сигнатуру функции (имя + параметры)
                        params = [arg.arg for arg in node.args.args]
                        signature = f"{node.name}({', '.join(params)})"
                        
                        # Получить тело функции (первые 5 строк для сравнения)
                        func_lines = content.split('\n')[node.lineno-1:node.end_lineno]
                        func_body_start = '\n'.join(func_lines[:10])  # Первые 10 строк
                        
                        function_signatures[signature].append({
                            "file": str(py_file.relative_to(self.backend_dir)),
                            "name": node.name,
                            "line": node.lineno,
                            "body_start": func_body_start[:200]  # Первые 200 символов
                        })
            except Exception as e:
                logger.warning(f"Ошибка парсинга {py_file}: {e}")
        
        # Найти дубликаты (функции с одинаковой сигнатурой)
        for signature, functions in function_signatures.items():
            if len(functions) > 1:
                # Проверить, действительно ли функции похожи
                bodies = [f["body_start"] for f in functions]
                if len(set(bodies)) < len(bodies):  # Есть одинаковые тела
                    duplicates.append({
                        "signature": signature,
                        "functions": functions,
                        "count": len(functions)
                    })
        
        return duplicates
    
    def find_unused_imports(self) -> List[Dict]:
        """Найти неиспользуемые импорты"""
        unused = []
        
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                # Собрать все импорты
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
                        for alias in node.names:
                            imports.add(alias.name)
                
                # Собрать все используемые имена
                used_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
                        used_names.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name):
                            used_names.add(node.value.id)
                
                # Найти неиспользуемые импорты
                file_unused = []
                for imp in imports:
                    if imp not in used_names and imp not in ['sys', 'os', 'json', 'datetime', 'typing']:
                        # Проверить, действительно ли не используется
                        if imp not in content.replace(f"import {imp}", "").replace(f"from {imp}", ""):
                            file_unused.append(imp)
                
                if file_unused:
                    unused.append({
                        "file": str(py_file.relative_to(self.backend_dir)),
                        "imports": file_unused
                    })
            except Exception as e:
                logger.warning(f"Ошибка анализа импортов {py_file}: {e}")
        
        return unused
    
    def find_unused_functions(self) -> List[Dict]:
        """Найти неиспользуемые функции"""
        unused = []
        all_function_calls = set()
        
        # Собрать все вызовы функций
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            all_function_calls.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            all_function_calls.add(node.func.attr)
            except Exception as e:
                logger.warning(f"Ошибка анализа вызовов {py_file}: {e}")
        
        # Найти функции, которые не вызываются
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Пропустить приватные методы и методы классов
                        if node.name.startswith('_') and not node.name.startswith('__'):
                            continue
                        
                        # Пропустить методы, которые могут быть вызваны через декораторы
                        if any(decorator.id == 'router' for decorator in node.decorator_list 
                               if isinstance(decorator, ast.Name)):
                            continue
                        
                        if node.name not in all_function_calls:
                            # Проверить, не является ли это точкой входа (main, __init__ и т.д.)
                            if node.name not in ['main', '__init__', '__call__', 'configure', 'setup']:
                                unused.append({
                                    "file": str(py_file.relative_to(self.backend_dir)),
                                    "function": node.name,
                                    "line": node.lineno
                                })
            except Exception as e:
                logger.warning(f"Ошибка анализа функций {py_file}: {e}")
        
        return unused
    
    def find_deprecated_components(self) -> List[Dict]:
        """Найти устаревшие компоненты (по комментариям, именам и т.д.)"""
        deprecated = []
        
        deprecated_keywords = [
            'deprecated', 'legacy', 'old', 'unused', 'todo', 'fixme',
            'hack', 'temporary', 'temp', 'obsolete', 'remove'
        ]
        
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    for keyword in deprecated_keywords:
                        if keyword in line_lower:
                            # Проверить, что это не просто случайное упоминание
                            if any(marker in line_lower for marker in ['#', '"""', "'''"]):
                                deprecated.append({
                                    "file": str(py_file.relative_to(self.backend_dir)),
                                    "line": i,
                                    "content": line.strip()[:100],
                                    "keyword": keyword
                                })
                                break
            except Exception as e:
                logger.warning(f"Ошибка анализа {py_file}: {e}")
        
        return deprecated
    
    def find_duplicated_code_blocks(self, min_lines: int = 5) -> List[Dict]:
        """Найти дублированные блоки кода"""
        duplicates = []
        code_blocks = defaultdict(list)
        
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split('\n')
                
                # Найти блоки кода (между пустыми строками или отступами)
                current_block = []
                current_indent = 0
                
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        if len(current_block) >= min_lines:
                            block_text = '\n'.join(current_block)
                            # Нормализовать (убрать отступы для сравнения)
                            normalized = '\n'.join(l.strip() for l in current_block if l.strip())
                            if len(normalized) > 50:  # Минимальный размер блока
                                code_blocks[normalized].append({
                                    "file": str(py_file.relative_to(self.backend_dir)),
                                    "start_line": i - len(current_block),
                                    "end_line": i - 1,
                                    "block": block_text
                                })
                        current_block = []
                    else:
                        current_block.append(line)
            except Exception as e:
                logger.warning(f"Ошибка анализа блоков {py_file}: {e}")
        
        # Найти дубликаты
        for block_text, occurrences in code_blocks.items():
            if len(occurrences) > 1:
                duplicates.append({
                    "block": block_text[:200],
                    "occurrences": occurrences,
                    "count": len(occurrences)
                })
        
        return duplicates
    
    def audit(self) -> Dict[str, Any]:
        """Провести полный аудит кода"""
        logger.info("Начало аудита кода...")
        
        logger.info("Поиск дублированных функций...")
        self.duplicated_code = self.find_duplicated_functions()
        
        logger.info("Поиск неиспользуемых импортов...")
        self.unused_imports = self.find_unused_imports()
        
        logger.info("Поиск неиспользуемых функций...")
        self.unused_functions = self.find_unused_functions()
        
        logger.info("Поиск устаревших компонентов...")
        self.deprecated_components = self.find_deprecated_components()
        
        logger.info("Поиск дублированных блоков кода...")
        duplicated_blocks = self.find_duplicated_code_blocks()
        
        return {
            "duplicated_functions": self.duplicated_code,
            "duplicated_blocks": duplicated_blocks,
            "unused_imports": self.unused_imports,
            "unused_functions": self.unused_functions,
            "deprecated_components": self.deprecated_components,
            "summary": {
                "total_duplicated_functions": len(self.duplicated_code),
                "total_duplicated_blocks": len(duplicated_blocks),
                "total_unused_imports": sum(len(u["imports"]) for u in self.unused_imports),
                "total_unused_functions": len(self.unused_functions),
                "total_deprecated": len(self.deprecated_components)
            }
        }
    
    def generate_report(self, audit_results: Dict[str, Any]) -> str:
        """Сгенерировать отчет в Markdown"""
        output = []
        
        output.append("# Отчет аудита кода AARD\n")
        output.append(f"*Сгенерировано: {Path(__file__).stat().st_mtime}*\n\n")
        
        summary = audit_results.get("summary", {})
        output.append("## Сводка\n\n")
        output.append(f"- Дублированных функций: {summary.get('total_duplicated_functions', 0)}\n")
        output.append(f"- Дублированных блоков кода: {summary.get('total_duplicated_blocks', 0)}\n")
        output.append(f"- Неиспользуемых импортов: {summary.get('total_unused_imports', 0)}\n")
        output.append(f"- Неиспользуемых функций: {summary.get('total_unused_functions', 0)}\n")
        output.append(f"- Устаревших компонентов: {summary.get('total_deprecated', 0)}\n\n")
        
        # Дублированные функции
        if audit_results.get("duplicated_functions"):
            output.append("## Дублированные функции\n\n")
            for dup in audit_results["duplicated_functions"][:20]:  # Ограничить вывод
                output.append(f"### {dup['signature']}\n")
                output.append(f"Найдено в {dup['count']} местах:\n")
                for func in dup["functions"]:
                    output.append(f"- `{func['file']}:{func['line']}` - {func['name']}\n")
                output.append("\n")
        
        # Неиспользуемые импорты
        if audit_results.get("unused_imports"):
            output.append("## Неиспользуемые импорты\n\n")
            for item in audit_results["unused_imports"][:30]:
                output.append(f"### {item['file']}\n")
                output.append(f"Импорты: {', '.join(item['imports'])}\n\n")
        
        # Неиспользуемые функции
        if audit_results.get("unused_functions"):
            output.append("## Неиспользуемые функции\n\n")
            for func in audit_results["unused_functions"][:30]:
                output.append(f"- `{func['file']}:{func['line']}` - {func['function']}\n")
            output.append("\n")
        
        # Устаревшие компоненты
        if audit_results.get("deprecated_components"):
            output.append("## Устаревшие компоненты\n\n")
            for comp in audit_results["deprecated_components"][:30]:
                output.append(f"- `{comp['file']}:{comp['line']}` - {comp['keyword']}\n")
                output.append(f"  {comp['content']}\n\n")
        
        return "\n".join(output)


def main():
    """Главная функция"""
    print("=" * 70)
    print(" Аудит кода проекта AARD")
    print("=" * 70 + "\n")
    
    auditor = CodeAuditor()
    
    try:
        audit_results = auditor.audit()
        
        # Сохранить результаты в JSON
        json_file = auditor.project_root / "docs" / "TECHNICAL_DEBT.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        json_file.write_text(json.dumps(audit_results, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # Сгенерировать отчет в Markdown
        report = auditor.generate_report(audit_results)
        md_file = auditor.project_root / "docs" / "TECHNICAL_DEBT.md"
        md_file.write_text(report, encoding="utf-8")
        
        print(f"\n✅ Аудит завершен:")
        print(f"   JSON: {json_file}")
        print(f"   Markdown: {md_file}")
        print(f"\n📊 Результаты:")
        summary = audit_results.get("summary", {})
        for key, value in summary.items():
            print(f"   - {key}: {value}")
        
    except Exception as e:
        logger.error(f"Ошибка аудита: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

