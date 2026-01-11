import sys
import os

os.environ["QT_FATAL_WARNINGS"] = "0"  # Вимкнути фатальні попередження
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"  # Вимкнути деякі логування

import json
import re
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QTextEdit,
                             QComboBox, QMessageBox, QGroupBox, QFormLayout,
                             QHeaderView, QTabWidget, QInputDialog, QDialog,
                             QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from database import Database
from parser import VersionParser

class EditProgramDialog(QDialog):
    """Діалогове вікно для редагування всіх параметрів програми"""
    def __init__(self, parent=None, program_data=None):
        super().__init__(parent)
        self.parent = parent
        self.program_data = program_data  # (id, name, category, url, current_version, installed_version, selector, last_check)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Редагування програми")
        self.setFixedSize(550, 450)
        
        layout = QVBoxLayout()
        
        # Форма для редагування даних
        form_group = QGroupBox("Редагувати інформацію про програму")
        form_layout = QFormLayout()
        
        # Назва програми
        self.name_input = QLineEdit()
        if self.program_data:
            self.name_input.setText(self.program_data[1])
        self.name_input.setPlaceholderText("Наприклад: Grandstream GXP1625")
        form_layout.addRow("Назва програми:", self.name_input)
        
        # Категорія
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Програма",
            "Прошивка", 
            "Мережевий пристрій",
            "Операційна система",
            "Бібліотека",
            "Інше"
        ])
        if self.program_data:
            index = self.category_combo.findText(self.program_data[2])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        form_layout.addRow("Категорія:", self.category_combo)
        
        # URL
        self.url_input = QLineEdit()
        if self.program_data:
            self.url_input.setText(self.program_data[3])
        self.url_input.setPlaceholderText("https://приклад.com/завантаження")
        form_layout.addRow("URL сторінки завантаження:", self.url_input)
        
        # Поточна версія (тільки для перегляду)
        current_version_label = QLabel()
        if self.program_data:
            current_version_label.setText(self.program_data[4] or "Не перевірено")
        form_layout.addRow("Поточна версія (автоматично):", current_version_label)
        
        # Встановлена версія
        self.installed_version_input = QLineEdit()
        if self.program_data:
            self.installed_version_input.setText(self.program_data[5] or "")
        self.installed_version_input.setPlaceholderText("Наприклад: 1.2.3")
        form_layout.addRow("Встановлена версія:", self.installed_version_input)
        
        # Селектор
        self.selector_input = QLineEdit()
        if self.program_data:
            self.selector_input.setText(self.program_data[6] or "")
        self.selector_input.setPlaceholderText("CSS селектор (необов'язково)")
        form_layout.addRow("Селектор версії:", self.selector_input)
        
        # Остання перевірка (тільки для перегляду)
        last_check_label = QLabel()
        if self.program_data:
            last_check = self.program_data[7] or "Ніколи"
            last_check_label.setText(last_check)
        form_layout.addRow("Остання перевірка:", last_check_label)
        
        # Статус активності
        self.active_checkbox = QComboBox()
        self.active_checkbox.addItems(["Активна", "Неактивна"])
        form_layout.addRow("Статус:", self.active_checkbox)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def get_updated_data(self):
        """Отримати оновлені дані з форми"""
        return {
            'name': self.name_input.text().strip(),
            'category': self.category_combo.currentText(),
            'url': self.url_input.text().strip(),
            'installed_version': self.installed_version_input.text().strip(),
            'selector': self.selector_input.text().strip(),
            'is_active': 1 if self.active_checkbox.currentText() == "Активна" else 0
        }

class VersionCheckThread(QThread):
    """Окремий потік для перевірки версій"""
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    version_checked = pyqtSignal(int, str, bool)  # program_id, version, is_changed
    
    def __init__(self, db, programs_to_check):
        super().__init__()
        self.db = db
        self.programs = programs_to_check
        self.parser = VersionParser()
        self.running = True
    
    def run(self):
        """Запуск потоку"""
        try:
            checked = 0
            updated = 0
            
            for program in self.programs:
                if not self.running:
                    break
                    
                program_id = program[0]
                name = program[1]
                url = program[3]
                selector = program[6]
                
                self.progress.emit(f"Перевіряю {name}...")
                
                # СПЕЦІАЛЬНА ОБРОБКА ДЛЯ GRANDSTREAM
                if 'grandstream.com' in url:
                    # Вилучаємо модель з назви програми
                    model_match = re.search(r'Grandstream\s+([A-Z0-9]+(?:\s+v\d+)?)', name)
                    if model_match:
                        model = model_match.group(1)
                        version = self.parser.get_grandstream_version(model)
                    else:
                        # Якщо не вдалося вилучити модель, використовуємо стандартний метод
                        version = self.parser.get_version_from_website(url, selector)
                else:
                    # Для інших сайтів - стандартна логіка
                    version = self.parser.get_version_from_website(url, selector)
                
                if version:
                    # Перевіряємо, чи змінилася версія
                    current_version = program[4]
                    is_changed = version != current_version
                    
                    if is_changed:
                        self.db.update_version(program_id, version)
                        updated += 1
                        self.progress.emit(f"✅ Оновлено {name}: {version}")
                    
                    # Сигнал для оновлення інтерфейсу
                    self.version_checked.emit(program_id, version, is_changed)
                    checked += 1
                else:
                    self.progress.emit(f"⚠️ Не знайдено версію для {name}")
                
                # Маленька затримка між запитами
                self.msleep(1000)
            
            self.progress.emit(f"✅ Готово! Перевірено {checked}, оновлено {updated}")
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        """Зупинити потік"""
        self.running = False

class AddProgramDialog(QDialog):
    """Діалогове вікно для додавання нової програми"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Додати нову програму")
        self.setFixedSize(550, 450)
        
        layout = QVBoxLayout()
        
        # Форма для введення даних
        form_group = QGroupBox("Інформація про програму")
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Наприклад: Grandstream GXP1625, Python, VLC")
        form_layout.addRow("Назва програми:", self.name_input)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Програма",
            "Прошивка", 
            "Мережевий пристрій",
            "Операційна система",
            "Бібліотека",
            "Інше"
        ])
        form_layout.addRow("Категорія:", self.category_combo)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://приклад.com/завантаження")
        form_layout.addRow("URL сторінки завантаження:", self.url_input)
        
        self.installed_version_input = QLineEdit()
        self.installed_version_input.setPlaceholderText("Наприклад: 1.2.3")
        form_layout.addRow("Встановлена версія:", self.installed_version_input)
        
        self.selector_input = QLineEdit()
        self.selector_input.setPlaceholderText("CSS селектор (необов'язково)")
        form_layout.addRow("Селектор версії:", self.selector_input)
        
        # Пояснення про формат для Grandstream
        help_label = QLabel(
            "Для Grandstream пристроїв вкажіть назву у форматі: 'Grandstream GXP1625'\n"
            "URL: https://www.grandstream.com/support/firmware\n"
            "Селектор: залиште порожнім\n\n"
            "Статус 'Активна' означає, що програма буде перевірятися автоматично."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #0066cc; font-size: 10px; padding: 5px; background-color: #f0f8ff; border-radius: 3px;")
        form_layout.addRow("", help_label)
        
        # Статус активності
        self.active_checkbox = QComboBox()
        self.active_checkbox.addItems(["Активна", "Неактивна"])
        self.active_checkbox.setCurrentText("Активна")
        form_layout.addRow("Статус:", self.active_checkbox)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def get_program_data(self):
        """Отримати дані програми з форми"""
        return {
            'name': self.name_input.text().strip(),
            'category': self.category_combo.currentText(),
            'url': self.url_input.text().strip(),
            'installed_version': self.installed_version_input.text().strip(),
            'selector': self.selector_input.text().strip(),
            'is_active': 1 if self.active_checkbox.currentText() == "Активна" else 0
        }

class MainWindow(QMainWindow):
    """Головне вікно програми"""
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.check_thread = None
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        self.setWindowTitle("Version Checker v2.0")
        self.setGeometry(100, 100, 1200, 700)
        
        # Центральний віджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        
        # Заголовок
        title_label = QLabel("🔍 Моніторинг версій програм")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            margin: 15px;
            color: #2c3e50;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Статусна панель
        self.status_label = QLabel("Готово до роботи")
        self.status_label.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
            font-weight: bold;
        """)
        main_layout.addWidget(self.status_label)
        
        # Кнопки управління
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("➕ Додати")
        self.add_button.setToolTip("Додати нову програму для моніторингу")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.add_button.clicked.connect(self.open_add_dialog)
        
        self.edit_button = QPushButton("✏️ Редагувати")
        self.edit_button.setToolTip("Редагувати всі параметри обраної програми")
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        self.edit_button.clicked.connect(self.edit_selected_program)
        
        self.check_all_button = QPushButton("🔍 Всі")
        self.check_all_button.setToolTip("Перевірити всі активні програми")
        self.check_all_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.check_all_button.clicked.connect(self.check_all_programs)
        
        self.check_single_button = QPushButton("🔎 Обране")
        self.check_single_button.setToolTip("Перевірити тільки обрану програму")
        self.check_single_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.check_single_button.clicked.connect(self.check_selected_program)
        
        self.edit_version_button = QPushButton("🔄 Версія")
        self.edit_version_button.setToolTip("Редагувати тільки встановлену версію")
        self.edit_version_button.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        self.edit_version_button.clicked.connect(self.edit_installed_version)
        
        self.delete_button = QPushButton("🗑️ Видалити")
        self.delete_button.setToolTip("Видалити обрану програму")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.delete_button.clicked.connect(self.delete_selected)
        
        # Додавання кнопок у layout
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.check_all_button)
        button_layout.addWidget(self.check_single_button)
        button_layout.addWidget(self.edit_version_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Створюємо таблицю
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Назва", "Категорія", "Поточна версія", 
            "Встановлена версія", "Остання перевірка", "Статус", "URL", "Активна"
        ])
        
        # Налаштування таблиці
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Назва
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)  # URL
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)
        
        main_layout.addWidget(self.table)
        
        # Статистика
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Всього програм: 0")
        self.updated_label = QLabel("Потребують оновлення: 0")
        self.active_label = QLabel("Активних: 0")
        self.last_check_label = QLabel("Остання перевірка: Ніколи")
        
        for label in [self.total_label, self.updated_label, self.active_label, self.last_check_label]:
            label.setStyleSheet("color: #6c757d; font-size: 11px; font-weight: bold;")
            stats_layout.addWidget(label)
        
        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)
        
        central_widget.setLayout(main_layout)
        
        # Статус бар
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готово")
        
        # Завантажуємо програми при старті
        self.load_programs()
    
    def load_config(self):
        """Завантажити конфігурацію"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "auto_check_interval": 1440,
                    "timeout": 30
                }
        except:
            self.config = {}
    
    def load_programs(self):
        """Завантажити програми з БД в таблицю"""
        try:
            programs = self.db.get_all_programs()
            
            self.table.setRowCount(len(programs))
            
            need_update_count = 0
            active_count = 0
            last_check_time = None
            
            for row, program in enumerate(programs):
                # Заповнюємо комірки
                self.table.setItem(row, 0, QTableWidgetItem(str(program[0])))  # ID
                self.table.setItem(row, 1, QTableWidgetItem(program[1]))      # Назва
                self.table.setItem(row, 2, QTableWidgetItem(program[2]))      # Категорія
                
                # Поточна версія
                current_version_item = QTableWidgetItem(program[4] or "Не перевірено")
                self.table.setItem(row, 3, current_version_item)
                
                # Встановлена версія
                installed_version_item = QTableWidgetItem(program[5] or "")
                self.table.setItem(row, 4, installed_version_item)
                
                # Остання перевірка
                last_check = program[7]
                if last_check:
                    last_check_time = last_check
                    try:
                        dt = datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S")
                        last_check_str = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        last_check_str = last_check
                else:
                    last_check_str = "Ніколи"
                
                self.table.setItem(row, 5, QTableWidgetItem(last_check_str))
                
                # URL (скорочено)
                url = program[3]
                if len(url) > 40:
                    url_display = url[:37] + "..."
                else:
                    url_display = url
                url_item = QTableWidgetItem(url_display)
                url_item.setToolTip(url)  # Повний URL при наведенні
                self.table.setItem(row, 7, url_item)
                
                # Активність
                is_active = program[8] if len(program) > 8 else 1
                active_item = QTableWidgetItem("Так" if is_active else "Ні")
                active_item.setTextAlignment(Qt.AlignCenter)
                if is_active:
                    active_item.setBackground(QColor(212, 237, 218))
                    active_item.setForeground(QColor(21, 87, 36))
                    active_count += 1
                else:
                    active_item.setBackground(QColor(220, 220, 220))
                    active_item.setForeground(QColor(108, 117, 125))
                self.table.setItem(row, 8, active_item)
                
                # Визначаємо статус оновлення
                current = program[4] or ""
                installed = program[5] or ""
                
                status_item = QTableWidgetItem()
                if not current:
                    status_item.setText("Не перевірено")
                    status_item.setBackground(QColor(Qt.yellow))  # Світло-жовтий
                    status_item.setForeground(Qt.black)
                elif not installed:
                    status_item.setText("Версія не вказана")
                    status_item.setBackground(QColor(220, 220, 220))  # Сірий
                    status_item.setForeground(Qt.black)
                elif current == installed:
                    status_item.setText("Актуальна")
                    status_item.setBackground(QColor(212, 237, 218))  # Світло-зелений
                    status_item.setForeground(QColor(21, 87, 36))
                else:
                    status_item.setText("Потрібно оновити")
                    status_item.setBackground(QColor(248, 215, 218))  # Світло-червоний
                    status_item.setForeground(QColor(114, 28, 36))
                    need_update_count += 1
                
                self.table.setItem(row, 6, status_item)
            
            # Оновлюємо статистику
            self.total_label.setText(f"Всього програм: {len(programs)}")
            self.updated_label.setText(f"Потребують оновлення: {need_update_count}")
            self.active_label.setText(f"Активних: {active_count}")
            
            if last_check_time:
                self.last_check_label.setText(f"Остання перевірка: {last_check_time}")
            
            self.status_bar.showMessage(f"Завантажено {len(programs)} програм")
            
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити програми: {str(e)}")
    
    def get_selected_program_data(self):
        """Отримати дані обраної програми"""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Попередження", "Оберіть програму для редагування")
            return None
        
        row = selected_rows[0].row()
        program_id = int(self.table.item(row, 0).text())
        
        # Знаходимо програму в базі даних
        programs = self.db.get_all_programs()
        for program in programs:
            if program[0] == program_id:
                return program
        
        return None
    
    def open_add_dialog(self):
        """Відкрити діалог додавання програми"""
        dialog = AddProgramDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            program_data = dialog.get_program_data()
            
            # Валідація даних
            if not program_data['name'] or not program_data['url']:
                QMessageBox.warning(self, "Помилка", "Будь ласка, заповніть назву та URL")
                return
            
            if not program_data['url'].startswith(('http://', 'https://')):
                QMessageBox.warning(self, "Помилка", "URL має починатися з http:// або https://")
                return
            
            # Додаємо програму
            self.db.add_program(
                program_data['name'],
                program_data['category'],
                program_data['url'],
                program_data['installed_version'],
                program_data['selector'],
                program_data['is_active']
            )
            
            QMessageBox.information(self, "Успіх", "Програма додана успішно!")
            self.load_programs()
    
    def edit_selected_program(self):
        """Редагувати всі параметри обраної програми"""
        program_data = self.get_selected_program_data()
        if not program_data:
            return
        
        dialog = EditProgramDialog(self, program_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_updated_data()
            
            # Валідація даних
            if not updated_data['name'] or not updated_data['url']:
                QMessageBox.warning(self, "Помилка", "Назва та URL не можуть бути порожніми")
                return
            
            if not updated_data['url'].startswith(('http://', 'https://')):
                QMessageBox.warning(self, "Помилка", "URL має починатися з http:// або https://")
                return
            
            # Оновлюємо програму в базі даних
            self.db.update_program(
                program_data[0],  # program_id
                updated_data['name'],
                updated_data['category'],
                updated_data['url'],
                updated_data['installed_version'],
                updated_data['selector'],
                updated_data['is_active']
            )
            
            QMessageBox.information(self, "Успіх", "Програма оновлена успішно!")
            self.load_programs()
    
    def edit_installed_version(self):
        """Редагувати тільки встановлену версію"""
        program_data = self.get_selected_program_data()
        if not program_data:
            return
        
        current_version = program_data[5] or ""
        
        # Діалогове вікно для введення версії
        new_version, ok = QInputDialog.getText(
            self,
            f"Редагування версії - {program_data[1]}",
            "Введіть встановлену версію:",
            QLineEdit.Normal,
            current_version
        )
        
        if ok and new_version.strip():
            self.db.update_installed_version(program_data[0], new_version.strip())
            self.load_programs()
            self.status_bar.showMessage("Версія оновлена")
            QMessageBox.information(self, "Успіх", f"Версія для {program_data[1]} оновлена!")
    
    def check_all_programs(self):
        """Перевірити версії всіх активних програм"""
        if self.check_thread and self.check_thread.isRunning():
            QMessageBox.warning(self, "Увага", "Перевірка вже виконується!")
            return
        
        programs = self.db.get_active_programs()
        if not programs:
            QMessageBox.information(self, "Інформація", "Немає активних програм для перевірки")
            return
        
        # Запускаємо перевірку в окремому потоці
        self.check_thread = VersionCheckThread(self.db, programs)
        self.check_thread.progress.connect(self.update_status)
        self.check_thread.finished.connect(self.on_check_finished)
        self.check_thread.error.connect(self.on_check_error)
        self.check_thread.version_checked.connect(self.on_version_checked)
        
        self.check_all_button.setEnabled(False)
        self.check_all_button.setText("⏳ Перевірка...")
        self.status_label.setText("Почато перевірку версій...")
        
        self.check_thread.start()
    
    def check_selected_program(self):
        """Перевірити тільки обрану програму"""
        program_data = self.get_selected_program_data()
        if not program_data:
            return
        
        if self.check_thread and self.check_thread.isRunning():
            QMessageBox.warning(self, "Увага", "Перевірка вже виконується!")
            return
        
        # Перевіряємо, чи програма активна
        is_active = program_data[8] if len(program_data) > 8 else 1
        if not is_active:
            reply = QMessageBox.question(
                self,
                "Програма неактивна",
                "Ця програма позначена як неактивна. Все одно перевірити?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Запускаємо перевірку для однієї програми
        self.check_thread = VersionCheckThread(self.db, [program_data])
        self.check_thread.progress.connect(self.update_status)
        self.check_thread.finished.connect(self.on_check_finished)
        self.check_thread.error.connect(self.on_check_error)
        self.check_thread.version_checked.connect(self.on_version_checked)
        
        self.check_single_button.setEnabled(False)
        self.check_single_button.setText("⏳ Перевірка...")
        self.status_label.setText(f"Перевіряю {program_data[1]}...")
        
        self.check_thread.start()
    
    def update_status(self, message):
        """Оновити статус перевірки"""
        self.status_label.setText(message)
        self.status_bar.showMessage(message)
    
    def on_version_checked(self, program_id, version, is_changed):
        """Обробник перевірки окремої версії"""
        # Оновлюємо відповідний рядок у таблиці
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == str(program_id):
                # Оновлюємо поточну версію
                self.table.setItem(row, 3, QTableWidgetItem(version))
                
                # Оновлюємо статус
                current = version
                installed_item = self.table.item(row, 4)
                installed = installed_item.text() if installed_item else ""
                
                status_item = QTableWidgetItem()
                if not current:
                    status_item.setText("Не перевірено")
                    status_item.setBackground(QColor(255, 255, 204))
                    status_item.setForeground(Qt.black)
                elif not installed:
                    status_item.setText("Версія не вказана")
                    status_item.setBackground(QColor(220, 220, 220))
                    status_item.setForeground(Qt.black)
                elif current == installed:
                    status_item.setText("Актуальна")
                    status_item.setBackground(QColor(212, 237, 218))
                    status_item.setForeground(QColor(21, 87, 36))
                else:
                    status_item.setText("Потрібно оновити")
                    status_item.setBackground(QColor(248, 215, 218))
                    status_item.setForeground(QColor(114, 28, 36))
                
                self.table.setItem(row, 6, status_item)
                break
    
    def on_check_finished(self):
        """Обробник завершення перевірки"""
        self.check_all_button.setEnabled(True)
        self.check_all_button.setText("🔍 Всі")
        self.check_single_button.setEnabled(True)
        self.check_single_button.setText("🔎 Обране")
        self.status_label.setText("Перевірка завершена")
        self.load_programs()  # Оновити всю таблицю
        
        QMessageBox.information(self, "Готово", "Перевірка версій завершена!")
    
    def on_check_error(self, error_message):
        """Обробник помилки перевірки"""
        self.check_all_button.setEnabled(True)
        self.check_all_button.setText("🔍 Всі")
        self.check_single_button.setEnabled(True)
        self.check_single_button.setText("🔎 Обране")
        self.status_label.setText("Помилка при перевірці")
        
        QMessageBox.critical(self, "Помилка", f"Сталася помилка: {error_message}")
    
    def delete_selected(self):
        """Видалити обрану програму"""
        program_data = self.get_selected_program_data()
        if not program_data:
            return
        
        reply = QMessageBox.question(
            self, 
            "Підтвердження видалення",
            f"Ви впевнені, що хочете видалити програму:\n\n"
            f"Назва: {program_data[1]}\n"
            f"Категорія: {program_data[2]}\n\n"
            f"Цю дію неможливо скасувати!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.delete_program(program_data[0])
            self.load_programs()
            self.status_bar.showMessage(f"Програма '{program_data[1]}' видалена")
    
    def closeEvent(self, event):
        """Обробник закриття вікна"""
        # Зупиняємо потік перевірки, якщо він працює
        if self.check_thread and self.check_thread.isRunning():
            self.check_thread.stop()
            self.check_thread.wait(2000)  # Чекаємо до 2 секунд
        
        self.db.close_all_connections()  
        event.accept()

def main():
    # Створюємо QApplication
    app = QApplication(sys.argv)
    
    # Налаштовуємо стиль
    app.setStyle('Fusion')
    
    # Створюємо головне вікно
    window = MainWindow()
    window.show()
    
     # Запускаємо цикл подій
    sys.exit(app.exec_())

class Worker(QThread):
    """Робітник для обробки одного завдання"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class VersionChecker:
    """Клас для перевірки версій (не успадковує QThread)"""
    def __init__(self, db):
        self.db = db
        self.parser = VersionParser()
    
    def check_program(self, program):
        """Перевірити одну програму"""
        program_id = program[0]
        name = program[1]
        url = program[3]
        selector = program[6]
        
        # СПЕЦІАЛЬНА ОБРОБКА ДЛЯ GRANDSTREAM
        if 'grandstream.com' in url:
            # Вилучаємо модель з назви програми
            model_match = re.search(r'Grandstream\s+([A-Z0-9]+(?:\s+v\d+)?)', name)
            if model_match:
                model = model_match.group(1)
                version = self.parser.get_grandstream_version(model)
            else:
                # Якщо не вдалося вилучити модель, використовуємо стандартний метод
                version = self.parser.get_version_from_website(url, selector)
        else:
            # Для інших сайтів - стандартна логіка
            version = self.parser.get_version_from_website(url, selector)
        
        result = {
            'program_id': program_id,
            'name': name,
            'version': version,
            'success': version is not None
        }
        
        if version:
            # Перевіряємо, чи змінилася версія
            current_version = program[4]
            if version != current_version:
                self.db.update_version(program_id, version)
                result['updated'] = True
                result['old_version'] = current_version
            else:
                result['updated'] = False
            
            # Оновлюємо час останньої перевірки
            self.db.update_last_check(program_id)
        
        return result


if __name__ == "__main__":
    main()