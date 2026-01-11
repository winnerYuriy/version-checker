from urllib.parse import urlparse
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
import time

class VersionParser:
    def __init__(self):
        self.session = requests.Session()
        # Додаємо заголовки, щоб сайти думали, що це браузер
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_version_from_website(self, url, selector=None):
        """Отримати версію з веб-сайту"""
        try:
            print(f"Перевіряю {url}...")
            
            # Затримка, щоб не перевантажувати сайти
            time.sleep(2)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()  # Перевірка на помилки HTTP
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Якщо задано CSS селектор
            if selector and selector.strip():
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    version = self.extract_version_from_text(text)
                    if version:
                        return version
            
            # Автоматичний пошук версії в тексті сторінки
            # Пошук паттернів версій: v1.2.3, version 2.0, 3.1.4, etc.
            patterns = [
                r'\b(\d+(?:\.\d+){1,3})\b',  # 1.2, 1.2.3, 1.2.3.4, 1.0.7.79
                r'v?(\d+\.\d+\.\d+)',  # 1.2.3
                r'v?(\d+\.\d+)',       # 1.2
                r'Version\s*[:]?\s*(\d+\.\d+\.\d+)',
                r'Версія\s*[:]?\s*(\d+\.\d+\.\d+)',
                r'(\d{4}\.\d+\.\d+)',  # 2023.1.0
            ]
            
            page_text = soup.get_text()
            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Беремо перше знайдене число як найімовірнішу версію
                    for match in matches:
                        if len(match) > 2:  # Мінімум 1.2
                            return match
            
            return None
            
        except requests.RequestException as e:
            print(f"Помилка при отриманні {url}: {e}")
            return None
        except Exception as e:
            print(f"Невідома помилка: {e}")
            return None
    
    def get_grandstream_version(self, model_name):
        """
        Спеціальна функція для отримання версії прошивки з сайту Grandstream
        за конкретною моделлю пристрою.
        
        Приклад використання:
            get_grandstream_version("GXP1625")
            get_grandstream_version("GXW4232")
        """
        url = "https://www.grandstream.com/support/firmware"
        print(f"🔍 Отримую дані для моделі {model_name} з {url}")
        
        try:
            # Завантажуємо сторінку
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Знаходимо ВСІ таблиці на сторінці
            tables = soup.find_all('table')
            
            # Нормалізуємо назву моделі для пошуку
            search_model = model_name.upper().replace(" ", "")
            
            for table in tables:
                # Шукаємо рядки таблиці
                rows = table.find_all('tr')
                
                for row in rows:
                    # Перша комірка в рядку зазвичай містить назви моделей
                    first_cell = row.find('td')
                    if not first_cell:
                        continue
                    
                    # Отримуємо текст комірки з моделями
                    models_text = first_cell.get_text(strip=True).upper()
                    
                    # Перевіряємо, чи наш пристрій вказаний у цьому списку
                    # Враховуємо формати запису: "GXP1610/1615", "GXP1620/1625"
                    # Створюємо список можливих назв для пошуку
                    possible_names = [search_model]
                    
                    # Якщо шукаємо GXP1625, додамо також GXP1620/1625
                    if "/" not in search_model:
                        # Додаємо варіант із слешем (для пошуку в рядках типу "GXP1620/1625")
                        base_model = re.match(r'([A-Z]+)\d+', search_model)
                        if base_model:
                            base = base_model.group(1)  # "GXP"
                            possible_names.append(base)
                    
                    # Флаг знаходження моделі
                    model_found = False
                    for name in possible_names:
                        if name and name in models_text:
                            model_found = True
                            break
                    
                    if model_found:
                        # Знайшли рядок з нашою моделлю
                        # Тепер шукаємо версію прошивки в цьому рядку
                        all_cells = row.find_all('td')
                        
                        # Версія зазвичай знаходиться в другій або третій комірці
                        for i, cell in enumerate(all_cells[1:], start=1):  # Починаємо з другої комірки
                            cell_text = cell.get_text(strip=True)
                            
                            # Шукаємо номер версії в тексті комірки
                            version = self.extract_version_from_text(cell_text)
                            if version:
                                print(f"✅ Знайдено версію для {model_name}: {version}")
                                return version
                        
                        # Якщо в комірках не знайшли чіткої версії, дивимось посилання
                        for cell in all_cells[1:]:
                            links = cell.find_all('a')
                            for link in links:
                                link_text = link.get_text(strip=True)
                                version = self.extract_version_from_text(link_text)
                                if version:
                                    print(f"✅ Знайдено версію для {model_name} в посиланні: {version}")
                                    return version
            
            # Якщо не знайшли конкретну модель, повертаємо None
            print(f"❌ Модель {model_name} не знайдена на сторінці")
            return None
            
        except Exception as e:
            print(f"❌ Помилка при парсингу Grandstream: {e}")
            return None

    def extract_version_from_text(self, text):
        """Витягнути номер версії з тексту"""
        patterns = [
                # 1. Версії з префіксом (v, version, версія)
                r'(?:v|version|версія|вірсія|release|реліз|build|білд)\s*[:=]?\s*v?(\d+(?:\.\d+)+)',
                
                # 2. Версії з 2-6 частинами (1.0, 1.0.7, 1.0.7.79, 1.0.7.79.1)
                r'\b(\d+(?:\.\d+){1,5})\b',
                
                # 3. Версії з датами (2024.01.15.1)
                r'\b(\d{4}(?:\.\d+){1,3})\b',
                
                # 4. Версії в дужках/квадратних дужках
                r'[\[(]v?(\d+(?:\.\d+)+)[])]',
                
                # 5. Версії з буквами (1.0.7a, 2.0-beta, 3.1.4-rc1)
                r'\b(\d+(?:\.\d+)+[a-zA-Z]*(?:-\w+)?)\b',
                
                # 6. Версії з роздільниками _ і -
                r'\b(\d+(?:[_.-]\d+)+)\b',
                
                # 7. Просто числа більше 1000 (може бути версією)
                r'\b(20\d{2}|\d{4,})\b',  # 2024, 12345
            ]
        

        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def check_specific_sites(self, url, name):
        """Спеціальні правила для популярних сайтів"""
        domain = urlparse(url).netloc.lower()
        
        # Grandstream
        if 'grandstream.com' in domain:
            # Тут ми не можемо визначити модель з URL, тому повертаємо None
            # Конкретна модель буде визначатися в основній програмі
            return None

        # Для GitHub
        if 'github.com' in url:
            try:
                # Формуємо API URL для GitHub
                repo_path = url.replace('https://github.com/', '')
                api_url = f"https://api.github.com/repos/{repo_path}/releases/latest"
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('tag_name', '').replace('v', '')
            except:
                pass
        
        # Для Docker Hub
        elif 'hub.docker.com' in url:
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                # Пошук версії на Docker Hub
                tag_elements = soup.select('.TagList__tag-name')
                if tag_elements:
                    return tag_elements[0].text.strip()
            except:
                pass
        
        return None

# Тестування парсера
if __name__ == "__main__":
    parser = VersionParser()
    
    # Тестуємо на Python сайті
    version = parser.get_version_from_website(
        "https://www.python.org/downloads/",
        ".download-for-current-os .download-number"
    )
    print(f"Версія Python: {version}")
    
    # Тестуємо без селектора
    version = parser.get_version_from_website("https://www.videolan.org/vlc/")
    print(f"Версія VLC: {version}")