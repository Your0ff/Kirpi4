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

        all_phone_numbers = []
        for page_num in range(start, end + 1):
            # Для первой страницы не делаем переход, так как мы уже на ней после login()
            if page_num != start:
                print(f"🔍 Переход на страницу {page_num}...")
                page_url = f"{BASE_URL}?page={page_num}"
                self.driver.get(page_url)
            else:
                print(f"🔍 Парсинг текущей страницы {page_num}...")

            # Ждем полной загрузки страницы и парсим номера
            page_numbers = self.wait_and_parse_page()
            all_phone_numbers.extend(page_numbers)
            print(f"✅ Страница {page_num}: {len(page_numbers)} номеров")

        print(f"🎯 Всего найдено номеров: {len(all_phone_numbers)}")
        return all_phone_numbers

    def wait_and_parse_page(self):
        """Ждет загрузки страницы и парсит номера"""
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
                current_numbers = self.extract_phone_numbers(page_source)
                current_count = len(current_numbers)

                # Если найдено достаточное количество номеров - возвращаем результат
                if current_count >= expected_numbers:
                    return current_numbers

                # Если это последняя попытка - возвращаем что есть
                if attempt == max_attempts - 1:
                    print(f"⚠️ Найдено только {current_count} номеров (ожидалось {expected_numbers})")
                    return current_numbers

                time.sleep(0.5)  # Короткая пауза между проверками

            return []

        except Exception as e:
            print(f"❌ Ошибка при парсинге страницы: {e}")
            # В случае ошибки пытаемся спарсить то, что есть
            try:
                page_source = self.driver.page_source
                return self.extract_phone_numbers(page_source)
            except:
                return []

    def extract_phone_numbers(self, html_content):
        phone_numbers = []
        pattern = r'\+55[0-9\s\-\(\)\.]+'
        for match in re.finditer(pattern, html_content):
            cleaned_number = re.sub(r'[^\d\+]', '', match.group())
            if cleaned_number.startswith(PHONE_PREFIX) and len(cleaned_number) >= MIN_PHONE_LENGTH:
                if cleaned_number not in phone_numbers:
                    phone_numbers.append(cleaned_number)
        return phone_numbers

    def save_results(self, phone_numbers, phones_per_page=15):
        os.makedirs('data', exist_ok=True)
        txt_path = os.path.join('data', 'phone_numbers.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            total = len(phone_numbers)
            page = START_PAGE
            for i, number in enumerate(phone_numbers, 1):
                if (i - 1) % phones_per_page == 0:
                    if i != 1:
                        f.write('\n')
                    f.write(f"=== Страница {page} ===\n")
                    page += 1
                f.write(f"{i}. {number}\n")
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
        phone_numbers = parser.parse_all_pages()
        print(f"Всего номеров найдено: {len(phone_numbers)}")
        parser.save_results(phone_numbers)
    finally:
        parser.close()


if __name__ == "__main__":
    main()
