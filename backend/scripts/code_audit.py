"""
Скрипт для аудита кода на дублирование и неиспользуемые функции
"""
import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def find_duplicate_functions(root_dir: str) -> Dict[str, List[str]]:
    """Найти дублированные функции"""
    function_bodies = defaultdict(list)
    
    for py_file in Path(root_dir).rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pytest_cache" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Получить тело функции как строку
                        func_body = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                        func_name = node.name
                        
                        # Игнорировать тесты и приватные методы
                        if not func_name.startswith('test_') and not func_name.startswith('_'):
                            # Создать ключ из тела функции (без имени)
                            body_key = func_body[len(func_name):].strip()
                            function_bodies[body_key].append(f"{py_file}:{func_name}")
        except Exception as e:
            print(f"Ошибка при обработке {py_file}: {e}")
    
    # Найти дубликаты (функции с одинаковым телом)
    duplicates = {k: v for k, v in function_bodies.items() if len(v) > 1}
    return duplicates

def find_unused_imports(root_dir: str) -> List[Tuple[str, List[str]]]:
    """Найти неиспользуемые импорты (базовая проверка)"""
    unused = []
    
    for py_file in Path(root_dir).rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pytest_cache" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(py_file))
                
                imported_names = set()
                used_names = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_names.add(alias.asname or alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            imported_names.add(alias.asname or alias.name)
                    elif isinstance(node, ast.Name):
                        used_names.add(node.id)
                
                # Простая проверка (не учитывает контекст)
                unused_imports = imported_names - used_names
                if unused_imports:
                    unused.append((str(py_file), list(unused_imports)))
        except Exception as e:
            print(f"Ошибка при обработке {py_file}: {e}")
    
    return unused

def find_empty_files(root_dir: str) -> List[str]:
    """Найти пустые или почти пустые файлы"""
    empty_files = []
    
    for py_file in Path(root_dir).rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pytest_cache" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                # Файл считается пустым если содержит только комментарии и docstrings
                lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
                if len(lines) <= 3:  # Только импорты и docstring
                    empty_files.append(str(py_file))
        except Exception as e:
            print(f"Ошибка при обработке {py_file}: {e}")
    
    return empty_files

def generate_audit_report(root_dir: str = "backend/app") -> str:
    """Сгенерировать отчет аудита"""
    report = []
    report.append("=" * 80)
    report.append("ОТЧЕТ АУДИТА КОДА")
    report.append("=" * 80)
    report.append("")
    
    # Дублированные функции
    report.append("1. ДУБЛИРОВАННЫЕ ФУНКЦИИ:")
    report.append("-" * 80)
    duplicates = find_duplicate_functions(root_dir)
    if duplicates:
        for body, locations in list(duplicates.items())[:10]:  # Первые 10
            report.append(f"Найдено {len(locations)} дубликатов:")
            for loc in locations:
                report.append(f"  - {loc}")
            report.append("")
    else:
        report.append("Дубликаты не найдены")
    report.append("")
    
    # Пустые файлы
    report.append("2. ПУСТЫЕ ИЛИ ПОЧТИ ПУСТЫЕ ФАЙЛЫ:")
    report.append("-" * 80)
    empty = find_empty_files(root_dir)
    if empty:
        for f in empty[:20]:  # Первые 20
            report.append(f"  - {f}")
    else:
        report.append("Пустые файлы не найдены")
    report.append("")
    
    # Неиспользуемые импорты (базовая проверка)
    report.append("3. ВОЗМОЖНО НЕИСПОЛЬЗУЕМЫЕ ИМПОРТЫ (требует ручной проверки):")
    report.append("-" * 80)
    unused_imports = find_unused_imports(root_dir)
    if unused_imports:
        for file, imports in unused_imports[:20]:  # Первые 20
            report.append(f"  {file}:")
            for imp in imports:
                report.append(f"    - {imp}")
    else:
        report.append("Неиспользуемые импорты не найдены")
    report.append("")
    
    report.append("=" * 80)
    report.append("РЕКОМЕНДАЦИИ:")
    report.append("1. Проверить дублированные функции вручную")
    report.append("2. Удалить или заполнить пустые файлы")
    report.append("3. Проверить неиспользуемые импорты (могут быть использованы динамически)")
    report.append("4. Проверить неиспользуемые классы и методы")
    report.append("=" * 80)
    
    return "\n".join(report)

if __name__ == "__main__":
    report = generate_audit_report()
    print(report)
    
    # Сохранить отчет
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    with open(docs_dir / "TECHNICAL_DEBT.md", "w", encoding="utf-8") as f:
        f.write("# Технический долг и результаты аудита кода\n\n")
        f.write(report)
