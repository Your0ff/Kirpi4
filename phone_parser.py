import time
import json
import os
import re
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

    def login(self):
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
            time.sleep(2)
            # Проверяем, что авторизация прошла успешно
            if "login" in self.driver.current_url.lower():
                print("❌ Авторизация не удалась!")
                return False
            print("✅ Авторизация прошла успешно!")
            return True
        except Exception as e:
            print(f"❌ Ошибка при авторизации: {e}")
            return False

    def parse_all_pages(self):
        all_phone_numbers = []
        for page_num in range(START_PAGE, END_PAGE + 1):
            page_url = f"{BASE_URL}?page={page_num}"
            self.driver.get(page_url)
            time.sleep(PAGE_DELAY)
            page_source = self.driver.page_source
            page_numbers = self.extract_phone_numbers(page_source)
            all_phone_numbers.extend(page_numbers)
            print(f"✅ Спарсено номеров на странице {page_num}: {len(page_numbers)}")
        return all_phone_numbers

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
        json_path = os.path.join('data', 'parsing_results.json')
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
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(phone_numbers, f, ensure_ascii=False, indent=2)
        print(f"✅ Результаты сохранены в {txt_path} и {json_path}")

    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    parser = PhoneNumberParser()
    try:
        if not parser.login():
            return
        # После логина сразу переходим на первую страницу orders
        parser.driver.get(f"{BASE_URL}?page={START_PAGE}")
        time.sleep(PAGE_DELAY)
        phone_numbers = parser.parse_all_pages()
        print(f"Всего номеров найдено: {len(phone_numbers)}")
        parser.save_results(phone_numbers)
    finally:
        parser.close()


if __name__ == "__main__":
    main()
