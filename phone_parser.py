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


def extract_2fa_code_from_row(row):
    """Извлекает 2FA код из строки таблицы (через Selenium)"""
    try:
        if not ENABLE_2FA:
            return None
        
        # Способ 1: Ищем все tooltip-text элементы в строке
        tooltip_elements = row.find_elements(By.CSS_SELECTOR, "span.tooltip-text")
        
        for tooltip in tooltip_elements:
            # Пробуем получить текст разными способами (для скрытых элементов)
            try:
                tooltip_text = tooltip.text.strip()
            except:
                try:
                    tooltip_text = tooltip.get_attribute("textContent").strip()
                except:
                    try:
                        tooltip_text = tooltip.get_attribute("innerText").strip()
                    except:
                        continue
            
            # Проверяем, содержит ли tooltip текст "2FA:"
            if tooltip_text and tooltip_text.startswith("2FA:"):
                # Извлекаем код после "2FA:"
                two_fa_code = tooltip_text.replace("2FA:", "").strip()
                if two_fa_code:
                    return two_fa_code
        
        # Способ 2: Ищем кнопку с иконкой shield-check и извлекаем tooltip из её контейнера
        try:
            # Ищем кнопки с иконкой shield-check
            shield_buttons = row.find_elements(By.CSS_SELECTOR, "i.mdi-shield-check")
            for icon in shield_buttons:
                # Находим родительский tooltip-container
                try:
                    tooltip_container = icon.find_element(By.XPATH, "./ancestor::div[contains(@class, 'tooltip-container')]")
                    if tooltip_container:
                        tooltip = tooltip_container.find_element(By.CSS_SELECTOR, "span.tooltip-text")
                        # Пробуем получить текст разными способами
                        try:
                            tooltip_text = tooltip.text.strip()
                        except:
                            try:
                                tooltip_text = tooltip.get_attribute("textContent").strip()
                            except:
                                try:
                                    tooltip_text = tooltip.get_attribute("innerText").strip()
                                except:
                                    continue
                        
                        if tooltip_text and tooltip_text.startswith("2FA:"):
                            two_fa_code = tooltip_text.replace("2FA:", "").strip()
                            if two_fa_code:
                                return two_fa_code
                except:
                    # Пробуем найти tooltip через родительскую кнопку
                    try:
                        button = icon.find_element(By.XPATH, "./ancestor::button")
                        tooltip_container = button.find_element(By.XPATH, "./following-sibling::span[contains(@class, 'tooltip-text')] | ./parent::div//span[contains(@class, 'tooltip-text')]")
                        if tooltip_container:
                            tooltip_text = tooltip_container.get_attribute("textContent") or tooltip_container.text
                            if tooltip_text and tooltip_text.strip().startswith("2FA:"):
                                two_fa_code = tooltip_text.strip().replace("2FA:", "").strip()
                                if two_fa_code:
                                    return two_fa_code
                    except:
                        pass
        except Exception:
            pass
        
        # Способ 3: Используем JavaScript для получения innerHTML строки (для скрытых элементов)
        try:
            row_html = row.get_attribute("innerHTML")
            if row_html:
                # Ищем 2FA код в HTML через регулярное выражение
                two_fa_match = re.search(r'2FA:\s*([A-Za-z0-9]{10,20})', row_html, re.IGNORECASE)
                if two_fa_match:
                    return two_fa_match.group(1).strip()
        except Exception:
            pass
        
        # Способ 4: Ищем любой текст, содержащий "2FA:" в строке
        try:
            row_text = row.text
            if "2FA:" in row_text:
                # Извлекаем код после "2FA:"
                match = re.search(r'2FA:\s*([A-Za-z0-9]+)', row_text)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass
            
    except Exception as e:
        # Тихий провал - не все номера имеют 2FA
        pass
    
    return None


def extract_2fa_code_from_html(row_html):
    """Извлекает 2FA код из HTML строки таблицы"""
    try:
        if not ENABLE_2FA:
            return None
        
        # Способ 1: Ищем tooltip-text элемент, содержащий "2FA:"
        # Паттерн: <span class="tooltip-text">2FA: код</span>
        two_fa_pattern = r'<span\s+class=["\']tooltip-text["\']>2FA:\s*([^<]+)</span>'
        two_fa_match = re.search(two_fa_pattern, row_html, re.IGNORECASE | re.DOTALL)
        
        if two_fa_match:
            two_fa_code = two_fa_match.group(1).strip()
            if two_fa_code:
                return two_fa_code
        
        # Способ 2: Ищем внутри tooltip-container с кнопкой shield-check
        # Ищем структуру: <div class="tooltip-container">...<i class="mdi mdi-shield-check">...<span class="tooltip-text">2FA: код</span>
        tooltip_container_pattern = r'<div[^>]*class=["\'][^"\']*tooltip-container[^"\']*["\'][^>]*>.*?<i[^>]*class=["\'][^"\']*mdi-shield-check[^"\']*["\'][^>]*>.*?<span[^>]*class=["\']tooltip-text["\'][^>]*>2FA:\s*([^<]+)</span>'
        two_fa_match = re.search(tooltip_container_pattern, row_html, re.IGNORECASE | re.DOTALL)
        
        if two_fa_match:
            two_fa_code = two_fa_match.group(1).strip()
            if two_fa_code:
                return two_fa_code
        
        # Способ 3: Ищем любой текст "2FA: код" в строке (более гибкий поиск)
        two_fa_pattern_general = r'2FA:\s*([A-Za-z0-9]{10,20})'
        two_fa_match = re.search(two_fa_pattern_general, row_html, re.IGNORECASE)
        
        if two_fa_match:
            two_fa_code = two_fa_match.group(1).strip()
            if two_fa_code:
                return two_fa_code
                
    except Exception:
        pass
    
    return None


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
                if not self.navigate_to_page(page_num):
                    print(f"⚠️ Не удалось перейти на страницу {page_num}, пропускаем...")
                    continue
            else:
                print(f"🔍 Парсинг текущей страницы {page_num}...")

            # Ждем полной загрузки страницы и парсим номера с ID
            page_data = self.wait_and_parse_page()
            all_phone_data.extend(page_data)
            print(f"✅ Страница {page_num}: {len(page_data)} номеров")

        print(f"🎯 Всего найдено номеров: {len(all_phone_data)}")
        return all_phone_data
    
    def navigate_to_page(self, page_number):
        """Переходит на указанную страницу через клик по ссылке пагинации"""
        try:
            if page_number == 1:
                self.driver.get(f"{BASE_URL}")
                time.sleep(2)
                return True

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    # Ждем появления контейнера пагинации
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "pagination-container"))
                    )
                    
                    # Ищем ссылку пагинации с нужным номером страницы
                    pagination_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            f"//div[@id='pagination-container']//a[@class='page-link' and contains(@href, 'page={page_number}')]"))
                    )
                    
                    # Прокручиваем к элементу, если нужно
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", pagination_link)
                    time.sleep(0.5)
                    
                    # Кликаем на ссылку пагинации
                    pagination_link.click()
                    time.sleep(2)  # Даем время для AJAX загрузки

                    # Проверяем, что страница загрузилась
                    try:
                        # Ждем обновления пагинации (активная страница должна иметь класс active)
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH,
                                f"//div[@id='pagination-container']//li[@class='page-item active']//span[contains(text(), '{page_number}')]"))
                        )
                        print(f"✅ Успешно перешли на страницу {page_number}")
                        
                        # Дополнительная проверка - ждем появления строк таблицы
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.order-row"))
                        )
                        return True
                    except:
                        # Альтернативная проверка - просто наличие строк таблицы
                        rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.order-row")
                        if len(rows) > 0:
                            print(f"✅ Успешно перешли на страницу {page_number} (найдены строки таблицы)")
                            return True

                    print(f"⚠️ Попытка {attempt}: Не удалось подтвердить переход на страницу {page_number}")
                    time.sleep(2)

                except Exception as e:
                    print(f"⚠️ Попытка {attempt}: Не удалось перейти на страницу {page_number}: {e}")
                    time.sleep(2)

            print(f"❌ Не удалось перейти на страницу {page_number} после {max_attempts} попыток")
            return False

        except Exception as e:
            print(f"❌ Критическая ошибка при переходе на страницу {page_number}: {e}")
            return False

    def wait_and_parse_page(self):
        """Ждет загрузки страницы и парсит номера с ID"""
        try:
            # Ждем появления строк таблицы с заказами
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr.order-row"))
            )

            # Парсим страницу до тех пор, пока не найдем достаточное количество номеров
            max_attempts = 30  # максимум 15 секунд ожидания (30 * 0.5)
            expected_numbers = getattr(sys.modules.get('config'), 'EXPECTED_NUMBERS_PER_PAGE', 15)

            for attempt in range(max_attempts):
                # Пробуем извлечь данные через Selenium (более надежно)
                current_data = self.extract_phone_numbers_with_ids_selenium()
                
                # Если не получилось через Selenium, пробуем через HTML
                if len(current_data) == 0:
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
                # Сначала пробуем через Selenium
                data = self.extract_phone_numbers_with_ids_selenium()
                if len(data) > 0:
                    return data
                # Если не получилось, пробуем через HTML
                page_source = self.driver.page_source
                return self.extract_phone_numbers_with_ids(page_source)
            except Exception as e2:
                print(f"⚠️ Ошибка при извлечении данных: {e2}")
                return []

    def extract_phone_numbers_with_ids_selenium(self):
        """Извлекает номера телефонов через Selenium (более надежный способ)"""
        phone_data = []
        used_numbers = set()
        
        try:
            # Находим все строки таблицы
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.order-row")
            
            for row in rows:
                try:
                    # Извлекаем ID из <td class="text-muted">
                    id_elements = row.find_elements(By.CSS_SELECTOR, "td.text-muted")
                    if not id_elements:
                        # Альтернативный способ - из checkbox
                        checkbox = row.find_element(By.CSS_SELECTOR, "input.account-checkbox")
                        order_id = checkbox.get_attribute("data-order-id")
                    else:
                        order_id = id_elements[0].text.strip()
                    
                    if not order_id:
                        continue
                    
                    # Ищем номер телефона в теге <b>
                    phone_elements = row.find_elements(By.CSS_SELECTOR, "td b")
                    
                    for phone_elem in phone_elements:
                        phone_text = phone_elem.text.strip()
                        # Проверяем, что это номер телефона с нужным префиксом
                        if phone_text.startswith(PHONE_PREFIX) and phone_text not in used_numbers:
                            # Очищаем номер от возможных пробелов
                            phone_number = re.sub(r'[^\d\+]', '', phone_text)
                            if phone_number.startswith(PHONE_PREFIX):
                                # Извлекаем 2FA код, если включен парсинг 2FA
                                two_fa_code = extract_2fa_code_from_row(row) if ENABLE_2FA else None
                                
                                phone_data.append({
                                    'number': phone_number,
                                    'id': order_id,
                                    '2fa': two_fa_code
                                })
                                used_numbers.add(phone_number)
                                break  # Нашли номер для этой строки
                    
                except Exception as e:
                    # Пропускаем проблемную строку
                    continue
            
        except Exception as e:
            print(f"⚠️ Ошибка при извлечении через Selenium: {e}")
        
        return phone_data
    
    def extract_phone_numbers_with_ids(self, html_content):
        """Извлекает номера телефонов и соответствующие им ID из новой структуры таблицы"""
        phone_data = []

        # Более гибкий паттерн для поиска строк таблицы (учитываем возможные пробелы и другие атрибуты)
        row_pattern = r'<tr\s+class=["\']order-row["\'].*?>(.*?)</tr>'
        rows = re.finditer(row_pattern, html_content, re.DOTALL | re.IGNORECASE)

        used_numbers = set()
        rows_found = 0

        for row_match in rows:
            rows_found += 1
            row_html = row_match.group(1)

            # Извлекаем ID из <td class="text-muted">ID</td>
            id_match = re.search(r'<td\s+class=["\']text-muted["\']>(\d+)</td>', row_html, re.IGNORECASE)
            if not id_match:
                # Альтернативный способ - из data-order-id атрибута checkbox
                id_match = re.search(r'data-order-id=["\'](\d+)["\']', row_html, re.IGNORECASE)
            
            if not id_match:
                continue

            order_id = id_match.group(1)

            # Более гибкий поиск номера телефона - ищем <b> с номером телефона
            # Может быть в разных местах внутри <td>
            phone_pattern = rf'<b>\s*({re.escape(PHONE_PREFIX)}\d+)\s*</b>'
            phone_match = re.search(phone_pattern, row_html, re.IGNORECASE)
            
            # Если не нашли в <b>, пробуем найти номер напрямую по паттерну
            if not phone_match:
                phone_pattern2 = rf'({re.escape(PHONE_PREFIX)}\d{{10,}})'
                phone_match = re.search(phone_pattern2, row_html)
            
            if not phone_match:
                continue

            phone_number = phone_match.group(1).strip()
            # Очищаем номер от возможных пробелов и форматирования
            phone_number = re.sub(r'[^\d\+]', '', phone_number)

            # Проверяем, что номер начинается с нужного префикса и не дублируется
            if phone_number.startswith(PHONE_PREFIX) and phone_number not in used_numbers:
                # Извлекаем 2FA код, если включен парсинг 2FA
                two_fa_code = extract_2fa_code_from_html(row_html) if ENABLE_2FA else None
                
                phone_data.append({
                    'number': phone_number,
                    'id': order_id,
                    '2fa': two_fa_code
                })
                used_numbers.add(phone_number)

        if rows_found == 0:
            print("⚠️ Не найдено ни одной строки <tr class='order-row'>")
        elif len(phone_data) == 0:
            print(f"⚠️ Найдено строк: {rows_found}, но номера не извлечены. Проверьте префикс PHONE_PREFIX='{PHONE_PREFIX}'")

        return phone_data

    def save_results(self, phone_data, phones_per_page=EXPECTED_NUMBERS_PER_PAGE):
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
                
                # Формируем строку с номером, 2FA (если есть) и ID
                line = f"{i}. {data['number']}"
                if ENABLE_2FA and data.get('2fa'):
                    line += f" 2FA: {data['2fa']}"
                line += f" ID: {data['id']}"
                f.write(line + '\n')
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
