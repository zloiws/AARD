"""
Скрипт для безопасного удаления неиспользуемого кода
Этап 9.1.2: Удалить или переместить неиспользуемый код
"""
import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Set
import shutil

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class CodeCleaner:
    """Очистка неиспользуемого кода"""
    
    def __init__(self, dry_run: bool = True):
        self.backend_dir = backend_dir
        self.dry_run = dry_run
        self.removed_imports = []
        self.removed_functions = []
        self.moved_files = []
        
    def remove_unused_imports(self, file_path: Path, unused_imports: List[str]) -> bool:
        """Удалить неиспользуемые импорты из файла"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split('\n')
            new_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                
                # Проверить, является ли это импортом, который нужно удалить
                should_remove = False
                for unused in unused_imports:
                    if re.match(rf'^import\s+{re.escape(unused)}\s*$', stripped) or \
                       re.match(rf'^from\s+{re.escape(unused)}\s+import', stripped):
                        should_remove = True
                        break
                
                if should_remove:
                    # Пропустить эту строку
                    self.removed_imports.append({
                        "file": str(file_path.relative_to(self.backend_dir)),
                        "import": unused,
                        "line": i + 1
                    })
                    i += 1
                    continue
                
                new_lines.append(line)
                i += 1
            
            if not self.dry_run and new_lines != lines:
                file_path.write_text('\n'.join(new_lines), encoding="utf-8")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления импортов из {file_path}: {e}")
            return False
    
    def find_unused_test_files(self) -> List[Path]:
        """Найти неиспользуемые тестовые файлы"""
        unused = []
        tests_dir = self.backend_dir / "tests"
        
        if not tests_dir.exists():
            return unused
        
        # Проверить, есть ли ссылки на тестовые файлы
        for test_file in tests_dir.rglob("test_*.py"):
            # Пропустить conftest.py и __init__.py
            if test_file.name in ["conftest.py", "__init__.py"]:
                continue
            
            # Проверить, импортируется ли этот файл где-то
            test_module = str(test_file.relative_to(self.backend_dir)).replace('\\', '/').replace('/', '.').replace('.py', '')
            
            # Поиск импортов этого модуля
            found_import = False
            for py_file in self.backend_dir.rglob("*.py"):
                if py_file == test_file:
                    continue
                
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if test_module in content or test_file.stem in content:
                        found_import = True
                        break
                except:
                    continue
            
            if not found_import:
                # Проверить, не является ли это автономным тестом
                try:
                    content = test_file.read_text(encoding="utf-8")
                    # Если в файле есть if __name__ == "__main__", то это может быть автономный тест
                    if "__main__" not in content and "pytest" not in content:
                        unused.append(test_file)
                except:
                    pass
        
        return unused
    
    def find_duplicate_files(self) -> List[Dict]:
        """Найти дублированные файлы"""
        duplicates = []
        file_contents = {}
        
        # Собрать содержимое всех Python файлов
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                # Нормализовать (убрать комментарии и пустые строки для сравнения)
                normalized = '\n'.join(l.strip() for l in content.split('\n') 
                                      if l.strip() and not l.strip().startswith('#'))
                
                if normalized in file_contents:
                    duplicates.append({
                        "original": file_contents[normalized],
                        "duplicate": str(py_file.relative_to(self.backend_dir))
                    })
                else:
                    file_contents[normalized] = str(py_file.relative_to(self.backend_dir))
            except:
                continue
        
        return duplicates
    
    def cleanup(self, audit_results_path: Path) -> Dict[str, Any]:
        """Выполнить очистку на основе результатов аудита"""
        logger.info("Начало очистки неиспользуемого кода...")
        
        # Загрузить результаты аудита
        import json
        with open(audit_results_path, 'r', encoding='utf-8') as f:
            audit_results = json.load(f)
        
        # Удалить неиспользуемые импорты
        logger.info("Удаление неиспользуемых импортов...")
        for item in audit_results.get("unused_imports", [])[:50]:  # Ограничить для безопасности
            file_path = self.backend_dir / item["file"]
            if file_path.exists():
                self.remove_unused_imports(file_path, item["imports"])
        
        # Найти дублированные файлы
        logger.info("Поиск дублированных файлов...")
        duplicate_files = self.find_duplicate_files()
        
        # Найти неиспользуемые тестовые файлы
        logger.info("Поиск неиспользуемых тестовых файлов...")
        unused_test_files = self.find_unused_test_files()
        
        return {
            "removed_imports": self.removed_imports,
            "duplicate_files": duplicate_files,
            "unused_test_files": [str(f.relative_to(self.backend_dir)) for f in unused_test_files],
            "summary": {
                "removed_imports_count": len(self.removed_imports),
                "duplicate_files_count": len(duplicate_files),
                "unused_test_files_count": len(unused_test_files)
            }
        }


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Очистка неиспользуемого кода")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Только показать что будет удалено, не удалять")
    parser.add_argument("--execute", action="store_true",
                       help="Выполнить удаление (по умолчанию dry-run)")
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    print("=" * 70)
    print(" Очистка неиспользуемого кода проекта AARD")
    print("=" * 70 + "\n")
    
    if dry_run:
        print("⚠️  РЕЖИМ DRY-RUN: изменения не будут применены\n")
    else:
        print("⚠️  РЕЖИМ ВЫПОЛНЕНИЯ: изменения будут применены!\n")
    
    cleaner = CodeCleaner(dry_run=dry_run)
    
    # Путь к результатам аудита
    audit_results_path = cleaner.backend_dir.parent / "docs" / "TECHNICAL_DEBT.json"
    
    if not audit_results_path.exists():
        print(f"❌ Файл результатов аудита не найден: {audit_results_path}")
        print("   Сначала запустите: python scripts/code_audit.py")
        sys.exit(1)
    
    try:
        results = cleaner.cleanup(audit_results_path)
        
        print(f"\n✅ Очистка завершена:")
        summary = results.get("summary", {})
        for key, value in summary.items():
            print(f"   - {key}: {value}")
        
        if dry_run:
            print("\n💡 Для применения изменений запустите с флагом --execute")
        
    except Exception as e:
        logger.error(f"Ошибка очистки: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

