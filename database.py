import sqlite3
import json
import os
import sys
import threading
from datetime import datetime

class Database:
    def __init__(self, db_name='versions.db'):
        """Ініціалізація бази даних"""
        # Використовуємо правильний шлях
        if getattr(sys, 'frozen', False):
            # Якщо програма заморожена (EXE)
            db_path = os.path.join(os.path.dirname(sys.executable), db_name)
        else:
            # Звичайний режим
            db_path = db_name
            
        self.db_path = db_path
        self.local_storage = threading.local()  # Для потокобезпечних з'єднань
        
    def get_connection(self):
        """Отримати з'єднання з БД для поточного потоку"""
        if not hasattr(self.local_storage, 'connection'):
            self.local_storage.connection = sqlite3.connect(self.db_path)
            self.local_storage.cursor = self.local_storage.connection.cursor()
            # Увімкнути підтримку зовнішніх ключів
            self.local_storage.cursor.execute("PRAGMA foreign_keys = ON")
            
            # Створити таблиці, якщо потрібно
            self.create_tables()
            
        return self.local_storage.connection, self.local_storage.cursor
    
    def create_tables(self):
        """Створення таблиць, якщо їх немає"""
        conn, cursor = self.get_connection()
        
        # Таблиця програм
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                url TEXT NOT NULL,
                current_version TEXT,
                installed_version TEXT,
                version_selector TEXT,
                last_check TEXT,
                check_interval INTEGER DEFAULT 24,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблиця історії версій
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS version_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER,
                version TEXT,
                check_date TEXT,
                FOREIGN KEY (program_id) REFERENCES programs (id)
            )
        ''')
        
        conn.commit()
    
    def add_program(self, name, category, url, installed_version="", selector="", is_active=1):
        """Додати нову програму до моніторингу"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            INSERT INTO programs (name, category, url, installed_version, version_selector, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, category, url, installed_version, selector, is_active))
        conn.commit()
        return cursor.lastrowid
    
    def get_all_programs(self):
        """Отримати всі програми"""
        _, cursor = self.get_connection()
        
        cursor.execute('''
            SELECT * FROM programs ORDER BY name
        ''')
        return cursor.fetchall()
    
    def get_active_programs(self):
        """Отримати всі активні програми"""
        _, cursor = self.get_connection()
        
        cursor.execute('''
            SELECT * FROM programs WHERE is_active = 1
        ''')
        return cursor.fetchall()
    
    def get_program_by_id(self, program_id):
        """Отримати програму за ID"""
        _, cursor = self.get_connection()
        
        cursor.execute('SELECT * FROM programs WHERE id = ?', (program_id,))
        return cursor.fetchone()
    
    def update_program(self, program_id, name, category, url, installed_version, selector, is_active):
        """Оновити всі параметри програми"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            UPDATE programs 
            SET name = ?, category = ?, url = ?, 
                installed_version = ?, version_selector = ?, is_active = ?,
                updated_at = ?
            WHERE id = ?
        ''', (name, category, url, installed_version, selector, is_active,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), program_id))
        conn.commit()
        return True
    
    def update_version(self, program_id, new_version):
        """Оновити версію програми"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            UPDATE programs 
            SET current_version = ?, last_check = ?, updated_at = ?
            WHERE id = ?
        ''', (new_version, 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
              program_id))
        
        # Додаємо запис в історію
        cursor.execute('''
            INSERT INTO version_history (program_id, version, check_date)
            VALUES (?, ?, ?)
        ''', (program_id, new_version, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
    
    def update_installed_version(self, program_id, installed_version):
        """Оновити встановлену версію"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            UPDATE programs 
            SET installed_version = ?, updated_at = ?
            WHERE id = ?
        ''', (installed_version, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), program_id))
        conn.commit()
    
    def set_program_active(self, program_id, is_active):
        """Змінити статус активності програми"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            UPDATE programs 
            SET is_active = ?, updated_at = ?
            WHERE id = ?
        ''', (is_active, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), program_id))
        conn.commit()
    
    def update_last_check(self, program_id):
        """Оновити час останньої перевірки"""
        conn, cursor = self.get_connection()
        
        cursor.execute('''
            UPDATE programs 
            SET last_check = ?, updated_at = ?
            WHERE id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), program_id))
        conn.commit()
    
      # Таблиця історії версій з CASCADE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS version_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER,
                version TEXT,
                check_date TEXT,
                FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        
        # Створюємо індекси
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_version_history_program_id 
            ON version_history (program_id)
        ''')
        
        conn.commit()
    
    def delete_program(self, program_id):
        """Видалити програму"""
        conn, cursor = self.get_connection()
        
        try:
            # Спочатку видаляємо історію версій
            cursor.execute('DELETE FROM version_history WHERE program_id = ?', (program_id,))
            # Потім видаляємо програму
            cursor.execute('DELETE FROM programs WHERE id = ?', (program_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Помилка при видаленні програми {program_id}: {e}")
            conn.rollback()
            # Альтернативний спосіб: спробуємо без foreign key
            try:
                # Тимчасово вимкнути foreign keys
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute('DELETE FROM version_history WHERE program_id = ?', (program_id,))
                cursor.execute('DELETE FROM programs WHERE id = ?', (program_id,))
                cursor.execute("PRAGMA foreign_keys = ON")
                conn.commit()
                return True
            except Exception as e2:
                print(f"❌ Критична помилка при видаленні: {e2}")
                return False
    
    def close_all_connections(self):
        """Закрити всі з'єднання з БД"""
        if hasattr(self.local_storage, 'connection'):
            self.local_storage.connection.close()
            del self.local_storage.connection
            del self.local_storage.cursor

# Для тестування
if __name__ == "__main__":
    db = Database()
    print("✅ База даних створена успішно!")
    
    # Тестові дані
    try:
        db.add_program(
            "Grandstream GXP1625", 
            "Мережевий пристрій", 
            "https://www.grandstream.com/support/firmware",
            "1.0.7.79",
            "",
            1
        )
        
        print("✅ Додані тестові програми:")
        for program in db.get_all_programs():
            print(f"ID: {program[0]}, Назва: {program[1]}")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
    
    db.close_all_connections()