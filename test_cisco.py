# test_cisco.py
import requests
from bs4 import BeautifulSoup
import re

def test_cisco_parsing():
    url = "https://software.cisco.com/services/catalog/v1/releases?mdfid=286311068&softwareId=282463182&ts=8FCQIIHKKYJ9ZDQABGT1768151561520"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"🔗 Запит до: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Збережіть HTML для аналізу
            with open('cisco_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("✅ HTML збережено в cisco_page.html")
            
            # Простий пошук версії
            patterns = [
                r'Release\s+(\d+\.\d+[\.\d]*)',
                r'Version\s+(\d+\.\d+[\.\d]*)',
                r'v?(\d+\.\d+\.\d+\.\d+)',
                r'IOS\s+XE\s+(\d+\.\d+[\.\d]*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    print(f"✅ Знайдено версії: {matches}")
                    return matches[0]
            
            print("❌ Версію не знайдено в HTML")
            
        else:
            print(f"❌ HTTP помилка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    version = test_cisco_parsing()
    print(f"\n🎯 Результат: {version}")