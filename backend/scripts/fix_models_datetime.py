"""
Script to replace datetime.utcnow in SQLAlchemy models Column defaults
"""
import re
from pathlib import Path

backend_dir = Path(__file__).parent.parent
models_dir = backend_dir / "app" / "models"

def fix_file(file_path: Path) -> tuple[int, list[str]]:
    """Fix datetime.utcnow in a model file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Check if timezone is imported
        has_timezone_import = 'from datetime import' in content and 'timezone' in content
        
        # Replace datetime.utcnow in Column defaults
        # Pattern: default=datetime.utcnow or onupdate=datetime.utcnow
        content = re.sub(
            r'default=datetime\.utcnow',
            'default=lambda: datetime.now(timezone.utc)',
            content
        )
        content = re.sub(
            r'onupdate=datetime\.utcnow',
            'onupdate=lambda: datetime.now(timezone.utc)',
            content
        )
        
        # Add timezone import if needed
        if not has_timezone_import and 'from datetime import datetime' in content:
            content = re.sub(
                r'from datetime import datetime',
                'from datetime import datetime, timezone',
                content
            )
            content = re.sub(
                r'from datetime import datetime, timedelta',
                'from datetime import datetime, timedelta, timezone',
                content
            )
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            count = original_content.count('datetime.utcnow')
            return count, []
        else:
            return 0, []
            
    except Exception as e:
        return 0, [f"Error processing {file_path}: {e}"]

def main():
    """Main function"""
    print("=" * 80)
    print("Исправление datetime.utcnow в SQLAlchemy models")
    print("=" * 80)
    
    model_files = list(models_dir.glob("*.py"))
    model_files = [f for f in model_files if f.name != "__init__.py"]
    
    print(f"Найдено файлов моделей: {len(model_files)}")
    print()
    
    total_replacements = 0
    total_errors = []
    
    for file_path in model_files:
        relative_path = file_path.relative_to(backend_dir)
        count, errors = fix_file(file_path)
        if count > 0:
            print(f"✅ {relative_path}: {count} замен")
            total_replacements += count
        if errors:
            total_errors.extend(errors)
            for error in errors:
                print(f"⚠️  {error}")
    
    print()
    print("=" * 80)
    print(f"ИТОГО: {total_replacements} замен в {len(model_files)} файлах")
    if total_errors:
        print(f"Ошибок: {len(total_errors)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
