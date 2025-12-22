"""
Script to replace datetime.utcnow() with datetime.now(timezone.utc) or utc_now()
Usage: python scripts/fix_datetime_utcnow.py [--use-utils]
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

backend_dir = Path(__file__).parent.parent


def find_files_with_utcnow() -> List[Path]:
    """Find all Python files with datetime.utcnow()"""
    files = []
    for py_file in backend_dir.rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8')
            if 'datetime.utcnow()' in content:
                files.append(py_file)
        except Exception:
            pass
    return files


def fix_file(file_path: Path, use_utils: bool = False) -> Tuple[int, List[str]]:
    """
    Fix datetime.utcnow() in a file
    
    Returns:
        (count, errors): Number of replacements and list of errors
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Count occurrences
        count = content.count('datetime.utcnow()')
        if count == 0:
            return 0, []
        
        # Check if timezone is imported
        has_timezone_import = 'from datetime import' in content and 'timezone' in content
        has_datetime_import = 'from datetime import datetime' in content or 'import datetime' in content
        
        if use_utils:
            # Replace with utc_now() from utils
            content = content.replace('datetime.utcnow()', 'utc_now()')
            content = content.replace('datetime.utcnow().isoformat()', 'utc_now_iso()')
            
            # Add import if not present
            if 'from app.utils.datetime_utils import' not in content:
                # Find last import line
                import_lines = []
                for i, line in enumerate(content.split('\n')):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_lines.append((i, line))
                
                if import_lines:
                    last_import_line = import_lines[-1][0]
                    lines = content.split('\n')
                    lines.insert(last_import_line + 1, 'from app.utils.datetime_utils import utc_now, utc_now_iso')
                    content = '\n'.join(lines)
                else:
                    # Add at the beginning
                    lines = content.split('\n')
                    lines.insert(0, 'from app.utils.datetime_utils import utc_now, utc_now_iso')
                    content = '\n'.join(lines)
        else:
            # Replace with datetime.now(timezone.utc)
            content = content.replace('datetime.utcnow()', 'datetime.now(timezone.utc)')
            content = content.replace('datetime.utcnow().isoformat()', 'datetime.now(timezone.utc).isoformat()')
            
            # Add timezone import if needed
            if not has_timezone_import and has_datetime_import:
                # Update import statement
                content = re.sub(
                    r'from datetime import datetime',
                    'from datetime import datetime, timezone',
                    content
                )
                content = re.sub(
                    r'from datetime import datetime,',
                    'from datetime import datetime, timezone,',
                    content
                )
                # Also handle 'import datetime' case
                if 'import datetime' in content and 'from datetime import' not in content:
                    # This is trickier, need to add separate import
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip() == 'import datetime':
                            lines.insert(i + 1, 'from datetime import timezone')
                            break
                    content = '\n'.join(lines)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return count, []
        else:
            return 0, [f"No changes made to {file_path}"]
            
    except Exception as e:
        return 0, [f"Error processing {file_path}: {e}"]


def main():
    """Main function"""
    use_utils = '--use-utils' in sys.argv
    
    print("=" * 80)
    print("Исправление datetime.utcnow() во всех файлах")
    print("=" * 80)
    print(f"Режим: {'Использовать утилиту utc_now()' if use_utils else 'Использовать datetime.now(timezone.utc)'}")
    print()
    
    files = find_files_with_utcnow()
    print(f"Найдено файлов: {len(files)}")
    print()
    
    total_replacements = 0
    total_errors = []
    
    for file_path in files:
        relative_path = file_path.relative_to(backend_dir)
        count, errors = fix_file(file_path, use_utils)
        if count > 0:
            print(f"✅ {relative_path}: {count} замен")
            total_replacements += count
        if errors:
            total_errors.extend(errors)
            for error in errors:
                print(f"⚠️  {error}")
    
    print()
    print("=" * 80)
    print(f"ИТОГО: {total_replacements} замен в {len(files)} файлах")
    if total_errors:
        print(f"Ошибок: {len(total_errors)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
