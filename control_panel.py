import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import sys
import os
import threading
from datetime import datetime
import locale


class PhoneNumbersEditor:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.current_file_path = None  # Для отслеживания пути к файлу

    def open_editor(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("📱 Phone Numbers Editor - phone_numbers.txt")
        self.window.geometry("600x500")
        self.window.configure(bg='#f0f0f0')

        # Заголовок
        title_frame = tk.Frame(self.window, bg='#34495e', height=50)
        title_frame.pack(fill='x', padx=10, pady=10)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="📱 Просмотр и редактирование номеров телефонов",
            font=('Arial', 12, 'bold'),
            fg='white',
            bg='#34495e'
        )
        title_label.pack(pady=15)

        # Панель кнопок
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(fill='x', padx=10, pady=(0, 5))

        # Кнопка обновить
        refresh_btn = tk.Button(
            button_frame,
            text="🔄 Обновить",
            command=self.load_file,
            bg='#3498db',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=15
        )
        refresh_btn.pack(side='left', padx=(0, 5))

        # Кнопка сохранить
        save_btn = tk.Button(
            button_frame,
            text="💾 Сохранить",
            command=self.save_file,
            bg='#27ae60',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=15
        )
        save_btn.pack(side='left', padx=5)

        # Кнопка очистить
        clear_btn = tk.Button(
            button_frame,
            text="🗑️ Очистить всё",
            command=self.clear_file,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=15
        )
        clear_btn.pack(side='left', padx=5)

        # Информация о файле
        self.info_label = tk.Label(
            button_frame,
            text="",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        self.info_label.pack(side='right')

        # Текстовое поле для редактирования
        text_frame = tk.Frame(self.window, bg='#f0f0f0')
        text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 11),
            bg='white',
            fg='#2c3e50',
            insertbackground='#2c3e50',
            selectbackground='#3498db',
            selectforeground='white'
        )
        self.text_area.pack(fill='both', expand=True)

        # Загружаем содержимое файла
        self.load_file()

        # Обработка закрытия окна
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_file(self):
        """Загружает содержимое файла phone_numbers.txt"""
        # Проверяем несколько возможных путей к файлу
        possible_paths = [
            'phone_numbers.txt',
            'data/phone_numbers.txt',
            os.path.join('data', 'phone_numbers.txt'),
            os.path.join(os.getcwd(), 'data', 'phone_numbers.txt')
        ]

        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break

        try:
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(1.0, content)

                # Подсчитываем количество номеров
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                phone_count = len(lines)
                file_size = os.path.getsize(file_path)

                self.info_label.config(
                    text=f"Номеров: {phone_count} | Размер: {file_size} байт | Путь: {file_path}"
                )
                self.current_file_path = file_path  # Сохраняем путь для сохранения
            else:
                # Создаем папку data если её нет
                if not os.path.exists('data'):
                    os.makedirs('data')

                self.current_file_path = os.path.join('data', 'phone_numbers.txt')
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(1.0,
                                      "# Файл phone_numbers.txt не найден\n# Номера телефонов будут добавлены сюда после парсинга\n# Файл будет создан в папке data/\n")
                self.info_label.config(text=f"Файл не найден | Будет создан: {self.current_file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def save_file(self):
        """Сохраняет содержимое в файл"""
        try:
            content = self.text_area.get(1.0, tk.END)

            # Создаем папку data если её нет
            if hasattr(self, 'current_file_path') and 'data' in self.current_file_path:
                os.makedirs(os.path.dirname(self.current_file_path), exist_ok=True)

            file_path = getattr(self, 'current_file_path', os.path.join('data', 'phone_numbers.txt'))

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("Успех", f"Файл успешно сохранен!\nПуть: {file_path}")
            self.load_file()  # Обновляем информацию о файле

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def clear_file(self):
        """Очищает содержимое файла"""
        result = messagebox.askyesno(
            "Подтверждение",
            "Вы уверены, что хотите очистить всё содержимое?\nЭто действие нельзя отменить!"
        )

        if result:
            self.text_area.delete(1.0, tk.END)
            try:
                file_path = getattr(self, 'current_file_path', os.path.join('data', 'phone_numbers.txt'))
                # Создаем папку если её нет
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.info_label.config(text="Файл очищен")
                messagebox.showinfo("Успех", f"Файл очищен!\nПуть: {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось очистить файл: {e}")

    def on_close(self):
        """Обработка закрытия окна"""
        self.window.destroy()
        self.window = None


class TelegramScriptsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Scripts Control Panel")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f0f0')

        # Переменные состояния
        self.running_script = None
        self.phone_editor = PhoneNumbersEditor(self.root)

        # Определение скриптов
        self.scripts = [
            {
                'id': 'phone_parser',
                'name': 'Phone Parser',
                'description': 'Парсит номера с сайта',
                'filename': 'phone_parser.py',
                'order': 1,
                'color': '#3498db',
                'has_config': True,
                'has_file_editor': True  # Флаг для показа кнопки редактора файлов
            },
            {
                'id': 'create_folders',
                'name': 'Create Folders',
                'description': 'Создает папки',
                'filename': 'create_telegram_folders.py',
                'order': 2,
                'color': '#27ae60',
                'has_config': False,
                'has_file_editor': False
            },
            {
                'id': 'telegram_sender',
                'name': 'Auto Telegram Sender',
                'description': 'Главное творение',
                'filename': 'auto_telegram_sender.py',
                'order': 3,
                'color': '#9b59b6',
                'has_config': False,
                'has_file_editor': False
            }
        ]

        self.create_widgets()

    def create_widgets(self):
        # Главный заголовок
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="🤖 Кирпи4 от Юрова",
            font=('Arial', 18, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=20)

        # Основной контейнер
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Левая панель - скрипты
        left_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

        scripts_title = tk.Label(
            left_frame,
            text="📜 Все скрипты",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        scripts_title.pack(pady=10)

        # Контейнер для скриптов с прокруткой
        canvas = tk.Canvas(left_frame, bg='white')
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        self.scripts_container = tk.Frame(canvas, bg='white')

        self.scripts_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scripts_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        scrollbar.pack(side="right", fill="y")

        self.create_script_buttons()

        # Правая панель - логи
        right_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

        logs_title_frame = tk.Frame(right_frame, bg='white')
        logs_title_frame.pack(fill='x', pady=10, padx=10)

        logs_title = tk.Label(
            logs_title_frame,
            text="📋 Execution Logs",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#2c3e50'
        )
        logs_title.pack(side='left')

        clear_logs_btn = tk.Button(
            logs_title_frame,
            text="Clear",
            command=self.clear_logs,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=10
        )
        clear_logs_btn.pack(side='right')

        # Текстовое поле для логов
        self.log_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#f8f9fa',
            fg='#2c3e50',
            state='disabled'
        )
        self.log_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Статус бар
        self.status_bar = tk.Label(
            self.root,
            text="Ready to run scripts",
            relief='sunken',
            anchor='w',
            bg='#ecf0f1',
            font=('Arial', 10)
        )
        self.status_bar.pack(fill='x', side='bottom')

    def load_config_values(self):
        """Загружает текущие значения из config.py"""
        try:
            if os.path.exists('config.py'):
                with open('config.py', 'r', encoding='utf-8') as f:
                    content = f.read()

                # Парсим START_PAGE и END_PAGE
                start_page = 1
                end_page = 1

                for line in content.split('\n'):
                    if line.strip().startswith('START_PAGE'):
                        try:
                            start_page = int(line.split('=')[1].strip())
                        except:
                            start_page = 1
                    elif line.strip().startswith('END_PAGE'):
                        try:
                            end_page = int(line.split('=')[1].strip())
                        except:
                            end_page = 1

                return start_page, end_page
        except Exception as e:
            print(f"Error loading config: {e}")

        return 1, 1

    def save_config_values(self, start_page, end_page):
        """Сохраняет значения в config.py"""
        try:
            if os.path.exists('config.py'):
                with open('config.py', 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Обновляем значения
                for i, line in enumerate(lines):
                    if line.strip().startswith('START_PAGE'):
                        lines[i] = f"START_PAGE = {start_page}\n"
                    elif line.strip().startswith('END_PAGE'):
                        lines[i] = f"END_PAGE = {end_page}\n"

                # Сохраняем обратно
                with open('config.py', 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                self.log_message(f"Config updated: START_PAGE={start_page}, END_PAGE={end_page}", 'INFO')
                return True
        except Exception as e:
            self.log_message(f"Error saving config: {e}", 'ERROR')

        return False

    def create_script_buttons(self):
        for script in self.scripts:
            # Контейнер для каждого скрипта
            script_frame = tk.Frame(
                self.scripts_container,
                bg='#f8f9fa',
                relief='solid',
                bd=1
            )
            script_frame.pack(fill='x', pady=5, padx=5)

            # Заголовок с номером
            header_frame = tk.Frame(script_frame, bg='#f8f9fa')
            header_frame.pack(fill='x', padx=10, pady=5)

            name_label = tk.Label(
                header_frame,
                text=f"{script['order']}. {script['name']}",
                font=('Arial', 12, 'bold'),
                bg='#f8f9fa',
                fg='#2c3e50',
                anchor='w'
            )
            name_label.pack(side='left')

            # Индикатор статуса
            status_frame = tk.Frame(header_frame, bg='#f8f9fa')
            status_frame.pack(side='right')

            script['status_label'] = tk.Label(
                status_frame,
                text="●",
                font=('Arial', 16),
                bg='#f8f9fa',
                fg='#95a5a6'
            )
            script['status_label'].pack()

            # Описание
            desc_label = tk.Label(
                script_frame,
                text=script['description'],
                font=('Arial', 10),
                bg='#f8f9fa',
                fg='#7f8c8d',
                wraplength=300,
                justify='left'
            )
            desc_label.pack(anchor='w', padx=10)

            # Имя файла
            file_label = tk.Label(
                script_frame,
                text=f"File: {script['filename']}",
                font=('Arial', 9),
                bg='#f8f9fa',
                fg='#95a5a6',
                justify='left'
            )
            file_label.pack(anchor='w', padx=10, pady=(0, 5))

            # Поля конфигурации для Phone Parser
            if script.get('has_config', False):
                config_frame = tk.Frame(script_frame, bg='#f8f9fa')
                config_frame.pack(fill='x', padx=10, pady=5)

                # Заголовок для настроек
                config_title = tk.Label(
                    config_frame,
                    text="⚙️ Настройки парсинга:",
                    font=('Arial', 10, 'bold'),
                    bg='#f8f9fa',
                    fg='#2c3e50'
                )
                config_title.pack(anchor='w', pady=(0, 5))

                # Поля ввода
                fields_frame = tk.Frame(config_frame, bg='#f8f9fa')
                fields_frame.pack(fill='x')

                # START_PAGE
                start_frame = tk.Frame(fields_frame, bg='#f8f9fa')
                start_frame.pack(side='left', padx=(0, 10))

                start_label = tk.Label(
                    start_frame,
                    text="Начальная страница:",
                    font=('Arial', 9),
                    bg='#f8f9fa',
                    fg='#2c3e50'
                )
                start_label.pack(anchor='w')

                script['start_page_var'] = tk.StringVar()
                start_entry = tk.Entry(
                    start_frame,
                    textvariable=script['start_page_var'],
                    font=('Arial', 9),
                    width=8,
                    relief='solid',
                    bd=1
                )
                start_entry.pack()

                # END_PAGE
                end_frame = tk.Frame(fields_frame, bg='#f8f9fa')
                end_frame.pack(side='left')

                end_label = tk.Label(
                    end_frame,
                    text="Конечная страница:",
                    font=('Arial', 9),
                    bg='#f8f9fa',
                    fg='#2c3e50'
                )
                end_label.pack(anchor='w')

                script['end_page_var'] = tk.StringVar()
                end_entry = tk.Entry(
                    end_frame,
                    textvariable=script['end_page_var'],
                    font=('Arial', 9),
                    width=8,
                    relief='solid',
                    bd=1
                )
                end_entry.pack()

                # Загружаем текущие значения из config.py
                start_page, end_page = self.load_config_values()
                script['start_page_var'].set(str(start_page))
                script['end_page_var'].set(str(end_page))

            # Кнопка запуска
            script['button'] = tk.Button(
                script_frame,
                text=f"▶ Run Script",
                command=lambda s=script: self.run_script(s),
                bg=script['color'],
                fg='white',
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=20,
                pady=8
            )
            script['button'].pack(pady=10)

            # Кнопка редактора файлов для Phone Parser
            if script.get('has_file_editor', False):
                file_editor_btn = tk.Button(
                    script_frame,
                    text="📱 Просмотр номеров (phone_numbers.txt)",
                    command=self.phone_editor.open_editor,
                    bg='#f39c12',
                    fg='white',
                    font=('Arial', 9, 'bold'),
                    relief='flat',
                    padx=15,
                    pady=6
                )
                file_editor_btn.pack(pady=(0, 10))

    def log_message(self, message, level='INFO'):
        """Добавляет сообщение в лог с корректной обработкой кодировки"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Очищаем сообщение от проблемных символов
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='replace')

            # Определяем цвет по уровню
            color_map = {
                'INFO': '#3498db',
                'SUCCESS': '#27ae60',
                'ERROR': '#e74c3c',
                'WARNING': '#f39c12'
            }
            color = color_map.get(level, '#3498db')

            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n")

            # Добавляем цветовую разметку для последней строки
            line_start = self.log_text.index("end-2c linestart")
            line_end = self.log_text.index("end-1c")

            tag_name = f"level_{level}_{timestamp}".replace(':', '_').replace('.', '_')
            self.log_text.tag_add(tag_name, line_start, line_end)
            self.log_text.tag_config(tag_name, foreground=color)

            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)

        except Exception as e:
            print(f"Error logging message: {e}")

    def clear_logs(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def update_script_status(self, script, status):
        """Обновляет статус скрипта (waiting/running/success/error)"""
        color_map = {
            'waiting': '#95a5a6',
            'running': '#f39c12',
            'success': '#27ae60',
            'error': '#e74c3c'
        }

        script['status_label'].config(fg=color_map.get(status, '#95a5a6'))

        if status == 'running':
            script['status_label'].config(text="⟳")
            # Анимация вращения
            self.animate_running_status(script)
        else:
            script['status_label'].config(text="●")

    def animate_running_status(self, script):
        """Простая анимация для запущенного скрипта"""
        if self.running_script == script['id']:
            current = script['status_label'].cget('text')
            next_char = {'⟳': '⟲', '⟲': '⟳'}.get(current, '⟳')
            script['status_label'].config(text=next_char)
            self.root.after(500, lambda: self.animate_running_status(script))

    def run_script(self, script):
        if self.running_script:
            messagebox.showwarning(
                "Script Running",
                f"Cannot start {script['name']} - another script is already running"
            )
            return

        # Проверяем существование файла
        if not os.path.exists(script['filename']):
            self.log_message(f"File '{script['filename']}' not found in current directory", 'ERROR')
            messagebox.showerror(
                "File Not Found",
                f"Script file '{script['filename']}' not found in current directory"
            )
            return

        # Если это Phone Parser, сначала сохраняем конфигурацию
        if script.get('has_config', False):
            try:
                start_page = int(script['start_page_var'].get())
                end_page = int(script['end_page_var'].get())

                if start_page < 1 or end_page < 1:
                    raise ValueError("Страницы должны быть больше 0")

                if start_page > end_page:
                    raise ValueError("Начальная страница не может быть больше конечной")

                # Сохраняем в config.py
                if not self.save_config_values(start_page, end_page):
                    return

            except ValueError as e:
                messagebox.showerror(
                    "Invalid Input",
                    f"Ошибка в настройках: {str(e)}"
                )
                return

        self.running_script = script['id']

        # Отключаем все кнопки
        for s in self.scripts:
            s['button'].config(state='disabled')

        self.update_script_status(script, 'running')
        self.status_bar.config(text=f"Running {script['name']}...")
        self.log_message(f"Starting {script['name']} ({script['filename']})...")

        # Запускаем скрипт в отдельном потоке
        thread = threading.Thread(
            target=self.execute_script,
            args=(script,),
            daemon=True
        )
        thread.start()

    def execute_script(self, script):
        """Выполняет скрипт в отдельном потоке с правильной обработкой кодировки"""
        try:
            # Запускаем Python скрипт с UTF-8 кодировкой
            process = subprocess.Popen(
                [sys.executable, script['filename']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Читаем вывод построчно
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    clean_output = output.strip()
                    if clean_output:  # Только непустые строки
                        self.root.after(0, self.log_message, clean_output, 'INFO')

            # Получаем код возврата
            return_code = process.poll()

            if return_code == 0:
                self.root.after(0, self.script_finished, script, True, None)
            else:
                stderr_output = process.stderr.read()
                if stderr_output:
                    self.root.after(0, self.script_finished, script, False, stderr_output.strip())
                else:
                    self.root.after(0, self.script_finished, script, False, f"Script exited with code {return_code}")

        except UnicodeDecodeError as e:
            error_msg = f"Encoding error: {str(e)}"
            self.root.after(0, self.script_finished, script, False, error_msg)
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self.root.after(0, self.script_finished, script, False, error_msg)

    def script_finished(self, script, success, error_msg=None):
        """Вызывается когда скрипт завершился"""
        self.running_script = None

        # Включаем все кнопки обратно
        for s in self.scripts:
            s['button'].config(state='normal')

        if success:
            self.update_script_status(script, 'success')
            self.log_message(f"{script['name']} completed successfully!", 'SUCCESS')
            self.status_bar.config(text=f"{script['name']} completed successfully")
        else:
            self.update_script_status(script, 'error')
            if error_msg:
                self.log_message(f"Error in {script['name']}: {error_msg}", 'ERROR')
            self.log_message(f"{script['name']} failed!", 'ERROR')
            self.status_bar.config(text=f"{script['name']} failed")

        # Возвращаем статус в "готов" через 5 секунд
        self.root.after(5000, lambda: self.status_bar.config(text="Ready to run scripts"))
        self.root.after(5000, lambda: self.update_script_status(script, 'waiting'))


def main():
    # Устанавливаем кодировку для консоли
    if os.name == 'nt':  # Windows
        try:
            os.system('chcp 65001 >nul 2>&1')  # UTF-8
        except:
            pass

    root = tk.Tk()
    app = TelegramScriptsGUI(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application closed by user")


if __name__ == "__main__":
    main()
