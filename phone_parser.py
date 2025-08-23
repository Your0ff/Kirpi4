import time
import os
import re
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import *  # Импортируем все настройки из config.py


class PhoneNumberParser:
    def __init__(self):
        """Инициализация парсера с настройкой Selenium"""
        self.setup_driver()

    def setup_driver(self):
        """Настройка Chrome WebDriver"""
        chrome_options = Options()

        # Настройка фонового режима из конфигурации
        if HEADLESS_MODE:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Автоматическая установка ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def login(self, start_page=None):
        print("🔐 Выполнение авторизации...")
        self.driver.get("https://secondtg.org/login")
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.clear()
            email_field.send_keys(EMAIL)
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(PASSWORD)
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_button.click()

            # Ждем и проверяем успешность авторизации
            WebDriverWait(self.driver, 10).until(
                lambda d: "login" not in d.current_url.lower()
            )

            print("✅ Авторизация прошла успешно!")

            # Переходим на нужную стартовую страницу
            page_to_load = start_page if start_page is not None else START_PAGE
            print(f"🚀 Прямой переход на страницу {page_to_load}")
            first_page_url = f"{BASE_URL}?page={page_to_load}"
            self.driver.get(first_page_url)

            return True
        except Exception as e:
            print(f"❌ Ошибка при авторизации: {e}")
            return False

    def parse_all_pages(self, start_page=None, end_page=None):
        # Используем переданные параметры или значения из конфига
        start = start_page if start_page is not None else START_PAGE
        end = end_page if end_page is not None else END_PAGE

        all_phone_data = []
        for page_num in range(start, end + 1):
            # Для первой страницы не делаем переход, так как мы уже на ней после login()
            if page_num != start:
                print(f"🔍 Переход на страницу {page_num}...")
                page_url = f"{BASE_URL}?page={page_num}"
                self.driver.get(page_url)
            else:
                print(f"🔍 Парсинг текущей страницы {page_num}...")

            # Ждем полной загрузки страницы и парсим номера с ID
            page_data = self.wait_and_parse_page()
            all_phone_data.extend(page_data)
            print(f"✅ Страница {page_num}: {len(page_data)} номеров")

        print(f"🎯 Всего найдено номеров: {len(all_phone_data)}")
        return all_phone_data

    def wait_and_parse_page(self):
        """Ждет загрузки страницы и парсит номера с ID"""
        try:
            # Ждем появления основного контента страницы
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".order-item")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".list-group")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".content")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".container"))
                )
            )

            # Парсим страницу до тех пор, пока не найдем достаточное количество номеров
            max_attempts = 30  # максимум 15 секунд ожидания (30 * 0.5)
            expected_numbers = getattr(sys.modules.get('config'), 'EXPECTED_NUMBERS_PER_PAGE', 15)

            for attempt in range(max_attempts):
                page_source = self.driver.page_source
                current_data = self.extract_phone_numbers_with_ids(page_source)
                current_count = len(current_data)

                # Если найдено достаточное количество номеров - возвращаем результат
                if current_count >= expected_numbers:
                    return current_data

                # Если это последняя попытка - возвращаем что есть
                if attempt == max_attempts - 1:
                    print(f"⚠️ Найдено только {current_count} номеров (ожидалось {expected_numbers})")
                    return current_data

                time.sleep(0.5)  # Короткая пауза между проверками

            return []

        except Exception as e:
            print(f"❌ Ошибка при парсинге страницы: {e}")
            # В случае ошибки пытаемся спарсить то, что есть
            try:
                page_source = self.driver.page_source
                return self.extract_phone_numbers_with_ids(page_source)
            except:
                return []

    def extract_phone_numbers_with_ids(self, html_content):
        """Извлекает номера телефонов и соответствующие им ID"""
        phone_data = []

        # Паттерн для поиска номеров телефонов
        phone_pattern = rf'{re.escape(PHONE_PREFIX)}[0-9\s\-\(\)\.]+'
        # Паттерн для поиска ID
        id_pattern = r'<h4 class="order_id">ID: (\d+)</h4>'

        # Находим все номера телефонов
        phone_matches = list(re.finditer(phone_pattern, html_content))
        # Находим все ID
        id_matches = list(re.finditer(id_pattern, html_content))

        # Создаем словарь для связывания номеров с ID по позиции в тексте
        phone_positions = []
        for match in phone_matches:
            cleaned_number = re.sub(r'[^\d\+]', '', match.group())
            if cleaned_number.startswith(PHONE_PREFIX):
                phone_positions.append({
                    'number': cleaned_number,
                    'position': match.start()
                })

        id_positions = []
        for match in id_matches:
            id_positions.append({
                'id': match.group(1),
                'position': match.start()
            })

        # Связываем номера с ближайшими ID
        used_numbers = set()
        for phone_info in phone_positions:
            phone_number = phone_info['number']
            phone_pos = phone_info['position']

            # Избегаем дублирования номеров
            if phone_number in used_numbers:
                continue

            # Ищем ближайший ID (обычно ID идет перед номером)
            closest_id = None
            min_distance = float('inf')

            for id_info in id_positions:
                id_pos = id_info['position']
                # Рассматриваем ID, которые находятся перед номером или недалеко после
                distance = abs(phone_pos - id_pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_id = id_info['id']

            if closest_id:
                phone_data.append({
                    'number': phone_number,
                    'id': closest_id
                })
                used_numbers.add(phone_number)

        return phone_data

    def save_results(self, phone_data, phones_per_page=15):
        os.makedirs('data', exist_ok=True)
        txt_path = os.path.join('data', 'phone_numbers.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            total = len(phone_data)
            page = START_PAGE
            for i, data in enumerate(phone_data, 1):
                if (i - 1) % phones_per_page == 0:
                    if i != 1:
                        f.write('\n')
                    f.write(f"=== Страница {page} ===\n")
                    page += 1
                f.write(f"{i}. +{data['number']} ID: {data['id']}\n")
        print(f"✅ Результаты сохранены в {txt_path}")

    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    parser = PhoneNumberParser()
    try:
        if not parser.login():
            return
        # После логина мы уже на первой странице orders, начинаем парсинг
        phone_data = parser.parse_all_pages()
        print(f"Всего номеров найдено: {len(phone_data)}")
        parser.save_results(phone_data)
    finally:
        parser.close()


if __name__ == "__main__":
    main()
