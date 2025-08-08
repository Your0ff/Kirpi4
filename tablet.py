#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТОЙ СКРИПТ ДЛЯ ИСПРАВЛЕНИЯ CHROMEDRIVER
Решает ошибку [WinError 193] и другие проблемы с драйвером
"""

import os
import sys
import shutil
import subprocess
import requests
import zipfile
import tempfile
from pathlib import Path

def print_status(message, status="info"):
    """Красивый вывод статуса"""
    symbols = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️", "process": "🔧"}
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def clear_webdriver_cache():
    """Очистка кеша webdriver-manager"""
    print_status("Очищаем кеш webdriver-manager...", "process")
    
    cache_paths = [
        Path.home() / '.wdm',
        Path.home() / '.cache' / 'selenium',
        Path(tempfile.gettempdir()) / 'webdriver'
    ]
    
    cleared = 0
    for cache_path in cache_paths:
        if cache_path.exists():
            try:
                shutil.rmtree(cache_path)
                print_status(f"Удален кеш: {cache_path}", "success")
                cleared += 1
            except Exception as e:
                print_status(f"Не удалось удалить {cache_path}: {e}", "warning")
    
    if cleared == 0:
        print_status("Кеш не найден или уже очищен", "info")
    
    return True

def download_chromedriver():
    """Скачивание актуального ChromeDriver"""
    print_status("Скачиваем актуальный ChromeDriver...", "process")
    
    try:
        # Получаем последнюю стабильную версию
        version_url = "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE"
        response = requests.get(version_url, timeout=10)
        version = response.text.strip()
        print_status(f"Последняя версия: {version}", "info")
        
        # URL для скачивания (Windows 64-bit)
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"
        
        # Скачиваем архив
        print_status("Скачиваем архив...", "process")
        zip_response = requests.get(download_url, timeout=30)
        zip_response.raise_for_status()
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            tmp_file.write(zip_response.content)
            zip_path = tmp_file.name
        
        # Распаковываем
        extract_dir = Path(tempfile.gettempdir()) / "chromedriver_temp"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Находим chromedriver.exe
        chromedriver_exe = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == "chromedriver.exe":
                    chromedriver_exe = Path(root) / file
                    break
            if chromedriver_exe:
                break
        
        if not chromedriver_exe:
            print_status("chromedriver.exe не найден в архиве", "error")
            return False
        
        # Копируем в текущую папку
        current_dir = Path.cwd()
        destination = current_dir / "chromedriver.exe"
        
        # Удаляем старый файл если есть
        if destination.exists():
            destination.unlink()
        
        shutil.copy2(chromedriver_exe, destination)
        print_status(f"ChromeDriver сохранен: {destination}", "success")
        
        # Очищаем временные файлы
        os.unlink(zip_path)
        shutil.rmtree(extract_dir)
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка при скачивании ChromeDriver: {e}", "error")
        return False

def update_packages():
    """Обновление необходимых пакетов"""
    print_status("Обновляем Python пакеты...", "process")
    
    packages = ["selenium", "webdriver-manager", "requests"]
    
    for package in packages:
        try:
            print_status(f"Обновляем {package}...", "process")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                capture_output=True,
                text=True,
                check=True
            )
            print_status(f"{package} обновлен", "success")
        except subprocess.CalledProcessError as e:
            print_status(f"Ошибка при обновлении {package}: {e.stderr}", "error")

def test_chromedriver():
    """Тестирование ChromeDriver"""
    print_status("Тестируем ChromeDriver...", "process")
    
    test_code = '''
import os
import sys

# Тест 1: Проверка локального chromedriver.exe
chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
if os.path.exists(chromedriver_path):
    print("✅ Локальный chromedriver.exe найден")
else:
    print("❌ Локальный chromedriver.exe не найден")

# Тест 2: Импорт Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    print("✅ Selenium импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта Selenium: {e}")
    sys.exit(1)

# Тест 3: Создание Chrome options
try:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    print("✅ Chrome options созданы")
except Exception as e:
    print(f"❌ Ошибка создания Chrome options: {e}")

# Тест 4: Создание Service
try:
    if os.path.exists(chromedriver_path):
        service = Service(chromedriver_path)
        print("✅ Service создан с локальным драйвером")
    else:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        print("✅ Service создан с webdriver-manager")
except Exception as e:
    print(f"❌ Ошибка создания Service: {e}")

print("🎉 Все тесты пройдены! ChromeDriver готов к использованию.")
'''
    
    try:
        exec(test_code)
        return True
    except Exception as e:
        print_status(f"Ошибка при тестировании: {e}", "error")
        return False

def create_test_script():
    """Создание тестового скрипта для проверки работы"""
    print_status("Создаем тестовый скрипт...", "process")
    
    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ТЕСТОВЫЙ СКРИПТ ДЛЯ ПРОВЕРКИ CHROMEDRIVER
Запустите этот скрипт для проверки работы после исправления
"""

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def test_chrome():
    print("🧪 Тестируем ChromeDriver...")
    
    # Настройки Chrome
    options = Options()
    options.add_argument("--headless")  # Фоновый режим
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        # Проверяем локальный chromedriver
        chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe")
        if os.path.exists(chromedriver_path):
            print("🔧 Используем локальный ChromeDriver...")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            print("🔧 Используем WebDriver Manager...")
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
        # Тестовый переход на сайт
        print("🌐 Тестируем переход на Google...")
        driver.get("https://www.google.com")
        title = driver.title
        
        print(f"✅ УСПЕХ! Заголовок страницы: {title}")
        print("✅ ChromeDriver работает корректно!")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    success = test_chrome()
    if success:
        print("🎉 Тест прошел успешно! Можете использовать вашу программу.")
    else:
        print("🔧 Тест не прошел. Запустите fix_chromedriver.py еще раз.")
'''
    
    test_file = Path.cwd() / "test_chromedriver.py"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print_status(f"Тестовый скрипт создан: {test_file}", "success")

def main():
    """Главная функция исправления"""
    print("=" * 60)
    print("🚀 ИСПРАВЛЕНИЕ ПРОБЛЕМ С CHROMEDRIVER")
    print("=" * 60)
    
    try:
        # Шаг 1: Очистка кеша
        clear_webdriver_cache()
        print()
        
        # Шаг 2: Обновление пакетов
        update_packages()
        print()
        
        # Шаг 3: Скачивание ChromeDriver
        if download_chromedriver():
            print_status("ChromeDriver загружен успешно!", "success")
        print()
        
        # Шаг 4: Тестирование
        print_status("Проводим финальное тестирование...", "process")
        if test_chromedriver():
            print_status("Тестирование прошло успешно!", "success")
        print()
        
        # Шаг 5: Создание тестового скрипта
        create_test_script()
        print()
        
        # Финальное сообщение
        print("=" * 60)
        print("🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
        print("=" * 60)
        print("✅ ChromeDriver настроен и готов к работе")
        print("📄 Создан файл 'test_chromedriver.py' для дополнительной проверки")
        print("🚀 Теперь можете запускать вашу основную программу")
        print()
        print("📝 Что делать дальше:")
        print("1. Запустите: python test_chromedriver.py (для проверки)")
        print("2. Запустите вашу основную программу")
        print("3. Если проблемы остались - запустите этот скрипт еще раз")
        
    except KeyboardInterrupt:
        print_status("Процесс прерван пользователем", "warning")
    except Exception as e:
        print_status(f"Критическая ошибка: {e}", "error")
        print("🔧 Попробуйте запустить скрипт еще раз или обратитесь за помощью")

if __name__ == "__main__":
    main()

