"""
Скрипт для реорганизации документации
Этап 9.2.1: Реорганизовать документацию
"""
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class DocsReorganizer:
    """Реорганизатор документации"""
    
    def __init__(self, dry_run: bool = True):
        self.project_root = backend_dir.parent
        self.docs_dir = self.project_root / "docs"
        self.archive_dir = self.docs_dir / "archive"
        self.guides_dir = self.docs_dir / "guides"
        self.dry_run = dry_run
        self.moved_files = []
        self.merged_files = []
        
    def categorize_docs(self) -> Dict[str, List[Path]]:
        """Категоризировать документы"""
        categories = {
            "implementation_status": [],
            "test_results": [],
            "fixes": [],
            "guides": [],
            "architecture": [],
            "other": []
        }
        
        # Ключевые слова для категоризации
        keywords = {
            "implementation_status": ["implementation", "status", "complete", "progress"],
            "test_results": ["test", "result", "testing"],
            "fixes": ["fix", "fixes", "error", "bug"],
            "guides": ["guide", "setup", "howto", "tutorial"],
            "architecture": ["architecture", "design", "system"]
        }
        
        for md_file in self.docs_dir.glob("*.md"):
            if md_file.name == "README.md":
                continue
            
            file_name_lower = md_file.stem.lower()
            categorized = False
            
            for category, category_keywords in keywords.items():
                if any(kw in file_name_lower for kw in category_keywords):
                    categories[category].append(md_file)
                    categorized = True
                    break
            
            if not categorized:
                categories["other"].append(md_file)
        
        return categories
    
    def create_docs_index(self) -> str:
        """Создать индекс документации"""
        categories = self.categorize_docs()
        
        output = []
        output.append("# Документация AARD\n\n")
        output.append(f"*Последнее обновление: {datetime.now().strftime('%Y-%m-%d')}*\n\n")
        
        output.append("## Навигация\n\n")
        output.append("- [Руководства](#руководства)\n")
        output.append("- [Архитектура](#архитектура)\n")
        output.append("- [Статус реализации](#статус-реализации)\n")
        output.append("- [Результаты тестирования](#результаты-тестирования)\n")
        output.append("- [Исправления](#исправления)\n")
        output.append("- [Прочее](#прочее)\n\n")
        
        # Руководства
        if categories["guides"] or self.guides_dir.exists():
            output.append("## Руководства\n\n")
            output.append("Детальные руководства по использованию и настройке системы.\n\n")
            output.append("### Основные руководства\n\n")
            
            guide_files = list(self.guides_dir.glob("*.md")) if self.guides_dir.exists() else []
            for guide_file in sorted(guide_files):
                guide_name = guide_file.stem.replace("_", " ").title()
                output.append(f"- [{guide_name}](guides/{guide_file.name})\n")
            
            output.append("\n### Другие руководства\n\n")
            for doc in categories["guides"]:
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Архитектура
        if categories["architecture"]:
            output.append("## Архитектура\n\n")
            for doc in sorted(categories["architecture"]):
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Статус реализации
        if categories["implementation_status"]:
            output.append("## Статус реализации\n\n")
            for doc in sorted(categories["implementation_status"]):
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Результаты тестирования
        if categories["test_results"]:
            output.append("## Результаты тестирования\n\n")
            for doc in sorted(categories["test_results"]):
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Исправления
        if categories["fixes"]:
            output.append("## Исправления\n\n")
            for doc in sorted(categories["fixes"]):
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Прочее
        if categories["other"]:
            output.append("## Прочее\n\n")
            for doc in sorted(categories["other"]):
                output.append(f"- [{doc.stem}]({doc.name})\n")
            output.append("\n")
        
        # Архив
        if self.archive_dir.exists():
            archive_count = len(list(self.archive_dir.glob("*.md")))
            output.append(f"## Архив\n\n")
            output.append(f"Устаревшие документы перемещены в [archive/](archive/) ({archive_count} файлов)\n\n")
        
        return "\n".join(output)
    
    def move_to_archive(self, file_path: Path) -> bool:
        """Переместить файл в архив"""
        if not self.archive_dir.exists():
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        target = self.archive_dir / file_path.name
        
        # Если файл уже существует в архиве, добавить суффикс
        counter = 1
        while target.exists():
            target = self.archive_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
        
        if not self.dry_run:
            shutil.move(str(file_path), str(target))
        
        self.moved_files.append({
            "from": str(file_path.relative_to(self.project_root)),
            "to": str(target.relative_to(self.project_root))
        })
        
        return True
    
    def merge_related_docs(self) -> List[Dict]:
        """Объединить связанные документы"""
        merged = []
        
        # Найти связанные документы (например, TEST_RESULTS.md и TEST_RESULTS_LOGS.md)
        test_results_files = list(self.docs_dir.glob("*TEST*RESULT*.md"))
        if len(test_results_files) > 1:
            # Объединить в один файл
            main_file = test_results_files[0]
            merged_content = [main_file.read_text(encoding="utf-8")]
            
            for other_file in test_results_files[1:]:
                content = other_file.read_text(encoding="utf-8")
                merged_content.append(f"\n\n---\n\n## Из {other_file.name}\n\n{content}")
                
                if not self.dry_run:
                    self.move_to_archive(other_file)
                
                merged.append({
                    "merged_from": str(other_file.relative_to(self.project_root)),
                    "merged_to": str(main_file.relative_to(self.project_root))
                })
            
            if not self.dry_run and merged:
                main_file.write_text("\n".join(merged_content), encoding="utf-8")
        
        return merged
    
    def reorganize(self) -> Dict[str, Any]:
        """Выполнить реорганизацию"""
        logger.info("Начало реорганизации документации...")
        
        # Объединить связанные документы
        logger.info("Объединение связанных документов...")
        merged = self.merge_related_docs()
        
        # Переместить устаревшие документы в архив
        logger.info("Перемещение устаревших документов...")
        # Определить устаревшие документы (например, с датами в прошлом или дубликаты)
        categories = self.categorize_docs()
        
        # Создать индекс
        logger.info("Создание индекса документации...")
        index_content = self.create_docs_index()
        
        if not self.dry_run:
            index_file = self.docs_dir / "README.md"
            index_file.write_text(index_content, encoding="utf-8")
        
        return {
            "merged_files": merged,
            "moved_files": self.moved_files,
            "index_created": True,
            "summary": {
                "merged_count": len(merged),
                "moved_count": len(self.moved_files)
            }
        }


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Реорганизация документации")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Только показать что будет изменено, не изменять")
    parser.add_argument("--execute", action="store_true",
                       help="Выполнить реорганизацию (по умолчанию dry-run)")
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    print("=" * 70)
    print(" Реорганизация документации проекта AARD")
    print("=" * 70 + "\n")
    
    if dry_run:
        print("⚠️  РЕЖИМ DRY-RUN: изменения не будут применены\n")
    else:
        print("⚠️  РЕЖИМ ВЫПОЛНЕНИЯ: изменения будут применены!\n")
    
    reorganizer = DocsReorganizer(dry_run=dry_run)
    
    try:
        results = reorganizer.reorganize()
        
        print(f"\n✅ Реорганизация завершена:")
        summary = results.get("summary", {})
        print(f"   - Объединено файлов: {summary.get('merged_count', 0)}")
        print(f"   - Перемещено в архив: {summary.get('moved_count', 0)}")
        print(f"   - Индекс создан: {results.get('index_created', False)}")
        
        if dry_run:
            print("\n💡 Для применения изменений запустите с флагом --execute")
        
    except Exception as e:
        logger.error(f"Ошибка реорганизации: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

