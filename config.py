# Конфигурационный файл для парсера
# Замените данные на свои

# Данные для авторизации
EMAIL = "#"  # ВСТАВЬТЕ СВОЙ EMAIL ВМЕСТО #
PASSWORD = "#"  # ВСТАВЬТЕ СВОЙ ПАРОЛЬ ВМЕСТО #

# Путь к папке, где будут создаваться папки с номерами
base_path = r"#"  # ИЗМЕНИТЕ НА СВОЙ ПУТЬ ВМЕСТО #

# Путь к файлу Telegram.exe
telegram_exe_path = r"#"  # ИЗМЕНИТЕ НА СВОЙ ПУТЬ ВМЕСТО #

# URL для парсинга
BASE_URL = "https://secondtg.org/orders"
START_PAGE = 1  # Начальная страница
END_PAGE = 1   # Конечная страница (включительно)

# Настройки браузера
HEADLESS_MODE = False  # True для фонового режима, False для видимого браузера

# Таймауты (в секундах)
PAGE_LOAD_TIMEOUT = 10
DYNAMIC_CONTENT_WAIT = 5
PAGE_DELAY = 1  # Задержка между страницами

# Фильтр для номеров телефонов
PHONE_PREFIX = "+55"  # Префикс для поиска номеров
MIN_PHONE_LENGTH = 13  # Минимальная длина номера

# Файл для сохранения номеров телефонов
PHONE_NUMBERS_FILE = "phone_numbers.txt"

# Координаты мыши для автоматизации Telegram
# Замените на реальные координаты, полученные с помощью get_mouse_position()
MOUSE_COORDINATES = {
    'right_click': (650, 250),  # Координаты для правого клика в Telegram
    'left_click': (785, 450),   # Координаты для левого клика в Telegram
}
MOUSE_COORDINATES_lkm = {
    'left_click': (1100, 500),   # Координаты для левого клика в Telegram
}