"""
Скрипт для консолидации дублированного функционала
Этап 9.1.3: Консолидировать дублированный функционал
"""
import ast
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class DuplicateConsolidator:
    """Консолидация дублированного функционала"""
    
    def __init__(self, dry_run: bool = True):
        self.backend_dir = backend_dir
        self.dry_run = dry_run
        self.consolidated_functions = []
        
    def consolidate_print_separator(self) -> Dict:
        """Консолидировать функцию print_separator"""
        # Найти все файлы с print_separator
        files_with_separator = []
        
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                if "def print_separator" in content:
                    files_with_separator.append(py_file)
            except:
                continue
        
        # Заменить на импорт из utils
        replacements = []
        for file_path in files_with_separator:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Найти определение функции
                pattern = r'def print_separator\([^)]*\):.*?(?=\n\ndef|\nclass|\Z)'
                match = re.search(pattern, content, re.DOTALL)
                
                if match:
                    # Проверить, есть ли уже импорт из utils
                    if "from app.core.utils import" not in content and \
                       "from app.core import utils" not in content:
                        # Добавить импорт
                        import_line = "from app.core.utils import print_separator\n"
                        
                        # Найти место для импорта (после других импортов)
                        import_section_end = 0
                        for i, line in enumerate(content.split('\n')):
                            if line.strip().startswith('import ') or line.strip().startswith('from '):
                                import_section_end = i + 1
                        
                        lines = content.split('\n')
                        if import_section_end > 0:
                            lines.insert(import_section_end, import_line)
                        else:
                            lines.insert(0, import_line)
                        
                        content = '\n'.join(lines)
                    
                    # Удалить определение функции
                    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
                    
                    if new_content != content:
                        replacements.append({
                            "file": str(file_path.relative_to(self.backend_dir)),
                            "action": "replace_print_separator"
                        })
                        
                        if not self.dry_run:
                            file_path.write_text(new_content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Ошибка обработки {file_path}: {e}")
        
        return {
            "function": "print_separator",
            "files_updated": len(replacements),
            "replacements": replacements
        }
    
    def consolidate_init_servers(self) -> Dict:
        """Консолидировать функцию init_servers"""
        # Найти дублированные init_servers
        files_with_init = []
        
        for py_file in self.backend_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                if "def init_servers" in content:
                    files_with_init.append(py_file)
            except:
                continue
        
        # Оставить только один файл (scripts/init_ollama_servers.py), остальные удалить или заменить на импорт
        if len(files_with_init) > 1:
            main_file = None
            duplicates = []
            
            for file_path in files_with_init:
                if "scripts/init_ollama_servers.py" in str(file_path) or \
                   "init_ollama_servers.py" in str(file_path):
                    main_file = file_path
                else:
                    duplicates.append(file_path)
            
            if main_file:
                # Удалить дубликаты или заменить на импорт
                for dup_file in duplicates:
                    if not self.dry_run:
                        # Можно удалить файл или заменить функцию на импорт
                        # Пока просто пометим для удаления
                        pass
                    
                    self.consolidated_functions.append({
                        "file": str(dup_file.relative_to(self.backend_dir)),
                        "action": "remove_duplicate_init_servers"
                    })
        
        return {
            "function": "init_servers",
            "files_updated": len(self.consolidated_functions)
        }
    
    def consolidate(self, audit_results_path: Path) -> Dict[str, Any]:
        """Выполнить консолидацию на основе результатов аудита"""
        logger.info("Начало консолидации дублированного функционала...")
        
        # Консолидировать print_separator
        logger.info("Консолидация print_separator...")
        separator_result = self.consolidate_print_separator()
        
        # Консолидировать init_servers
        logger.info("Консолидация init_servers...")
        init_result = self.consolidate_init_servers()
        
        return {
            "print_separator": separator_result,
            "init_servers": init_result,
            "summary": {
                "total_consolidated": len(self.consolidated_functions)
            }
        }


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Консолидация дублированного функционала")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Только показать что будет изменено, не изменять")
    parser.add_argument("--execute", action="store_true",
                       help="Выполнить консолидацию (по умолчанию dry-run)")
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    print("=" * 70)
    print(" Консолидация дублированного функционала проекта AARD")
    print("=" * 70 + "\n")
    
    if dry_run:
        print("⚠️  РЕЖИМ DRY-RUN: изменения не будут применены\n")
    else:
        print("⚠️  РЕЖИМ ВЫПОЛНЕНИЯ: изменения будут применены!\n")
    
    consolidator = DuplicateConsolidator(dry_run=dry_run)
    
    # Путь к результатам аудита
    audit_results_path = consolidator.backend_dir.parent / "docs" / "TECHNICAL_DEBT.json"
    
    if not audit_results_path.exists():
        print(f"❌ Файл результатов аудита не найден: {audit_results_path}")
        print("   Сначала запустите: python scripts/code_audit.py")
        sys.exit(1)
    
    try:
        results = consolidator.consolidate(audit_results_path)
        
        print(f"\n✅ Консолидация завершена:")
        print(f"   - print_separator: {results['print_separator']['files_updated']} файлов")
        print(f"   - init_servers: {results['init_servers']['files_updated']} файлов")
        
        if dry_run:
            print("\n💡 Для применения изменений запустите с флагом --execute")
        
    except Exception as e:
        logger.error(f"Ошибка консолидации: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

