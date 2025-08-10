import os
import time
import subprocess
import pyautogui
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import EMAIL, PASSWORD, MOUSE_COORDINATES, MOUSE_COORDINATES_lkm, HEADLESS_MODE, base_path
from enum import Enum

# Используем PHONE_NUMBERS_FILE из config.py
PHONE_NUMBERS_FILE = os.path.join('data', 'phone_numbers.txt')
if not os.path.exists('data'):
    os.makedirs('data', exist_ok=True)

# Константы для таймингов
WAIT_AFTER_OTP_REQUEST = 7
WAIT_BETWEEN_KEYSTROKES = 0.8
WAIT_FOR_TELEGRAM_WINDOW = 15
WAIT_COPY_OTP_ATTEMPTS = 10


class PhoneStatus(Enum):
    """Статусы обработки номеров телефонов"""
    UNPROCESSED = ""
    PROCESSED = "+"
    BANNED = "- BAN"
    NO_CODE = "- nocode"


class AutoTelegramSender:
    def __init__(self):
        """Инициализация автоматического отправителя Telegram"""
        self.phone_numbers = []
        self.current_page = 1
        self.base_path = base_path
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Настройка Chrome WebDriver для автоматизации сайта"""
        chrome_options = Options()

        if HEADLESS_MODE:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Автоматическая установка ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def read_phone_numbers(self):
        """Чтение номеров телефонов из файла (только необработанные)"""

        # Загружаем только необработанные номера
        self.phone_numbers = self.load_unprocessed_numbers()

        if not self.phone_numbers:
            print("❌ Необработанные номера телефонов не найдены!")
            print("Все номера уже обработаны или файл пуст.")
            return False

        return True

    def update_phone_status(self, phone_number, status: PhoneStatus):
        """Универсальный метод для обновления статуса номера"""
        try:
            with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            with open(PHONE_NUMBERS_FILE, 'w', encoding='utf-8') as file:
                for line in lines:
                    if phone_number in line:
                        # Убираем существующие статусы
                        clean_line = line.strip()
                        for existing_status in PhoneStatus:
                            if existing_status.value and existing_status.value in clean_line:
                                clean_line = clean_line.replace(existing_status.value, '').strip()

                        # Добавляем новый статус
                        if status.value:
                            line = clean_line + ' ' + status.value + '\n'
                        else:
                            line = clean_line + '\n'
                    file.write(line)

            status_name = {
                PhoneStatus.PROCESSED: "обработанным",
                PhoneStatus.BANNED: "забаненным",
                PhoneStatus.NO_CODE: "без кода"
            }.get(status, "обновленным")

            print(f"✅ Номер {phone_number} отмечен как {status_name}")
        except Exception as e:
            print(f"❌ Ошибка при обновлении статуса номера {phone_number}: {e}")

    def mark_number_as_processed(self, phone_number):
        """Отмечает номер как обработанный"""
        self.update_phone_status(phone_number, PhoneStatus.PROCESSED)

    def mark_number_as_banned(self, phone_number):
        """Отмечает номер как забаненный"""
        self.update_phone_status(phone_number, PhoneStatus.BANNED)

    def is_number_processed(self, line):
        """Проверяет, был ли номер уже обработан (есть ли '+' в конце строки)"""
        return line.strip().endswith('+')

    def load_unprocessed_numbers(self):
        """Загружает только необработанные номера телефонов"""
        if not os.path.exists(PHONE_NUMBERS_FILE):
            print(f"❌ Файл '{PHONE_NUMBERS_FILE}' не найден!")
            return []

        try:
            with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            unprocessed_numbers = []
            current_page = 1

            for line in lines:
                line = line.strip()

                # Обновляем текущую страницу, если найдена новая
                if line.startswith('=== Страница'):
                    page_num = line.split()[2]
                    self.current_page = int(page_num)
                    continue

                if line and not line.startswith('=') and not line.startswith('Найденные') and not line.startswith(
                        'URL:') and not line.startswith('Дата:') and not line.startswith('Всего найдено:'):
                    if '+55' in line and not self.is_number_processed(line):
                        parts = line.split('.')
                        if len(parts) >= 2:
                            number = parts[1].strip()
                            if number.startswith('+55'):
                                unprocessed_numbers.append({
                                    'number': number,
                                    'page': self.current_page
                                })
                                print(f"📱 Найден необработанный номер: {number} (Страница {self.current_page})")

            print(f"✅ Найдено {len(unprocessed_numbers)} необработанных номеров")
            return unprocessed_numbers

        except Exception as e:
            print(f"❌ Ошибка при чтении файла: {e}")
            return []

    def login_and_open_orders(self):
        """Авторизация на сайте secondtg.org и открытие страницы orders"""
        try:
            # Переходим на страницу входа
            self.driver.get("https://secondtg.org/login")
            time.sleep(1)

            # Ждем появления формы входа
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )

            # Вводим email
            email_field.clear()
            email_field.send_keys(EMAIL)

            # Находим и вводим пароль
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(PASSWORD)

            # Нажимаем кнопку входа
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_button.click()

            # Ждем успешной авторизации
            time.sleep(1)

            # Проверяем, что авторизация прошла успешно
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                print("✅ Авторизация прошла успешно!")

                # Сразу переходим на страницу orders
                self.driver.get("https://secondtg.org/orders")
                time.sleep(1)
                return True
            else:
                print("❌ Авторизация не удалась")
                return False

        except Exception as e:
            print(f"❌ Ошибка при авторизации и открытии orders: {e}")
            return False

    def open_telegram_with_number(self, phone_number):
        """Открытие Telegram с конкретным номером"""
        try:
            # Формируем путь к папке с номером
            folder_name = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            folder_path = os.path.join(self.base_path, folder_name)
            telegram_path = os.path.join(folder_path, "Telegram.exe")

            if not os.path.exists(telegram_path):
                print(f"❌ Telegram.exe не найден в папке: {folder_path}")
                return False

            # Запускаем Telegram.exe
            subprocess.Popen([telegram_path])
            return True

        except Exception as e:
            print(f"❌ Ошибка при открытии Telegram для {phone_number}: {e}")
            return False

    @staticmethod
    def wait_for_telegram_window(timeout=WAIT_FOR_TELEGRAM_WINDOW):
        import pygetwindow as gw
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Получаем все окна и фильтруем их
                all_windows = gw.getAllWindows()
                telegram_windows = []

                for window in all_windows:
                    title = window.title
                    title_lower = title.lower()

                    # Проверяем, что это настоящее окно Telegram
                    if (title in ['Telegram', 'Telegram Desktop'] and
                            # Исключаем окна с названиями файлов
                            'auto_telegram_sender.py' not in title and
                            '.py' not in title_lower and
                            ' – ' not in title and
                            ' - ' not in title and
                            window.width > 300 and
                            window.height > 200 and
                            not window.isMinimized):
                        telegram_windows.append(window)

                if telegram_windows:
                    # Берем первое подходящее окно
                    window = telegram_windows[0]
                    print(f"✅ Окно Telegram найдено: {window.title}")
                    return True

                time.sleep(0.5)

            except Exception as e:
                print(f"⚠️ Ошибка при поиске окна Telegram: {e}")
                time.sleep(1)

        print(f"❌ Окно Telegram не найдено за {timeout} секунд")
        return False

    def enter_phone_number(self, phone_number):
        """Ввод номера телефона через клавиатуру"""
        try:
            # Ждем появления окна Telegram через pygetwindow
            import pygetwindow as gw
            if not self.wait_for_telegram_window():
                print("❌ Окно Telegram не найдено! Проверьте запуск приложения.")
                return False
            time.sleep(2)
            # Нажимаем Enter 2 раза
            pyautogui.press('enter')
            time.sleep(WAIT_BETWEEN_KEYSTROKES)
            pyautogui.press('enter')
            time.sleep(WAIT_BETWEEN_KEYSTROKES)
            # Нажимаем Backspace 3 раза
            pyautogui.press('backspace')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.1)
            # Вставляем номер телефона
            pyautogui.write(phone_number)
            pyautogui.press('enter')
            return True
        except Exception as e:
            print(f"❌ Ошибка при вводе номера {phone_number}: {e}")
            return False

    def navigate_to_page(self, page_number):
        """Переходит на указанную страницу в orders"""
        try:
            if page_number == 1:
                self.driver.get("https://secondtg.org/orders")
                time.sleep(2)
                return True

            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    # 1. Переходим напрямую по URL
                    self.driver.get(f"https://secondtg.org/orders?page={page_number}")
                    time.sleep(2)  # Даем время для загрузки

                    # 2. Проверяем по URL (первичная проверка)
                    current_url = self.driver.current_url
                    if f"page={page_number}" in current_url:
                        print(f"✅ Успешно перешли на страницу {page_number} (по URL)")
                        return True

                    # 3. Альтернативная проверка по содержимому страницы
                    try:
                        # Ищем любой элемент, уникальный для этой страницы (например, первый номер телефона)
                        phone_element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            f"//div[contains(@class, 'card-body') and contains(., '{self.phone_numbers[0]['number']}')]"))
                        )
                        print(f"✅ Успешно перешли на страницу {page_number} (по содержимому)")
                        return True
                    except:
                        pass

                    # 4. Проверка через пагинацию (если предыдущие методы не сработали)
                    try:
                        active_page = self.driver.find_element(By.CSS_SELECTOR,
                                                               ".v-pagination__item--active button").text
                        if active_page == str(page_number):
                            print(f"✅ Успешно перешли на страницу {page_number} (по пагинации)")
                            return True
                    except:
                        pass

                    print(f"⚠️ Попытка {attempt}: Не удалось подтвердить переход на страницу {page_number}")
                    time.sleep(2)

                except Exception as e:
                    print(f"⚠️ Попытка {attempt}: Не удалось перейти на страницу {page_number}")
                    time.sleep(2)

            print(f"❌ Не удалось перейти на страницу {page_number} после {max_attempts} попыток")
            return False

        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            return False

    def find_and_click_request_otp(self, phone_number):
        """Поиск и нажатие кнопки Request OTP для конкретного номера"""
        try:
            # Ищем card-body с номером телефона (номер отображается с +)
            card_body = self.driver.find_element(By.XPATH,
                                                 f"//div[contains(@class, 'card-body') and contains(., '{phone_number}')]")

            # Ищем кнопку Request OTP внутри этого card-body
            request_otp_button = card_body.find_element(By.XPATH,
                                                        ".//button[contains(text(), 'Request OTP') or contains(text(), 'OTP')]")

            # Нажимаем кнопку
            request_otp_button.click()
            print(f"✅ Кнопка Request OTP нажата для номера {phone_number}")
            time.sleep(WAIT_AFTER_OTP_REQUEST)
            return True

        except Exception as e:
            print(f"❌ Не удалось найти кнопку Request OTP для {phone_number}")
            return False

    def mark_number_as_nocode(self, phone_number):
        """Отмечает номер как не получивший код"""
        self.update_phone_status(phone_number, PhoneStatus.NO_CODE)

    def copy_otp_code_with_retry(self, phone_number, max_attempts=WAIT_COPY_OTP_ATTEMPTS):
        """Копирование OTP кода с повторными попытками и вставка в Telegram"""
        for attempt in range(1, max_attempts + 1):
            try:
                # Ищем card-body с номером телефона (номер отображается с +)
                card_body = self.driver.find_element(By.XPATH,
                                                     f"//div[contains(@class, 'card-body') and contains(., '{phone_number}')]")
                # Ищем третью кнопку копирования (для OTP)
                copy_buttons = card_body.find_elements(By.XPATH,
                                                       ".//i[contains(@class, 'mdi-content-copy') and contains(@class, 'copy_address')]")
                if len(copy_buttons) >= 3:
                    # Берем третью кнопку копирования (для OTP)
                    otp_copy_button = copy_buttons[2]
                    # Кликаем на кнопку копирования OTP
                    otp_copy_button.click()
                    time.sleep(1)
                    # Получаем скопированный текст из буфера обмена
                    otp_code = pyperclip.paste()
                    if otp_code and len(otp_code) > 0 and otp_code.strip():
                        print(f"✅ OTP код скопирован: {otp_code}")
                        if otp_code.strip().lower() == 'nocode':
                            return 'nocode'
                        # Вставляем OTP код в Telegram
                        pyautogui.write(otp_code)
                        time.sleep(3)
                        return otp_code
                    else:
                        if attempt < max_attempts:
                            print(f"⏳ Ожидание OTP кода (попытка {attempt}/{max_attempts})")
                            time.sleep(3)
                            continue
                        else:
                            print(f"❌ OTP код не найден после {max_attempts} попыток для номера {phone_number}")
                            return None
                else:
                    if attempt < max_attempts:
                        print(f"⏳ Кнопка копирования недоступна (попытка {attempt}/{max_attempts})")
                        time.sleep(3)
                        continue
                    else:
                        print(f"❌ Кнопка копирования OTP не найдена для номера {phone_number}")
                        return None
            except Exception as e:
                # Упрощенный вывод ошибки без stacktrace
                print(f"❌ Ошибка при копировании OTP для {phone_number} (попытка {attempt}/{max_attempts})")
                if attempt < max_attempts:
                    time.sleep(3)
                    continue
                else:
                    return None
        return None

    def leave_telegram_group(self):
        """Выход из группы Telegram перед закрытием"""

        # Используем координаты из конфигурации
        right_click_x, right_click_y = MOUSE_COORDINATES['right_click']
        left_click_x, left_click_y = MOUSE_COORDINATES['left_click']
        left_click_x2, left_click_y2 = MOUSE_COORDINATES_lkm['left_click']
        try:
            pyautogui.click(left_click_x2, left_click_y2)
            time.sleep(0.8)
            # Нажимаем Ctrl+F для поиска
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(WAIT_BETWEEN_KEYSTROKES)

            # Вводим "sec" для поиска группы
            pyautogui.write("sec")
            time.sleep(0.5)

            # Нажимаем правую кнопку мыши по заданным координатам
            pyautogui.rightClick(right_click_x, right_click_y)
            time.sleep(0.5)

            # Нажимаем левую кнопку мыши по заданным координатам для выбора "Выйти из группы"
            pyautogui.click(left_click_x, left_click_y)
            time.sleep(0.5)

            pyautogui.press('enter')
            time.sleep(0.5)

            pyautogui.press('enter')
            time.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Ошибка при выходе из группы: {e}")

    def close_telegram(self):
        """Закрытие Telegram"""
        try:
            # Закрываем все процессы Telegram
            os.system("taskkill /f /im Telegram.exe >nul 2>&1")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии Telegram: {e}")

    def clean_number_folder(self, phone_number):
        """Очистка папки номера после успешной обработки"""
        try:
            import shutil
            # Формируем путь к папке с номером
            folder_name = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            folder_path = os.path.join(self.base_path, folder_name)
            if not os.path.exists(folder_path):
                return False
            # Список файлов и папок для удаления
            items_to_remove = [
                "Telegram.exe",  # Удаляем Telegram.exe
                "log.txt",
                "emoji",  # Удаляем папку emoji в корне
            ]
            for item in items_to_remove:
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                    except Exception:
                        pass
                elif os.path.isdir(item_path):
                    try:
                        shutil.rmtree(item_path)
                    except Exception:
                        pass
            # Удаляем папку emoji внутри tdata (если существует)
            tdata_emoji_path = os.path.join(folder_path, "tdata", "emoji")
            if os.path.isdir(tdata_emoji_path):
                try:
                    shutil.rmtree(tdata_emoji_path)
                except Exception:
                    pass
            print(f"✅ Очистка завершена.")
            return True
        except Exception as e:
            print(f"❌ Ошибка при очистке папки {phone_number}: {e}")
            return False

    def is_number_banned(self, phone_number):
        """Проверяет, забанен ли номер (имеет ли статус BR - BAN)"""
        try:
            # Ищем карточку с номером (номер отображается с +)
            card_body = self.driver.find_element(By.XPATH,
                                                 f"//div[contains(@class, 'card-body') and contains(., '{phone_number}')]")

            # Проверяем наличие блока с BR - BAN
            ban_element = card_body.find_element(By.XPATH,
                                                 ".//h6[contains(@class, 'mb-1') and contains(., 'BR - BAN')]")
            return True
        except:
            # Номер не забанен, возвращаем False без вывода ошибки
            return False

    def process_all_numbers(self):
        """Обработка всех номеров телефонов"""
        if not self.read_phone_numbers():
            return

        # Авторизуемся и открываем orders
        if not self.login_and_open_orders():
            print("❌ Не удалось авторизоваться и открыть orders. Завершаем работу.")
            return

        successful_processes = 0
        failed_processes = 0
        banned_processes = 0  # Счетчик забаненных номеров
        otp_codes = {}
        last_page = 1

        for i, phone_data in enumerate(self.phone_numbers, 1):
            phone_number = phone_data['number']
            page_number = phone_data['page']

            # Если страница изменилась, переходим на новую страницу
            if page_number != last_page:
                if not self.navigate_to_page(page_number):
                    failed_processes += 1
                    continue
                last_page = page_number

            # Проверяем, не забанен ли номер
            if self.is_number_banned(phone_number):
                print(f"⚠️ Номер {phone_number} забанен (BR - BAN), отмечаем как '- BAN'")
                self.mark_number_as_banned(phone_number)  # Используем новый метод
                banned_processes += 1
                continue

            # Открываем Telegram с номером
            if not self.open_telegram_with_number(phone_number):
                failed_processes += 1
                continue

            if not self.enter_phone_number(phone_number):
                failed_processes += 1
                self.close_telegram()
                time.sleep(1)
                continue

            time.sleep(1)  # Даем Telegram обработать ввод номера

            if not self.find_and_click_request_otp(phone_number):
                failed_processes += 1
                self.close_telegram()
                time.sleep(1)
                continue

            otp_code = self.copy_otp_code_with_retry(phone_number)
            if otp_code and otp_code.strip().upper() == 'NOCODE':
                self.mark_number_as_nocode(phone_number)
                failed_processes += 1
                self.close_telegram()
                time.sleep(1)
                continue
            elif not otp_code:
                failed_processes += 1
                self.close_telegram()
                time.sleep(1)
                continue

            # успешная обработка
            self.close_telegram()  # Сначала закрываем Telegram
            self.clean_number_folder(phone_number)  # Потом чистим папку
            otp_codes[phone_number] = otp_code
            successful_processes += 1
            self.mark_number_as_processed(phone_number)
            time.sleep(1)

            # Пауза между номерами
            if i < len(self.phone_numbers):
                time.sleep(0.5)

        # Результаты
        print(f"✅ Успешно обработано: {successful_processes}")
        print(f"🚫 Забанено: {banned_processes}")
        print(f"❌ Ошибок: {failed_processes}")
        print(f"📊 Всего обработано: {len(self.phone_numbers)}")

        # Выводим полученные OTP коды в консоль
        if otp_codes:
            print(f"\n📋 Полученные OTP коды:")
            for phone, code in otp_codes.items():
                print(f"  {phone}: {code}")

    def close(self):
        """Закрытие браузера и очистка"""
        if self.driver:
            self.driver.quit()
        # Убираем вызов close_telegram() отсюда, так как он уже вызывается в process_all_numbers


def main():
    """Главная функция"""
    sender = AutoTelegramSender()

    try:
        # Обработка всех номеров
        sender.process_all_numbers()

    except KeyboardInterrupt:
        print("\n⏹️ Процесс прерван пользователем.")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
    finally:
        sender.close()


if __name__ == "__main__":
    main()
