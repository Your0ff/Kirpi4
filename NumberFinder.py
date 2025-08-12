import os
import re
import glob


def remove_numbers_with_json_files(txt_file_path, directory_path=None):
    """
    Удаляет строки с номерами телефонов из txt файла, если существуют соответствующие JSON файлы

    Args:
        txt_file_path (str): Путь к txt файлу со списком номеров
        directory_path (str): Путь к директории с JSON файлами (по умолчанию та же, что и txt файл)
    """

    # Спрашиваем у пользователя, нужно ли удалять OTP коды
    while True:
        remove_otp = input("Удалить OTP коды из оставшихся номеров? (Y/N): ").strip().upper()
        if remove_otp in ['Y', 'N', 'YES', 'NO', 'Д', 'Н']:
            break
        print("Пожалуйста, введите Y (да) или N (нет)")

    remove_otp_codes = remove_otp in ['Y', 'YES', 'Д']

    # Если директория не указана, используем директорию txt файла
    if directory_path is None:
        directory_path = os.path.dirname(txt_file_path)

    # Проверяем существование txt файла
    if not os.path.exists(txt_file_path):
        print(f"Файл {txt_file_path} не найден!")
        return

    # Получаем список всех JSON файлов в директории
    json_files = glob.glob(os.path.join(directory_path, "*.json"))

    # Извлекаем номера телефонов из имен JSON файлов
    json_numbers = set()
    for json_file in json_files:
        filename = os.path.basename(json_file)
        # Убираем расширение .json
        number = filename.replace('.json', '')
        json_numbers.add(number)

    print(f"Найдено {len(json_numbers)} JSON файлов")
    print(f"Номера из JSON файлов: {sorted(json_numbers)}")

    # Читаем содержимое txt файла
    with open(txt_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Сохраняем исходные строки для диагностики
    original_lines = lines.copy()

    # Фильтруем строки
    filtered_lines = []
    removed_count = 0

    for line in lines:
        # Ищем номер телефона в строке (формат +номер)
        phone_match = re.search(r'\+(\d+)', line)

        if phone_match:
            phone_number = phone_match.group(1)  # Номер без знака +

            # Проверяем, есть ли соответствующий JSON файл
            if phone_number in json_numbers:
                print(f"Удаляется строка: {line.strip()}")
                removed_count += 1
                continue  # Пропускаем эту строку

        # Добавляем строку в отфильтрованный список
        filtered_lines.append(line)

    # Обрабатываем OTP коды если нужно
    if remove_otp_codes:
        print("\nУдаление OTP кодов из оставшихся строк...")
        cleaned_lines = []
        for line in filtered_lines:
            # Если строка содержит номер телефона, удаляем OTP код
            if re.search(r'^\d+\.\s*\+\d+', line.strip()):
                # Убираем "+ OTP код: XXXXX" из строки
                cleaned_line = re.sub(r'\s*\+\s*OTP код:\s*\d+', '', line)
                cleaned_lines.append(cleaned_line)
                print(f"Очищено: {line.strip()} -> {cleaned_line.strip()}")
            else:
                # Оставляем строку без изменений (заголовки страниц и пустые строки)
                cleaned_lines.append(line)
        filtered_lines = cleaned_lines

    # Записываем отфильтрованные строки обратно в файл
    with open(txt_file_path, 'w', encoding='utf-8') as file:
        file.writelines(filtered_lines)

    # Диагностика для понимания расхождений
    print(f"\n=== ДИАГНОСТИКА ===")
    print(f"JSON файлов найдено: {len(json_numbers)}")
    print(f"Строк удалено: {removed_count}")
    print(f"Разница: {len(json_numbers) - removed_count}")

    # Находим номера из JSON, которые НЕ были найдены в ИСХОДНОМ txt файле
    not_found_in_txt = []
    for json_number in json_numbers:
        found = False
        for line in original_lines:  # Используем исходные строки!
            if f'+{json_number}' in line:
                found = True
                break

        if not found:
            not_found_in_txt.append(json_number)

    if not_found_in_txt:
        print(f"\nНомера из JSON, которые НЕ найдены в исходном txt файле ({len(not_found_in_txt)} шт.):")
        for i, number in enumerate(sorted(not_found_in_txt), 1):
            print(f"  {i}. {number}")
            if i >= 10:  # Показываем только первые 10
                print(f"  ... и еще {len(not_found_in_txt) - 10}")
                break
    else:
        print("\nВсе номера из JSON файлов найдены в txt файле!")

    if remove_otp_codes:
        print(f"\nГотово! Удалено {removed_count} строк(и) и очищены OTP коды")
    else:
        print(f"\nГотово! Удалено {removed_count} строк(и)")


def main():
    """
    Основная функция для запуска скрипта
    """

    # Путь к txt файлу (замените на свой путь)
    txt_file = r"D:\NumberFinder\phone_numbers.txt"

    # Путь к директории с JSON файлами (по умолчанию та же директория)
    json_directory = r"D:\NumberFinder."  # Текущая директория, можете изменить на нужную

    # Если хотите указать конкретные пути:
    # txt_file = r"C:\path\to\your\список_номеров.txt"
    # json_directory = r"C:\path\to\your\json_files"

    print("Запуск скрипта для удаления номеров...")
    print(f"Txt файл: {txt_file}")
    print(f"Директория с JSON: {json_directory}")

    remove_numbers_with_json_files(txt_file, json_directory)


if __name__ == "__main__":
    main()

