#!/usr/bin/env python3
"""
LAUNCHER для Version Checker
Цей файл потрібен для коректного створення EXE файлу.
Він вирішує проблеми з шляхами та імпортами після упаковки PyInstaller.
"""

import sys
import os
import traceback
from datetime import datetime

def setup_environment():
    """Налаштувати середовище для роботи в EXE та звичайному режимі"""
    
    # Визначаємо, чи ми в EXE файлі
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # Режим EXE: використовуємо тимчасову папку PyInstaller
        base_path = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
        
        # Змінюємо поточну робочу директорію на папку з EXE
        os.chdir(exe_dir)
        
        # Додаємо шляхи для імпортів
        sys.path.insert(0, base_path)
        sys.path.insert(0, exe_dir)
    else:
        # Звичайний режим: використовуємо папку скрипта
        base_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(base_path)
    
    return base_path, is_frozen

def setup_data_files(base_path, is_frozen):
    """Налаштувати файли даних"""
    
    # Список необхідних файлів
    required_files = ['config.json', 'versions.db']
    
    for filename in required_files:
        file_path = os.path.join(base_path, filename)
        
        # Якщо файлу немає, створити за замовчуванням
        if not os.path.exists(file_path):
            if filename == 'config.json':
                create_default_config()
            elif filename == 'versions.db':
                # База даних створиться автоматично при першому запуску
                pass
    
    # Створюємо папку для бекапів
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)

def create_default_config():
    """Створити конфігураційний файл за замовчуванням"""
    default_config = {
        "database": {
            "name": "versions.db",
            "backup_folder": "backups",
            "auto_backup": True,
            "backup_interval_days": 7
        },
        "checking": {
            "auto_check_interval_minutes": 1440,
            "retry_attempts": 3,
            "timeout_seconds": 30,
            "delay_between_checks": 2
        },
        "appearance": {
            "theme": "default",
            "font_size": 12,
            "show_notifications": True
        }
    }
    
    import json
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

def handle_exception(exc_type, exc_value, exc_traceback):
    """Обробник необроблених винятків"""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Записуємо в лог
    log_file = "error_log.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f"Помилка: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(error_msg)
        f.write(f"\n{'='*60}\n\n")
    
    # Спроба показати повідомлення в GUI
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        QMessageBox.critical(
            None,
            "Критична помилка",
            f"Сталася помилка програми:\n\n{exc_value}\n\n"
            f"Деталі записані в {log_file}"
        )
    except:
        # Якщо не вдалося показати GUI, виводимо в консоль
        print(f"Критична помилка:\n{error_msg}")
        input("Натисніть Enter для виходу...")
    
    sys.exit(1)

def main():
    """Головна функція запускача"""
    
    # Налаштовуємо обробник винятків
    sys.excepthook = handle_exception
    
    print("🚀 Запуск Version Checker...")
    
    try:
        # Налаштовуємо середовище
        base_path, is_frozen = setup_environment()
        
        print(f"📁 Робоча папка: {os.getcwd()}")
        print(f"🔧 Режим: {'EXE' if is_frozen else 'Python'}")
        
        # Налаштовуємо файли даних
        setup_data_files(base_path, is_frozen)
        
        # Імпортуємо головну програму
        print("📦 Завантаження модулів...")
        
        # Приховуємо попередження PyQt
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        # Імпортуємо головний модуль
        from main import main as app_main
        
        print("✅ Модулі завантажено успішно!")
        print("🖥️ Запуск головного вікна...")
        
        # Запускаємо головну програму
        app_main()
        
    except ImportError as e:
        print(f"❌ Помилка імпорту: {e}")
        print("Перевірте наявність всіх необхідних файлів:")
        print("  - main.py")
        print("  - database.py") 
        print("  - parser.py")
        print("  - PyQt5 встановлено (pip install PyQt5)")
        
        input("Натисніть Enter для виходу...")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Невідома помилка: {e}")
        import traceback
        traceback.print_exc()
        input("Натисніть Enter для виходу...")
        sys.exit(1)

if __name__ == "__main__":
    main()