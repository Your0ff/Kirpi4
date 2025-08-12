import os
import time
import subprocess
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import EMAIL, PASSWORD, HEADLESS_MODE, base_path
from enum import Enum
from pynput.keyboard import Key, Controller as KeyboardController
from pynput import mouse

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

        # Инициализируем контроллеры pynput
        self.keyboard = KeyboardController()
        self.mouse_controller = mouse.Controller()

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

    def update_phone_status(self, phone_number, status: PhoneStatus, otp_code=None):
        """Универсальный метод для обновления статуса номера и добавления OTP кода"""
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

                        # Убираем старые OTP коды, если есть
                        if 'OTP код:' in clean_line:
                            clean_line = clean_line.split('OTP код:')[0].strip()

                        # Восстанавливаем правильный формат строки
                        parts = clean_line.split('.')
                        if len(parts) >= 2:
                            line_number = parts[0].strip()
                            # Формируем правильную строку с номером телефона
                            if phone_number.startswith('+'):
                                formatted_line = f"{line_number}. {phone_number}"
                            else:
                                formatted_line = f"{line_number}. +{phone_number}"
                        else:
                            formatted_line = clean_line

                        # Добавляем статус и OTP код
                        if status == PhoneStatus.PROCESSED and otp_code:
                            line = f"{formatted_line} + OTP код: {otp_code}"
                        elif status.value:
                            line = f"{formatted_line} {status.value}"
                        else:
                            line = formatted_line

                        line += '\n'
                    else:
                        line = line
                    file.write(line)

            status_name = {
                PhoneStatus.PROCESSED: "обработанным",
                PhoneStatus.BANNED: "забаненным",
                PhoneStatus.NO_CODE: "без кода"
            }.get(status, "обновленным")

            print(f"✅ Номер {phone_number} отмечен как {status_name}")
        except Exception as e:
            print(f"❌ Ошибка при обновлении статуса номера {phone_number}: {e}")

    def mark_number_as_processed(self, phone_number, otp_code=None):
        """Отмечает номер как обработанный с возможностью добавления OTP кода"""
        self.update_phone_status(phone_number, PhoneStatus.PROCESSED, otp_code)

    def update_phone_numbers_with_otp(self, otp_codes):
        """Добавляет OTP коды к уже обработанным номерам в файле"""
        for phone_number, otp_code in otp_codes.items():
            self.update_phone_status(phone_number, PhoneStatus.PROCESSED, otp_code)

    def mark_number_as_banned(self, phone_number):
        """Отмечает номер как забаненный"""
        self.update_phone_status(phone_number, PhoneStatus.BANNED)

    def is_number_processed(self, line):
        """Проверяет, был ли номер уже обработан (есть ли '+' в конце строки или '+ OTP код:')"""
        line = line.strip()
        return (line.endswith('+') or
                '+ OTP код:' in line or
                '- BAN' in line or
                '- nocode' in line)

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
                            full_number_part = parts[1].strip()
                            # Извлекаем только номер телефона, убирая OTP часть если есть
                            number = full_number_part.split(' +')[0] if ' +' in full_number_part else full_number_part
                            number = number.split(' OTP')[0] if ' OTP' in number else number
                            number = number.strip()

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
            # Извлекаем только номер телефона, убирая OTP часть если есть
            clean_number = phone_number.split(' +')[0] if ' +' in phone_number else phone_number
            clean_number = clean_number.split(' OTP')[0] if ' OTP' in clean_number else clean_number

            # Формируем путь к папке с номером
            folder_name = clean_number.replace('+', '').replace('-', '').replace(' ', '')
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
            time.sleep(2)  # Увеличили с 1 до 2 секунд для стабильности

            # Нажимаем Enter 2 раза
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
            time.sleep(WAIT_BETWEEN_KEYSTROKES)
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
            time.sleep(WAIT_BETWEEN_KEYSTROKES)

            # Нажимаем Backspace 3 раза
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(0.01)
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(0.01)
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            time.sleep(0.01)

            # Вводим номер телефона
            self.keyboard.type(phone_number)
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
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

    def verify_otp_entered_successfully(self):
        """Проверяет, был ли OTP код успешно введен в Telegram"""
        try:
            import pygetwindow as gw
            telegram_windows = [w for w in gw.getAllWindows() if
                                'Telegram' in w.title and w.width > 300 and w.height > 200]

            if telegram_windows:
                window = telegram_windows[0]
                # Если заголовок изменился с базового "Telegram", значит OTP принят
                if window.title != 'Telegram' or 'Telegram Desktop' in window.title:
                    time.sleep(1)
                    return True

            return False
        except Exception as e:
            print(f"⚠️ Ошибка при проверке статуса OTP: {e}")
            return False

    def wait_for_otp_acceptance(self, timeout=30):
        """Ждет подтверждения принятия OTP кода с тайм-аутом"""
        start_time = time.time()
        checks_made = 0

        while time.time() - start_time < timeout:
            checks_made += 1
            print(f"🔍 Проверка {checks_made}: ожидание принятия OTP...")

            if self.verify_otp_entered_successfully():
                elapsed_time = time.time() - start_time
                print(f"✅ OTP принят за {elapsed_time:.1f}с!")
                return True

            time.sleep(1)  # Проверяем каждую секунду

        print(f"⏰ Тайм-аут после {checks_made} проверок ({timeout}с)")
        return False

    def copy_otp_code_with_timeout(self, phone_number, timeout=30):
        """Копирование OTP кода с ожиданием в течение заданного времени"""
        start_time = time.time()
        check_count = 0

        print(f"⏳ Ожидание появления OTP кода для {phone_number} (максимум {timeout}с)...")

        while time.time() - start_time < timeout:
            check_count += 1
            elapsed_time = time.time() - start_time
            print(f"🔍 Проверка {check_count}: поиск OTP кода ({elapsed_time:.1f}с)")

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
                        print(f"✅ OTP код найден: {otp_code} (через {elapsed_time:.1f}с)")

                        if otp_code.strip().lower() == 'nocode':
                            return 'nocode'

                        # Вставляем OTP код в Telegram
                        self.keyboard.type(otp_code)
                        print(f"📱 OTP код введен в Telegram: {otp_code}")

                        # Ждем подтверждения принятия OTP с тайм-аутом
                        if self.wait_for_otp_acceptance(timeout=30):
                            print("✅ OTP успешно принят Telegram!")
                            return otp_code
                        else:
                            print("❌ OTP не принят за 30 секунд")
                            return None
                    else:
                        # OTP код еще не появился, ждем и проверяем снова
                        time.sleep(1)  # Проверяем каждую секунду
                        continue
                else:
                    # Кнопка копирования недоступна, ждем и проверяем снова
                    time.sleep(1)
                    continue

            except Exception as e:
                # Элемент не найден, ждем и проверяем снова
                time.sleep(1)
                continue

        # Время истекло
        print(f"⏰ Тайм-аут ожидания OTP кода ({timeout}с). Код не появился для номера {phone_number}")
        return None

    def close_telegram(self):
        """Закрытие Telegram с проверкой завершения процесса"""
        try:
            # Закрываем все процессы Telegram
            os.system("taskkill /f /im Telegram.exe >nul 2>&1")

            # Ждем завершения процесса
            max_wait = 10  # Максимум 10 секунд ожидания
            for i in range(max_wait):
                # Проверяем, запущен ли еще Telegram
                result = os.system("tasklist /fi \"imagename eq Telegram.exe\" 2>nul | find /i \"Telegram.exe\" >nul")
                if result != 0:  # Процесс не найден
                    print("✅ Telegram успешно закрыт")
                    return
                time.sleep(1)

            print("⚠️ Telegram может быть еще запущен, продолжаем...")

        except Exception as e:
            print(f"⚠️ Ошибка при закрытии Telegram: {e}")

    def _remove_file_with_retry(self, file_path, max_attempts=5):
        """Удаление файла с несколькими попытками"""
        for attempt in range(1, max_attempts + 1):
            try:
                os.remove(file_path)
                return True
            except PermissionError:
                if attempt < max_attempts:
                    time.sleep(0.5)  # Ждем 2 секунды между попытками
                    continue
                else:
                    print(f"⚠️ Не удалось удалить {os.path.basename(file_path)} (файл заблокирован)")
                    return False
            except Exception:
                return False
        return False

    def clean_number_folder(self, phone_number):
        """Очистка папки номера после успешной обработки"""
        try:
            import shutil
            # Извлекаем только номер телефона, убирая OTP часть если есть
            clean_number = phone_number.split(' +')[0] if ' +' in phone_number else phone_number
            clean_number = clean_number.split(' OTP')[0] if ' OTP' in clean_number else clean_number

            # Формируем путь к папке с номером
            folder_name = clean_number.replace('+', '').replace('-', '').replace(' ', '')
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
                    # Для Telegram.exe делаем несколько попыток
                    if item == "Telegram.exe":
                        self._remove_file_with_retry(item_path)
                    else:
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

            otp_code = self.copy_otp_code_with_timeout(phone_number, timeout=30)
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
            self.mark_number_as_processed(phone_number, otp_code)
            time.sleep(1)

            # Пауза между номерами
            if i < len(self.phone_numbers):
                time.sleep(0.5)

        # Результаты
        print(f"✅ Успешно обработано: {successful_processes}")
        print(f"🚫 Забанено: {banned_processes}")
        print(f"❌ Ошибок: {failed_processes}")
        print(f"📊 Всего обработано: {len(self.phone_numbers)}")

        # OTP коды уже добавлены при обработке каждого номера

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
