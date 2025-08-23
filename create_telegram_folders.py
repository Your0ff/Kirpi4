import os
import shutil
import re

from config import base_path, telegram_exe_path, PHONE_PREFIX


def create_folders_and_copy_telegram():
    """
    Создает папки с названиями номеров телефонов и копирует туда Telegram
    """

    # Файл с номерами телефонов (создается парсером)
    phone_numbers_file = os.path.join('data', 'phone_numbers.txt')

    print("=" * 60)
    print("СОЗДАНИЕ ПАПОК С НОМЕРАМИ ТЕЛЕФОНОВ")
    print("=" * 60)

    # Проверяем существование папки data/
    if not os.path.exists('data'):
        try:
            os.makedirs('data')
            print(f"✅ Создана папка: {os.path.join('data')}")
        except Exception as e:
            print(f"❌ Не удалось создать папку {os.path.join('data')}: {e}")
            return
    else:
        print(f"✅ Папка data/ существует: {os.path.join('data')}")

    # Проверяем существование файла с номерами
    if not os.path.exists(phone_numbers_file):
        print(f"❌ Файл '{phone_numbers_file}' не найден!")
        print("Сначала запустите парсер для создания файла с номерами.")
        return

    # Проверяем существование Telegram.exe
    if not os.path.exists(telegram_exe_path):
        print(f"❌ Файл Telegram.exe не найден по пути: {telegram_exe_path}")
        print("Укажите правильный путь к Telegram.exe в настройках.")
        return

    # Проверяем/создаем базовую папку
    if not os.path.exists(base_path):
        try:
            os.makedirs(base_path)
            print(f"✅ Создана папка: {base_path}")
        except Exception as e:
            print(f"❌ Не удалось создать папку {base_path}: {e}")
            return
    else:
        print(f"✅ Папка существует: {base_path}")

    # ============================================
    # ЧТЕНИЕ НОМЕРОВ ТЕЛЕФОНОВ
    # ============================================

    print(f"\n📖 Читаем номера из файла '{phone_numbers_file}'...")

    phone_numbers = []
    try:
        with open(phone_numbers_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        # Парсим номера из файла
        for line in lines:
            line = line.strip()
            if line and not line.startswith('=') and not line.startswith('Найденные') and not line.startswith(
                    'URL:') and not line.startswith('Дата:') and not line.startswith('Всего найдено:'):
                # Ищем номера в строке вида "1. +5581991302524 ID: 249598"
                if f'{PHONE_PREFIX}' in line:
                    # Используем регулярное выражение для извлечения только номера телефона
                    phone_match = re.search(rf'\+{PHONE_PREFIX}\d+', line)
                    if phone_match:
                        phone_number = phone_match.group()
                        phone_numbers.append(phone_number)
                        print(f"📱 Найден номер: {phone_number}")

    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        return

    if not phone_numbers:
        print("❌ Номера телефонов не найдены в файле!")
        print("Убедитесь, что парсер создал файл с номерами.")
        return

    print(f"✅ Найдено {len(phone_numbers)} номеров телефонов")

    # ============================================
    # СОЗДАНИЕ ПАПОК И КОПИРОВАНИЕ TELEGRAM
    # ============================================

    print(f"\n📁 Создаем папки и копируем Telegram...")
    print(f"📂 Базовая папка: {base_path}")
    print(f"📱 Telegram: {telegram_exe_path}")
    print("=" * 60)

    created_folders = 0
    errors = 0

    for i, phone_number in enumerate(phone_numbers, 1):
        try:
            # Создаем папку с названием номера (убираем только символ + и пробелы)
            folder_name = phone_number.replace('+', '').replace(' ', '')
            folder_path = os.path.join(base_path, folder_name)

            # Создаем папку
            os.makedirs(folder_path, exist_ok=True)

            # Копируем Telegram.exe
            telegram_dest = os.path.join(folder_path, "Telegram.exe")
            shutil.copy2(telegram_exe_path, telegram_dest)

            created_folders += 1

            # Прогресс-бар
            progress = int((i / len(phone_numbers)) * 100)
            progress_bar = '[' + '#' * (progress // 5) + ' ' * ((100 - progress) // 5) + ']'
            print(f"\rПрогресс: {progress_bar} {progress}% | Папка {i}/{len(phone_numbers)}: {folder_name}", end='')

        except Exception as e:
            errors += 1
            print(f"\n❌ Ошибка при создании папки для {phone_number}: {e}")

    # ============================================
    # РЕЗУЛЬТАТЫ
    # ============================================

    print(f"\n\n{'=' * 60}")
    print("РЕЗУЛЬТАТЫ СОЗДАНИЯ ПАПОК")
    print(f"{'=' * 60}")
    print(f"✅ Успешно создано папок: {created_folders}")
    if errors > 0:
        print(f"❌ Ошибок: {errors}")
    print(f"📂 Все папки созданы в: {base_path}")
    print(f"📱 Telegram скопирован в каждую папку")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    create_folders_and_copy_telegram()
