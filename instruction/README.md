# Telega1 Project

## Описание

Автоматизация сбора номеров с сайта secondtg.org, создание папок для каждого номера, автоматизация Telegram Desktop и обработка OTP-кодов.

## Быстрый старт

1. **Установите зависимости:**
   ```
   pip install -r requirements.txt
   ```

2. **Настройте параметры в `config.py`:**
   - EMAIL, PASSWORD — для авторизации на сайте (если используется)
   - BASE_URL, START_PAGE, END_PAGE — диапазон страниц для парсинга
   - MOUSE_COORDINATES — координаты для макросов Telegram

3. **Парсинг номеров:**
   - Запустите `phone_parser.py` для сбора номеров с сайта.
   - Результаты сохраняются в папку `data/`:
     - `data/phone_numbers.txt` — список номеров
     - `data/parsing_results.json` — json с номерами

4. **Создание папок и копирование Telegram:**
   - Запустите `create_telegram_folders.py` — создаст папки для каждого номера и скопирует `Telegram.exe`.

5. **Автоматизация Telegram:**
   - Запустите `auto_telegram_sender.py` для автоматизации ввода номеров, получения OTP и очистки папок.

## Структура файлов

- `data/phone_numbers.txt` — список номеров для обработки
- `data/parsing_results.json` — json с результатами парсинга
- `config.py` — все параметры и настройки
- `requirements.txt` — зависимости
- `README.md` — эта инструкция

## Зависимости

См. файл `requirements.txt`.

## Примечания
- Для работы с профилем Chrome используйте отдельный профиль, не используемый в обычном браузере.
- Все действия с Telegram Desktop автоматизированы через pyautogui, pyperclip и координаты мыши.
