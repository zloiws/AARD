"""
Скрипт для реорганизации структуры проекта
Перемещает файлы в правильные места
"""
import os
import shutil
from pathlib import Path

# Корневая директория проекта
ROOT = Path(__file__).parent.parent.parent

def move_files(src_pattern, dst_dir, description):
    """Переместить файлы по паттерну"""
    print(f"\n📦 {description}...")
    
    src_dir = Path(src_pattern).parent
    pattern = Path(src_pattern).name
    
    # Получаем все файлы по паттерну
    files = list(src_dir.glob(pattern))
    
    if not files:
        print(f"  ℹ️  Файлы не найдены: {pattern}")
        return
    
    # Создаем целевую директорию
    dst_path = ROOT / dst_dir
    dst_path.mkdir(parents=True, exist_ok=True)
    
    moved = 0
    for file in files:
        try:
            dst_file = dst_path / file.name
            # Если файл уже существует, удаляем старый
            if dst_file.exists():
                file.unlink()
                print(f"  🗑️  Удален дубликат: {file.name}")
            else:
                shutil.move(str(file), str(dst_file))
                print(f"  ✅ Перемещен: {file.name}")
                moved += 1
        except Exception as e:
            print(f"  ❌ Ошибка при перемещении {file.name}: {e}")
    
    print(f"  📊 Перемещено: {moved} файлов")

def remove_duplicates(src_dir, dst_dir, extension=".md"):
    """Удалить дубликаты файлов"""
    print(f"\n🗑️  Удаление дубликатов {extension} из {src_dir}...")
    
    src_path = ROOT / src_dir
    dst_path = ROOT / dst_dir
    
    if not src_path.exists():
        return
    
    removed = 0
    for file in src_path.glob(f"*{extension}"):
        if (dst_path / file.name).exists():
            file.unlink()
            print(f"  🗑️  Удален дубликат: {file.name}")
            removed += 1
    
    print(f"  📊 Удалено дубликатов: {removed}")

def main():
    print("═══════════════════════════════════════════════════════")
    print("  📋 РЕОРГАНИЗАЦИЯ ФАЙЛОВ ПРОЕКТА")
    print("═══════════════════════════════════════════════════════")
    
    # 1. Переместить тестовые скрипты
    move_files(
        "backend/scripts/test_*.py",
        "backend/tests/scripts",
        "Перемещение тестовых скриптов из backend/scripts/ в backend/tests/scripts/"
    )
    
    # 2. Переместить документацию из backend/ в docs/
    move_files(
        "backend/*.md",
        "docs",
        "Перемещение документации из backend/ в docs/"
    )
    
    # 3. Переместить документацию из корня в docs/
    move_files(
        "*.md",
        "docs",
        "Перемещение документации из корня проекта в docs/ (кроме README.md)"
    )
    
    # 4. Удалить дубликаты документации
    remove_duplicates("backend", "docs", ".md")
    
    print("\n" + "="*55)
    print("  ✅ РЕОРГАНИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*55)
    
    # Итоговая статистика
    print("\n📊 Итоговая статистика:")
    print(f"  Тестовых скриптов в backend/tests/scripts/: {len(list((ROOT / 'backend/tests/scripts').glob('*.py')))}")
    print(f"  Тестовых скриптов в backend/scripts/: {len(list((ROOT / 'backend/scripts').glob('test_*.py')))}")
    print(f"  Документации в backend/: {len(list((ROOT / 'backend').glob('*.md')))}")
    print(f"  Документации в docs/: {len(list((ROOT / 'docs').glob('*.md')))}")

if __name__ == "__main__":
    main()

