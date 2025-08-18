import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import os
import time
import sys
from datetime import datetime
import json

# Импорт ваших существующих модулей БЕЗ ИЗМЕНЕНИЙ
import config
from auto_telegram_sender import AutoTelegramSender
from phone_parser import PhoneNumberParser
from create_telegram_folders import create_folders_and_copy_telegram
from config import *


class RoundedFrame(tk.Frame):
    """Кастомный Frame с закругленными углами"""

    def __init__(self, parent, bg='#ffffff', corner_radius=10, **kwargs):
        super().__init__(parent, **kwargs)
        self.bg = bg
        self.corner_radius = corner_radius
        self.configure(bg=bg)


class ExpandableCard(tk.Frame):
    """Расширяемая карточка с анимацией"""

    def __init__(self, parent, title, bg='#ffffff', **kwargs):
        super().__init__(parent, bg=parent['bg'], **kwargs)

        self.title = title
        self.bg = bg
        self.is_expanded = False
        self.content_frame = None

        # Создание заголовка
        self.header_frame = tk.Frame(self, bg=bg, cursor='hand2')
        self.header_frame.pack(fill='x')

        # Добавление тени и закругления (имитация)
        self.configure(relief='flat', bd=0)

        # Заголовок с иконкой
        header_content = tk.Frame(self.header_frame, bg=bg)
        header_content.pack(fill='x', padx=15, pady=12)

        self.title_label = tk.Label(header_content, text=title,
                                    font=('Segoe UI', 11, 'bold'),
                                    fg='#323130', bg=bg)
        self.title_label.pack(side='left')

        self.arrow_label = tk.Label(header_content, text='▶',
                                    font=('Segoe UI', 10),
                                    fg='#605e5c', bg=bg)
        self.arrow_label.pack(side='right')

        # Привязка событий
        self.header_frame.bind('<Button-1>', self.toggle_expand)
        header_content.bind('<Button-1>', self.toggle_expand)
        self.title_label.bind('<Button-1>', self.toggle_expand)
        self.arrow_label.bind('<Button-1>', self.toggle_expand)

        # Hover эффекты
        self.header_frame.bind('<Enter>', self.on_enter)
        self.header_frame.bind('<Leave>', self.on_leave)

    def on_enter(self, e):
        """Hover эффект"""
        self.header_frame.configure(bg='#f3f2f1')
        self.title_label.configure(bg='#f3f2f1')
        self.arrow_label.configure(bg='#f3f2f1')

    def on_leave(self, e):
        """Убрать hover эффект"""
        self.header_frame.configure(bg=self.bg)
        self.title_label.configure(bg=self.bg)
        self.arrow_label.configure(bg=self.bg)

    def toggle_expand(self, event=None):
        """Переключение раскрытия/сворачивания"""
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """Раскрытие карточки"""
        if self.content_frame:
            self.content_frame.pack(fill='x', padx=15, pady=(0, 15))
        self.arrow_label.configure(text='▼')
        self.is_expanded = True
        # Обновляем скролл после изменения размера
        self.master.after(50, self._update_parent_scroll)

    def collapse(self):
        """Сворачивание карточки"""
        if self.content_frame:
            self.content_frame.pack_forget()
        self.arrow_label.configure(text='▶')
        self.is_expanded = False
        # Обновляем скролл после изменения размера
        self.master.after(50, self._update_parent_scroll)

    def _update_parent_scroll(self):
        """Обновление скролла левой панели"""
        # Используем переданную ссылку на главный класс
        if hasattr(self, '_control_panel'):
            # Обновляем только левый скролл
            if hasattr(self._control_panel, 'update_left_scroll'):
                self._control_panel.update_left_scroll()

    def set_content(self, content_frame):
        """Установка контента карточки"""
        self.content_frame = content_frame


class TelegramControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📱 Telegram Automation Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f5f5f5')
        self.root.minsize(1000, 600)

        # Настройка стилей Windows 11
        self.setup_styles()

        # Очередь для межпоточного взаимодействия
        self.message_queue = queue.Queue()

        # Переменные состояния
        self.is_parsing = False
        self.is_processing = False
        self.auto_sender = None
        self.parser = None

        # Статистика
        self.stats = {
            'processed': 0,
            'banned': 0,
            'no_code': 0,
            'errors': 0,
            'total': 0
        }

        self.setup_ui()
        self.update_stats()

        # Запуск обновления интерфейса
        self.root.after(100, self.process_queue)

    def setup_styles(self):
        """Настройка корпоративных стилей"""
        style = ttk.Style()
        style.theme_use('clam')

        # Улучшенная корпоративная цветовая схема
        self.colors = {
            'primary': '#0066cc',  # Современный синий
            'primary_dark': '#0052a3',
            'primary_light': '#4d94ff',
            'secondary': '#f0f4f8',  # Светло-голубой фон
            'background': '#ffffff',
            'surface': '#f8f9fa',
            'card_shadow': '#e0e6ed',
            'text': '#2c3e50',  # Темно-серый текст
            'text_secondary': '#718096',
            'success': '#38a169',  # Зеленый успех
            'warning': '#ed8936',  # Оранжевое предупреждение
            'error': '#e53e3e',  # Красная ошибка
            'border': '#e2e8f0',  # Серая граница
            'hover': '#edf2f7'  # Hover эффект
        }

        # Настройка стилей ttk
        style.configure('Title.TLabel',
                        font=('Segoe UI', 24, 'normal'),
                        foreground=self.colors['primary'],
                        background='#f5f5f5')

        style.configure('Heading.TLabel',
                        font=('Segoe UI', 12, 'bold'),
                        foreground=self.colors['text'],
                        background=self.colors['background'])

        style.configure('Custom.TButton',
                        font=('Segoe UI', 10),
                        padding=(20, 10))

        style.configure('Status.TLabel',
                        font=('Segoe UI', 9),
                        foreground=self.colors['text_secondary'])

    def create_card(self, parent, title, content_height=200):
        """Создание карточки в корпоративном стиле"""
        card_frame = tk.Frame(parent, bg=self.colors['background'],
                              relief='flat', bd=1)
        card_frame.configure(highlightbackground=self.colors['border'],
                             highlightthickness=1)

        # Заголовок карточки
        header_frame = tk.Frame(card_frame, bg=self.colors['secondary'], height=40)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        title_label = tk.Label(header_frame, text=title,
                               font=('Segoe UI', 11, 'bold'),
                               fg=self.colors['text'],
                               bg=self.colors['secondary'])
        title_label.pack(side='left', padx=15, pady=12)

        # Контент карточки
        content_frame = tk.Frame(card_frame, bg=self.colors['background'])
        content_frame.pack(fill='both', expand=True, padx=15, pady=15)

        return card_frame, content_frame

    def create_action_button(self, parent, text, command, style='primary', icon=''):
        """Создание корпоративной кнопки"""
        colors = {
            'primary': (self.colors['primary'], '#ffffff'),
            'secondary': (self.colors['surface'], self.colors['text']),
            'success': (self.colors['success'], '#ffffff'),
            'warning': (self.colors['warning'], '#ffffff'),
            'error': (self.colors['error'], '#ffffff')
        }

        bg_color, fg_color = colors.get(style, colors['primary'])

        btn = tk.Button(parent,
                        text=f"{icon} {text}" if icon else text,
                        command=command,
                        bg=bg_color,
                        fg=fg_color,
                        font=('Segoe UI', 10),
                        relief='flat',
                        cursor='hand2',
                        padx=20,
                        pady=8,
                        border=0)

        # Hover эффекты
        def on_enter(e):
            if style == 'primary':
                btn.configure(bg=self.colors['primary_dark'])
            else:
                btn.configure(bg=self.lighten_color(bg_color))

        def on_leave(e):
            btn.configure(bg=bg_color)

        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        return btn

    def setup_ui(self):
        """Создание корпоративного интерфейса с прокруткой"""

        # ==== ЗАГОЛОВОК ====
        header_frame = tk.Frame(self.root, bg='#ffffff', height=70)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)

        # Добавляем тень
        shadow_frame = tk.Frame(self.root, bg='#e1dfdd', height=2)
        shadow_frame.pack(fill='x')

        header_content = tk.Frame(header_frame, bg='#ffffff')
        header_content.pack(fill='both', expand=True, padx=25, pady=15)

        # Логотип и заголовок
        title_frame = tk.Frame(header_content, bg='#ffffff')
        title_frame.pack(side='left')

        main_title = tk.Label(title_frame, text="📱 Telegram Automation Manager",
                              font=('Segoe UI', 18, 'bold'),
                              fg=self.colors['primary'],
                              bg='#ffffff')
        main_title.pack(anchor='w')

        subtitle = tk.Label(title_frame, text="Управление автоматизацией и мониторинг",
                            font=('Segoe UI', 9),
                            fg=self.colors['text_secondary'],
                            bg='#ffffff')
        subtitle.pack(anchor='w', pady=(2, 0))

        # Индикатор статуса
        status_frame = tk.Frame(header_content, bg='#ffffff')
        status_frame.pack(side='right')

        self.status_indicator = tk.Label(status_frame, text="🟢",
                                         font=('Segoe UI', 14),
                                         bg='#ffffff')
        self.status_indicator.pack(side='left', padx=(0, 8))

        self.main_status_label = tk.Label(status_frame, text="Система готова",
                                          font=('Segoe UI', 10, 'bold'),
                                          fg=self.colors['success'],
                                          bg='#ffffff')
        self.main_status_label.pack(side='left')

        # ==== ОСНОВНОЙ КОНТЕНТ БЕЗ ПРОКРУТКИ ====
        main_content_frame = tk.Frame(self.root, bg='#f5f5f5')
        main_content_frame.pack(fill='both', expand=True)

        # Контент основной области
        main_content = tk.Frame(main_content_frame, bg='#f5f5f5')
        main_content.pack(fill='both', expand=True, padx=20, pady=15)

        # Верхняя панель - статистика
        self.create_stats_panel(main_content)

        # Средняя панель - действия и мониторинг
        content_container = tk.Frame(main_content, bg='#f5f5f5')
        content_container.pack(fill='both', expand=True, pady=(15, 0))

        # Левая колонка - управление (расширяемые карточки) с отдельным скроллом
        left_column_container = tk.Frame(content_container, bg='#f5f5f5', width=380)
        left_column_container.pack(side='left', fill='both', padx=(0, 15))
        left_column_container.pack_propagate(False)

        # Создаем отдельный Canvas со скроллом для левой панели
        left_canvas = tk.Canvas(left_column_container, bg='#f5f5f5', highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_column_container, orient='vertical', command=left_canvas.yview)
        left_scrollable_frame = tk.Frame(left_canvas, bg='#f5f5f5')

        def configure_left_scroll(event=None):
            # Обновляем scrollregion для левой панели
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))
            # Устанавливаем ширину левого фрейма
            if event and event.widget == left_canvas:
                canvas_width = event.width
                left_canvas.itemconfig(left_canvas_window, width=canvas_width)

        left_scrollable_frame.bind('<Configure>', configure_left_scroll)
        left_canvas.bind('<Configure>', configure_left_scroll)

        left_canvas_window = left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor='nw')
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_canvas.pack(side='left', fill='both', expand=True)
        left_scrollbar.pack(side='right', fill='y')

        # Привязываем скролл колесика мыши для левой панели
        def _on_left_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _bind_to_left_mousewheel(event):
            # Привязываем левый скролл
            left_canvas.bind_all('<MouseWheel>', _on_left_mousewheel)

        def _unbind_from_left_mousewheel(event):
            # Отвязываем левый скролл
            left_canvas.unbind_all('<MouseWheel>')

        left_canvas.bind('<Enter>', _bind_to_left_mousewheel)
        left_canvas.bind('<Leave>', _unbind_from_left_mousewheel)

        # Функция для обновления скролла левой панели
        def update_left_scroll():
            left_canvas.update_idletasks()
            configure_left_scroll()

        self.update_left_scroll = update_left_scroll

        self.create_expandable_control_panel(left_scrollable_frame)

        # Правая колонка - мониторинг
        right_column = tk.Frame(content_container, bg='#f5f5f5')
        right_column.pack(side='right', fill='both', expand=True)

        self.create_monitoring_panel(right_column)

        # ==== НИЖНЯЯ ПАНЕЛЬ - СТАТУС ====
        bottom_frame = tk.Frame(self.root, bg='#ffffff', height=40)
        bottom_frame.pack(fill='x')
        bottom_frame.pack_propagate(False)

        # Тень сверху
        shadow_top = tk.Frame(self.root, bg='#e1dfdd', height=1)
        shadow_top.pack(fill='x', before=bottom_frame)

        status_content = tk.Frame(bottom_frame, bg='#ffffff')
        status_content.pack(fill='both', expand=True, padx=25, pady=10)

        self.bottom_status = tk.Label(status_content, text="Готов к работе",
                                      font=('Segoe UI', 8),
                                      fg=self.colors['text_secondary'],
                                      bg='#ffffff')
        self.bottom_status.pack(side='left')

        # Время
        self.time_label = tk.Label(status_content, text="",
                                   font=('Segoe UI', 8),
                                   fg=self.colors['text_secondary'],
                                   bg='#ffffff')
        self.time_label.pack(side='right')
        self.update_time()

    def create_stats_panel(self, parent):
        """Создание панели статистики с закругленными карточками"""
        stats_frame = tk.Frame(parent, bg='#f5f5f5')
        stats_frame.pack(fill='x', pady=(0, 15))

        # Статистические карточки
        stat_configs = [
            ('Всего номеров', 'total', '📊', self.colors['primary']),
            ('Обработано', 'processed', '✅', self.colors['success']),
            ('Забанено', 'banned', '🚫', self.colors['error']),
            ('Без кода', 'no_code', '⚠️', self.colors['warning']),
            ('Ошибки', 'errors', '❌', self.colors['error'])
        ]

        self.stat_widgets = {}

        for i, (title, key, icon, color) in enumerate(stat_configs):
            # Контейнер для закругления
            stat_container = tk.Frame(stats_frame, bg='#f5f5f5')
            stat_container.pack(side='left', fill='both', expand=True,
                                padx=(0, 8) if i < len(stat_configs) - 1 else (0, 0))

            # Основная карточка с тенью
            stat_card = tk.Frame(stat_container, bg=self.colors['background'],
                                 relief='flat', bd=0)
            stat_card.pack(fill='both', expand=True, padx=1, pady=1)

            # Добавляем тень (имитация)
            shadow_frame = tk.Frame(stat_container, bg='#e0e0e0', height=2)
            shadow_frame.pack(fill='x')

            # Иконка
            icon_label = tk.Label(stat_card, text=icon,
                                  font=('Segoe UI', 18),
                                  bg=self.colors['background'])
            icon_label.pack(pady=(12, 3))

            # Значение
            value_label = tk.Label(stat_card, text="0",
                                   font=('Segoe UI', 22, 'bold'),
                                   fg=color,
                                   bg=self.colors['background'])
            value_label.pack()

            # Название
            title_label = tk.Label(stat_card, text=title,
                                   font=('Segoe UI', 9),
                                   fg=self.colors['text_secondary'],
                                   bg=self.colors['background'])
            title_label.pack(pady=(2, 12))

            self.stat_widgets[key] = value_label

    def create_expandable_control_panel(self, parent):
        """Создание панели управления с расширяемыми карточками"""

        # === КАРТОЧКА ПАРСИНГА ===
        parsing_card = ExpandableCard(parent, "📱 Парсинг номеров", bg=self.colors['background'])
        parsing_card._control_panel = self  # Передаем ссылку на главный класс
        parsing_card.pack(fill='x', pady=(0, 10))

        # Контент парсинга
        parsing_content = tk.Frame(parsing_card, bg=self.colors['background'])

        # Стилизованные кнопки с закруглениями
        btn_frame1 = tk.Frame(parsing_content, bg=self.colors['background'])
        btn_frame1.pack(fill='x', pady=3)

        start_parse_btn = self.create_rounded_button(btn_frame1, "🚀 Запустить парсер",
                                                     self.start_parsing, 'primary')
        start_parse_btn.pack(fill='x')

        btn_frame3 = tk.Frame(parsing_content, bg=self.colors['background'])
        btn_frame3.pack(fill='x', pady=3)

        show_numbers_btn = self.create_rounded_button(btn_frame3, "📋 Показать номера",
                                                      self.show_numbers, 'secondary')
        show_numbers_btn.pack(fill='x')

        parsing_card.set_content(parsing_content)

        # === КАРТОЧКА СОЗДАНИЯ ПАПОК ===
        folders_card = ExpandableCard(parent, "📁 Создание папок", bg=self.colors['background'])
        folders_card._control_panel = self  # Передаем ссылку на главный класс
        folders_card.pack(fill='x', pady=(0, 10))

        # Контент создания папок
        folders_content = tk.Frame(folders_card, bg=self.colors['background'])

        btn_frame_folders1 = tk.Frame(folders_content, bg=self.colors['background'])
        btn_frame_folders1.pack(fill='x', pady=3)

        create_folders_btn = self.create_rounded_button(btn_frame_folders1, "📁 Создать папки",
                                                        self.create_folders, 'success')
        create_folders_btn.pack(fill='x')

        btn_frame_folders2 = tk.Frame(folders_content, bg=self.colors['background'])
        btn_frame_folders2.pack(fill='x', pady=3)

        open_folder_btn = self.create_rounded_button(btn_frame_folders2, "🗂️ Открыть базовую папку",
                                                     self.open_base_folder, 'secondary')
        open_folder_btn.pack(fill='x')

        folders_card.set_content(folders_content)

        # === КАРТОЧКА ОБРАБОТКИ ===
        processing_card = ExpandableCard(parent, "🤖 Обработка номеров", bg=self.colors['background'])
        processing_card._control_panel = self  # Передаем ссылку на главный класс
        processing_card.pack(fill='x', pady=(0, 10))

        # Контент обработки
        processing_content = tk.Frame(processing_card, bg=self.colors['background'])

        btn_frame4 = tk.Frame(processing_content, bg=self.colors['background'])
        btn_frame4.pack(fill='x', pady=3)

        start_proc_btn = self.create_rounded_button(btn_frame4, "▶️ Запустить обработку",
                                                    self.start_processing, 'primary')
        start_proc_btn.pack(fill='x')

        btn_frame5 = tk.Frame(processing_content, bg=self.colors['background'])
        btn_frame5.pack(fill='x', pady=3)

        pause_btn = self.create_rounded_button(btn_frame5, "⏸️ Приостановить",
                                               self.pause_processing, 'warning')
        pause_btn.pack(fill='x')

        btn_frame6 = tk.Frame(processing_content, bg=self.colors['background'])
        btn_frame6.pack(fill='x', pady=3)

        stop_proc_btn = self.create_rounded_button(btn_frame6, "⏹️ Остановить",
                                                   self.stop_processing, 'error')
        stop_proc_btn.pack(fill='x')

        btn_frame7 = tk.Frame(processing_content, bg=self.colors['background'])
        btn_frame7.pack(fill='x', pady=3)

        reset_btn = self.create_rounded_button(btn_frame7, "🔄 Сброс статистики",
                                               self.reset_stats, 'secondary')
        reset_btn.pack(fill='x')

        processing_card.set_content(processing_content)

        # Обновляем левый скролл после создания всех карточек
        if hasattr(self, 'update_left_scroll'):
            self.root.after(150, self.update_left_scroll)

        # === КАРТОЧКА УПРАВЛЕНИЯ ФАЙЛАМИ ===
        files_card = ExpandableCard(parent, "📂 Управление данными", bg=self.colors['background'])
        files_card._control_panel = self  # Передаем ссылку на главный класс
        files_card.pack(fill='x', pady=(0, 10))

        # Контент файлов
        files_content = tk.Frame(files_card, bg=self.colors['background'])

        btn_frame9 = tk.Frame(files_content, bg=self.colors['background'])
        btn_frame9.pack(fill='x', pady=3)

        export_btn = self.create_rounded_button(btn_frame9, "📊 Экспорт результатов",
                                                self.export_results, 'secondary')
        export_btn.pack(fill='x')

        btn_frame10 = tk.Frame(files_content, bg=self.colors['background'])
        btn_frame10.pack(fill='x', pady=3)

        settings_btn = self.create_rounded_button(btn_frame10, "⚙️ Настройки",
                                                  self.open_settings, 'secondary')
        settings_btn.pack(fill='x')

        btn_frame11 = tk.Frame(files_content, bg=self.colors['background'])
        btn_frame11.pack(fill='x', pady=3)

        clear_btn = self.create_rounded_button(btn_frame11, "🗑️ Очистить данные",
                                               self.clear_data, 'error')
        clear_btn.pack(fill='x')

        files_card.set_content(files_content)

        # По умолчанию раскрываем первую карточку
        parsing_card.expand()

        # Финальное обновление левого скролла после создания всего интерфейса
        if hasattr(self, 'update_left_scroll'):
            self.root.after(250, self.update_left_scroll)

    def create_rounded_button(self, parent, text, command, style='primary'):
        """Создание стилизованной кнопки с закруглениями"""
        colors = {
            'primary': {
                'bg': self.colors['primary'],
                'fg': '#ffffff',
                'hover': self.colors['primary_dark']
            },
            'secondary': {
                'bg': self.colors['surface'],
                'fg': self.colors['text'],
                'hover': '#e9ecef'
            },
            'success': {
                'bg': self.colors['success'],
                'fg': '#ffffff',
                'hover': '#0e6e0e'
            },
            'warning': {
                'bg': self.colors['warning'],
                'fg': '#ffffff',
                'hover': '#e67e00'
            },
            'error': {
                'bg': self.colors['error'],
                'fg': '#ffffff',
                'hover': '#c23616'
            }
        }

        style_config = colors.get(style, colors['primary'])

        # Создаем контейнер для имитации закругления
        btn_container = tk.Frame(parent, bg=parent['bg'])

        btn = tk.Button(btn_container,
                        text=text,
                        command=command,
                        bg=style_config['bg'],
                        fg=style_config['fg'],
                        font=('Segoe UI', 9, 'bold'),
                        relief='flat',
                        cursor='hand2',
                        pady=10,
                        border=0,
                        activebackground=style_config['hover'],
                        activeforeground=style_config['fg'])

        btn.pack(fill='x', padx=2, pady=1)  # Небольшие отступы для имитации закругления

        # Hover эффекты
        def on_enter(e):
            btn.configure(bg=style_config['hover'])

        def on_leave(e):
            btn.configure(bg=style_config['bg'])

        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        return btn_container

    def create_monitoring_panel(self, parent):
        """Создание панели мониторинга с закругленными карточками"""

        # Прогресс карточка с закруглениями
        progress_container = tk.Frame(parent, bg='#f5f5f5')
        progress_container.pack(fill='x', pady=(0, 15))

        progress_card = tk.Frame(progress_container, bg=self.colors['background'], relief='flat', bd=0)
        progress_card.pack(fill='x', padx=1, pady=1)

        # Тень для прогресс карточки
        progress_shadow = tk.Frame(progress_container, bg='#e0e0e0', height=2)
        progress_shadow.pack(fill='x')

        # Заголовок прогресса
        progress_header = tk.Frame(progress_card, bg=self.colors['secondary'], height=35)
        progress_header.pack(fill='x')
        progress_header.pack_propagate(False)

        progress_title = tk.Label(progress_header, text="📈 Прогресс выполнения",
                                  font=('Segoe UI', 10, 'bold'),
                                  fg=self.colors['text'],
                                  bg=self.colors['secondary'])
        progress_title.pack(side='left', padx=12, pady=8)

        # Контент прогресса
        progress_content = tk.Frame(progress_card, bg=self.colors['background'])
        progress_content.pack(fill='x', padx=15, pady=12)

        self.progress_bar = ttk.Progressbar(progress_content,
                                            mode='determinate',
                                            length=300)
        self.progress_bar.pack(fill='x', pady=(0, 5))

        self.progress_text = tk.Label(progress_content, text="Готов к работе",
                                      font=('Segoe UI', 9),
                                      fg=self.colors['text_secondary'],
                                      bg=self.colors['background'])
        self.progress_text.pack(anchor='w')

        # Логи карточка с закруглениями
        logs_container = tk.Frame(parent, bg='#f5f5f5')
        logs_container.pack(fill='both', expand=True)

        logs_card = tk.Frame(logs_container, bg=self.colors['background'], relief='flat', bd=0)
        logs_card.pack(fill='both', expand=True, padx=1, pady=1)

        # Тень для логов карточки
        logs_shadow = tk.Frame(logs_container, bg='#e0e0e0', height=2)
        logs_shadow.pack(fill='x')

        # Заголовок логов
        logs_header = tk.Frame(logs_card, bg=self.colors['secondary'])
        logs_header.pack(fill='x')

        logs_header_content = tk.Frame(logs_header, bg=self.colors['secondary'])
        logs_header_content.pack(fill='x', padx=12, pady=8)

        logs_title = tk.Label(logs_header_content, text="📝 Журнал выполнения",
                              font=('Segoe UI', 10, 'bold'),
                              fg=self.colors['text'],
                              bg=self.colors['secondary'])
        logs_title.pack(side='left')

        # Кнопка очистки логов
        clear_logs_btn = tk.Button(logs_header_content, text="🗑️",
                                   command=self.clear_logs,
                                   font=('Segoe UI', 8),
                                   bg=self.colors['surface'],
                                   fg=self.colors['text'],
                                   relief='flat',
                                   cursor='hand2',
                                   padx=8, pady=2)
        clear_logs_btn.pack(side='right')

        # Контент логов
        logs_content = tk.Frame(logs_card, bg=self.colors['background'])
        logs_content.pack(fill='both', expand=True, padx=12, pady=12)

        # Область логов
        self.logs_text = scrolledtext.ScrolledText(logs_content,
                                                   bg='#fafafa',
                                                   fg=self.colors['text'],
                                                   font=('Consolas', 8),
                                                   wrap='word',
                                                   relief='flat',
                                                   bd=0,
                                                   height=15)
        self.logs_text.configure(highlightbackground=self.colors['border'],
                                 highlightthickness=1)
        self.logs_text.pack(fill='both', expand=True)

        # Настройка тегов для логов
        self.logs_text.tag_configure('INFO', foreground=self.colors['text'])
        self.logs_text.tag_configure('SUCCESS', foreground=self.colors['success'])
        self.logs_text.tag_configure('WARNING', foreground=self.colors['warning'])
        self.logs_text.tag_configure('ERROR', foreground=self.colors['error'])

    def lighten_color(self, color):
        """Осветление цвета для hover эффектов"""
        return color  # Упрощенная версия

    def log_message(self, message, level='INFO'):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.message_queue.put(('log', formatted_message, level))

    def update_status(self, status, level='INFO'):
        """Обновление главного статуса"""
        colors = {
            'INFO': (self.colors['primary'], '🔵'),
            'SUCCESS': (self.colors['success'], '🟢'),
            'WARNING': (self.colors['warning'], '🟡'),
            'ERROR': (self.colors['error'], '🔴')
        }

        color, icon = colors.get(level, colors['INFO'])
        self.message_queue.put(('main_status', status, color, icon))

    def update_progress(self, value, max_value=100, text=""):
        """Обновление прогресс бара"""
        self.message_queue.put(('progress', value, max_value, text))

    def update_time(self):
        """Обновление времени"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.root.after(1000, self.update_time)

    def clear_logs(self):
        """Очистка логов"""
        self.logs_text.delete(1.0, 'end')

    def process_queue(self):
        """Обработка очереди сообщений"""
        try:
            while True:
                message_type, *args = self.message_queue.get_nowait()

                if message_type == 'log':
                    message, level = args
                    self.logs_text.insert('end', message, level)
                    self.logs_text.see('end')

                elif message_type == 'main_status':
                    status, color, icon = args
                    self.main_status_label.configure(text=status, fg=color)
                    self.status_indicator.configure(text=icon)
                    self.bottom_status.configure(text=status)

                elif message_type == 'progress':
                    value, max_value, text = args
                    if max_value > 0:
                        self.progress_bar.configure(maximum=max_value, value=value)
                        progress_percent = (value / max_value) * 100
                        display_text = f"{text} ({progress_percent:.1f}%)" if text else f"Прогресс: {progress_percent:.1f}%"
                        self.progress_text.configure(text=display_text)

                elif message_type == 'stats':
                    self.update_stats_display()

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    def update_stats_display(self):
        """Обновление отображения статистики"""
        for key, widget in self.stat_widgets.items():
            widget.configure(text=str(self.stats[key]))

    # ==== МЕТОДЫ УПРАВЛЕНИЯ (те же что и раньше) ====

    def start_parsing(self):
        """Запуск парсера в отдельном потоке"""
        if self.is_parsing:
            messagebox.showwarning("Предупреждение", "Парсер уже запущен!")
            return

        def parse_thread():
            try:
                self.is_parsing = True
                self.log_message("Запуск парсера номеров...", 'INFO')
                self.update_status("Парсинг в процессе...", 'INFO')

                self.parser = PhoneNumberParser()

                # Получаем актуальные настройки из конфига
                start_page = getattr(config, 'START_PAGE', 1)
                end_page = getattr(config, 'END_PAGE', 10)

                # Авторизация с передачей стартовой страницы
                self.log_message("Выполняется авторизация...", 'INFO')
                if not self.parser.login(start_page):
                    self.log_message("Ошибка авторизации!", 'ERROR')
                    self.update_status("Ошибка авторизации", 'ERROR')
                    return

                self.log_message("Авторизация успешна!", 'SUCCESS')

                # Парсинг
                self.log_message(f"Парсинг страниц {start_page}-{end_page}...", 'INFO')
                phone_numbers = self.parser.parse_all_pages(start_page, end_page)

                # Сохранение
                self.log_message("Сохранение результатов...", 'INFO')
                self.parser.save_results(phone_numbers)

                self.stats['total'] = len(phone_numbers)
                self.message_queue.put(('stats',))

                self.log_message(f"Парсинг завершен! Найдено {len(phone_numbers)} номеров", 'SUCCESS')
                self.update_status("Парсинг завершен", 'SUCCESS')

            except Exception as e:
                self.log_message(f"Ошибка парсинга: {str(e)}", 'ERROR')
                self.update_status("Ошибка парсинга", 'ERROR')
            finally:
                self.is_parsing = False
                if self.parser:
                    self.parser.close()

        threading.Thread(target=parse_thread, daemon=True).start()

    def stop_parsing(self):
        """Остановка парсера"""
        if not self.is_parsing:
            messagebox.showinfo("Информация", "Парсер не запущен!")
            return

        self.is_parsing = False
        if self.parser:
            self.parser.close()

        self.log_message("Парсер остановлен пользователем", 'WARNING')
        self.update_status("Парсер остановлен", 'WARNING')

    def create_folders(self):
        """Создание папок с номерами"""

        def create_thread():
            try:
                self.log_message("Создание папок с номерами...", 'INFO')
                self.update_status("Создание папок...", 'INFO')

                create_folders_and_copy_telegram()

                self.log_message("Папки созданы успешно!", 'SUCCESS')
                self.update_status("Папки созданы", 'SUCCESS')

            except Exception as e:
                self.log_message(f"Ошибка создания папок: {str(e)}", 'ERROR')
                self.update_status("Ошибка создания папок", 'ERROR')

        threading.Thread(target=create_thread, daemon=True).start()

    def open_base_folder(self):
        """Открытие базовой папки с номерами"""
        try:
            import subprocess
            import platform

            # Получаем путь из конфига
            folder_path = getattr(config, 'base_path', 'C:\\Users\\')

            # Проверяем существование папки
            if not os.path.exists(folder_path):
                messagebox.showerror("Ошибка", f"Папка не найдена:\n{folder_path}")
                self.log_message(f"Базовая папка не найдена: {folder_path}", 'ERROR')
                return

            # Открываем папку в зависимости от ОС
            system = platform.system().lower()
            if system == 'windows':
                os.startfile(folder_path)
            elif system == 'darwin':  # macOS
                subprocess.Popen(['open', folder_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder_path])

            self.log_message(f"Открыта базовая папка: {folder_path}", 'INFO')

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{str(e)}")
            self.log_message(f"Ошибка открытия базовой папки: {str(e)}", 'ERROR')

    def start_processing(self):
        """Запуск обработки номеров"""
        if self.is_processing:
            messagebox.showwarning("Предупреждение", "Обработка уже запущена!")
            return

        def process_thread():
            try:
                self.is_processing = True
                self.log_message("Запуск обработки номеров...", 'INFO')
                self.update_status("Обработка в процессе...", 'INFO')

                # Создание экземпляра AutoTelegramSender
                self.auto_sender = AutoTelegramSender()

                # Чтение номеров
                if not self.auto_sender.read_phone_numbers():
                    self.log_message("Не найдено номеров для обработки!", 'ERROR')
                    self.update_status("Нет номеров для обработки", 'WARNING')
                    return

                total_numbers = len(self.auto_sender.phone_numbers)
                self.stats['total'] = total_numbers

                self.log_message(f"Найдено {total_numbers} номеров для обработки", 'INFO')

                # Обработка каждого номера
                for i, phone_number in enumerate(self.auto_sender.phone_numbers, 1):
                    if not self.is_processing:  # Проверка на остановку
                        break

                    self.log_message(f"Обработка номера {i}/{total_numbers}: {phone_number}", 'INFO')
                    self.update_progress(i, total_numbers, f"Номер {i}/{total_numbers}")

                    try:
                        # Здесь вызываются методы из вашего класса БЕЗ ИЗМЕНЕНИЙ
                        success = self.auto_sender.process_single_number(phone_number)

                        if success:
                            self.stats['processed'] += 1
                            self.log_message(f"Номер {phone_number} успешно обработан", 'SUCCESS')
                        else:
                            self.stats['errors'] += 1
                            self.log_message(f"Ошибка обработки номера {phone_number}", 'ERROR')

                    except Exception as e:
                        self.stats['errors'] += 1
                        self.log_message(f"Исключение при обработке {phone_number}: {str(e)}", 'ERROR')

                    self.message_queue.put(('stats',))
                    time.sleep(1)  # Пауза между номерами

                self.log_message("Обработка номеров завершена!", 'SUCCESS')
                self.update_status("Обработка завершена", 'SUCCESS')

            except Exception as e:
                self.log_message(f"Критическая ошибка: {str(e)}", 'ERROR')
                self.update_status("Критическая ошибка", 'ERROR')
            finally:
                self.is_processing = False
                if self.auto_sender and self.auto_sender.driver:
                    self.auto_sender.driver.quit()

        threading.Thread(target=process_thread, daemon=True).start()

    def pause_processing(self):
        """Пауза обработки"""
        if not self.is_processing:
            messagebox.showinfo("Информация", "Обработка не запущена!")
            return

        # Здесь можно добавить логику паузы
        self.log_message("Обработка приостановлена", 'WARNING')
        self.update_status("Пауза", 'WARNING')

    def stop_processing(self):
        """Остановка обработки"""
        if not self.is_processing:
            messagebox.showinfo("Информация", "Обработка не запущена!")
            return

        self.is_processing = False
        self.log_message("Обработка остановлена пользователем", 'WARNING')
        self.update_status("Остановлено", 'WARNING')

    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'processed': 0,
            'banned': 0,
            'no_code': 0,
            'errors': 0,
            'total': 0
        }
        self.message_queue.put(('stats',))
        self.log_message("Статистика сброшена", 'INFO')

    def show_numbers(self):
        """Показ номеров в отдельном окне с возможностью редактирования"""
        numbers_window = tk.Toplevel(self.root)
        numbers_window.title("📋 Список номеров")
        numbers_window.geometry("900x700")
        numbers_window.configure(bg='#f5f5f5')

        # Заголовок
        header = tk.Frame(numbers_window, bg='#ffffff', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        title = tk.Label(header, text="📋 Список номеров телефонов (Редактирование)",
                         font=('Segoe UI', 16, 'bold'),
                         fg=self.colors['primary'],
                         bg='#ffffff')
        title.pack(pady=20)

        # Кнопки управления
        button_frame = tk.Frame(numbers_window, bg='#f5f5f5')
        button_frame.pack(fill='x', padx=20, pady=(0, 10))

        def save_numbers():
            """Сохранение отредактированных номеров"""
            try:
                content = text_area.get('1.0', 'end-1c')
                os.makedirs('data', exist_ok=True)
                with open(os.path.join('data', 'phone_numbers.txt'), 'w', encoding='utf-8') as f:
                    f.write(content)

                # Подсчитываем количество номеров
                import re
                phone_pattern = r'\+\d{10,15}'
                phone_numbers = re.findall(phone_pattern, content)
                total_count = len(phone_numbers)

                # Обновляем статистику
                self.stats['total'] = total_count
                self.message_queue.put(('stats',))

                messagebox.showinfo("Успех", f"Номера сохранены успешно!\nВсего номеров: {total_count}")
                self.log_message(f"Номера телефонов обновлены вручную. Всего: {total_count}", 'INFO')

                # Закрываем окно
                numbers_window.destroy()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")

        def clear_all():
            """Очистка всех номеров"""
            if messagebox.askyesno("Подтверждение", "Удалить все номера?"):
                text_area.delete('1.0', 'end')

                # Сохраняем пустой файл
                try:
                    os.makedirs('data', exist_ok=True)
                    with open(os.path.join('data', 'phone_numbers.txt'), 'w', encoding='utf-8') as f:
                        f.write('')
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")
                    return

                # Обновляем статистику до 0
                self.stats['total'] = 0
                self.message_queue.put(('stats',))
                self.log_message("Все номера телефонов удалены из файла", 'WARNING')

        save_btn = tk.Button(button_frame, text="💾 Сохранить",
                             command=save_numbers,
                             bg=self.colors['success'], fg='white',
                             font=('Segoe UI', 10, 'bold'),
                             relief='flat', padx=20, pady=5)
        save_btn.pack(side='left', padx=(0, 10))

        clear_btn = tk.Button(button_frame, text="🗑️ Очистить",
                              command=clear_all,
                              bg=self.colors['error'], fg='white',
                              font=('Segoe UI', 10, 'bold'),
                              relief='flat', padx=20, pady=5)
        clear_btn.pack(side='left')

        # Контент
        content_frame = tk.Frame(numbers_window, bg='#f5f5f5')
        content_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        try:
            with open(os.path.join('data', 'phone_numbers.txt'), 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = "# Файл с номерами не найден\n# Добавьте номера в формате:\n# +1234567890\n# +0987654321"

        text_area = scrolledtext.ScrolledText(content_frame,
                                              bg='#ffffff',
                                              fg=self.colors['text'],
                                              font=('Consolas', 10),
                                              relief='flat',
                                              bd=1,
                                              wrap='word')
        text_area.configure(highlightbackground=self.colors['border'],
                            highlightthickness=1)
        text_area.pack(fill='both', expand=True)
        text_area.insert('1.0', content)

        # Добавляем подсказку
        info_label = tk.Label(numbers_window,
                              text="💡 Редактируйте номера и нажмите 'Сохранить' для применения изменений",
                              font=('Segoe UI', 9),
                              fg=self.colors['text'],
                              bg='#f5f5f5')
        info_label.pack(pady=(0, 10))

    def export_results(self):
        """Экспорт результатов"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt")],
            title="Сохранить результаты"
        )

        if filename:
            try:
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'statistics': self.stats,
                    'config': {
                        'start_page': START_PAGE,
                        'end_page': END_PAGE,
                        'phone_prefix': PHONE_PREFIX
                    }
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                self.log_message(f"Результаты экспортированы в {filename}", 'SUCCESS')
                messagebox.showinfo("Успех", f"Результаты сохранены в {filename}")

            except Exception as e:
                self.log_message(f"Ошибка экспорта: {str(e)}", 'ERROR')
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")

    def open_settings(self):
        """Открытие окна настроек с возможностью редактирования"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ Настройки системы")
        settings_window.geometry("800x700")
        settings_window.configure(bg='#f5f5f5')
        settings_window.resizable(True, True)

        # Делаем окно модальным
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Заголовок
        header = tk.Frame(settings_window, bg='#ffffff', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        title = tk.Label(header, text="⚙️ Настройки системы",
                         font=('Segoe UI', 16, 'bold'),
                         fg=self.colors['primary'],
                         bg='#ffffff')
        title.pack(pady=20)

        # Основной контент с прокруткой
        main_frame = tk.Frame(settings_window, bg='#f5f5f5')
        main_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        # Canvas для прокрутки
        canvas = tk.Canvas(main_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f5f5f5')

        scrollable_frame.bind('<Configure>',
                              lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Привязка скролла мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)

        # Словарь для хранения переменных настроек
        self.settings_vars = {}

        # === ГРУППА: Авторизация ===
        self.create_settings_group(scrollable_frame, "🔐 Авторизация", [
            ("Email:", "EMAIL", "email", str(EMAIL) if 'EMAIL' in globals() else ""),
            ("Пароль:", "PASSWORD", "password", str(PASSWORD) if 'PASSWORD' in globals() else "")
        ])

        # === ГРУППА: Пути ===
        self.create_settings_group(scrollable_frame, "📁 Пути к файлам", [
            ("Базовая папка:", "base_path", "folder", str(base_path) if 'base_path' in globals() else ""),
            ("Путь к Telegram.exe:", "telegram_exe_path", "file",
             str(telegram_exe_path) if 'telegram_exe_path' in globals() else "")
        ])

        # === ГРУППА: Парсинг ===
        self.create_settings_group(scrollable_frame, "🔍 Настройки парсинга", [
            ("Начальная страница:", "START_PAGE", "number", str(START_PAGE) if 'START_PAGE' in globals() else "1"),
            ("Конечная страница:", "END_PAGE", "number", str(END_PAGE) if 'END_PAGE' in globals() else "1"),
            ("Префикс номера:", "PHONE_PREFIX", "text", str(PHONE_PREFIX) if 'PHONE_PREFIX' in globals() else "+55"),
            ("Мин. длина номера:", "MIN_PHONE_LENGTH", "number",
             str(MIN_PHONE_LENGTH) if 'MIN_PHONE_LENGTH' in globals() else "13"),
            ("Тайм-аут загрузки страницы (сек):", "PAGE_DELAY", "number",
             str(PAGE_DELAY) if 'PAGE_DELAY' in globals() else "1"),
            ("Ожидаемое кол-во номеров на странице:", "EXPECTED_NUMBERS_PER_PAGE", "number",
             str(getattr(config, 'EXPECTED_NUMBERS_PER_PAGE', 15) if 'config' in sys.modules else 15))
        ])

        # === ГРУППА: Интерфейс ===
        self.create_settings_group(scrollable_frame, "🖥️ Настройки интерфейса", [
            ("Фоновый режим браузера:", "HEADLESS_MODE", "checkbox",
             str(HEADLESS_MODE) if 'HEADLESS_MODE' in globals() else "False")
        ])

        # === НИЖНЯЯ ПАНЕЛЬ С КНОПКАМИ ===
        button_frame = tk.Frame(settings_window, bg='#ffffff', height=70)
        button_frame.pack(fill='x')
        button_frame.pack_propagate(False)

        # Тень сверху
        shadow = tk.Frame(settings_window, bg='#e1dfdd', height=1)
        shadow.pack(fill='x', before=button_frame)

        buttons_container = tk.Frame(button_frame, bg='#ffffff')
        buttons_container.pack(expand=True, pady=15)

        # Кнопки
        save_btn = tk.Button(buttons_container, text="💾 Сохранить",
                             command=lambda: self.save_settings(settings_window),
                             bg=self.colors['success'], fg='white',
                             font=('Segoe UI', 10, 'bold'),
                             relief='flat', cursor='hand2',
                             padx=20, pady=8)
        save_btn.pack(side='left', padx=(0, 10))

        reset_btn = tk.Button(buttons_container, text="🔄 Сброс",
                              command=self.reset_settings,
                              bg=self.colors['warning'], fg='white',
                              font=('Segoe UI', 10, 'bold'),
                              relief='flat', cursor='hand2',
                              padx=20, pady=8)
        reset_btn.pack(side='left', padx=5)

        cancel_btn = tk.Button(buttons_container, text="❌ Отмена",
                               command=settings_window.destroy,
                               bg=self.colors['surface'], fg=self.colors['text'],
                               font=('Segoe UI', 10, 'bold'),
                               relief='flat', cursor='hand2',
                               padx=20, pady=8)
        cancel_btn.pack(side='left', padx=(10, 0))

        # Центрируем окно
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (800 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (700 // 2)
        settings_window.geometry(f"800x700+{x}+{y}")

    def create_settings_group(self, parent, title, settings_list):
        """Создание группы настроек"""
        # Группа
        group_frame = tk.LabelFrame(parent, text=title,
                                    font=('Segoe UI', 11, 'bold'),
                                    fg=self.colors['primary'],
                                    bg='#f5f5f5')
        group_frame.pack(fill='x', pady=(0, 15), padx=10)

        # Контент группы
        content_frame = tk.Frame(group_frame, bg='#ffffff')
        content_frame.pack(fill='x', padx=15, pady=15)

        for i, (label_text, var_name, field_type, default_value) in enumerate(settings_list):
            # Строка настройки
            row_frame = tk.Frame(content_frame, bg='#ffffff')
            row_frame.pack(fill='x', pady=5)

            # Метка
            label = tk.Label(row_frame, text=label_text,
                             font=('Segoe UI', 9),
                             fg=self.colors['text'],
                             bg='#ffffff',
                             width=25, anchor='w')
            label.pack(side='left')

            # Поле ввода
            if field_type == "checkbox":
                var = tk.BooleanVar()
                var.set(default_value.lower() == 'true')
                widget = tk.Checkbutton(row_frame, variable=var,
                                        bg='#ffffff', fg=self.colors['text'])
                widget.pack(side='left')

            elif field_type == "folder":
                frame = tk.Frame(row_frame, bg='#ffffff')
                frame.pack(side='left', fill='x', expand=True)

                var = tk.StringVar()
                var.set(default_value)
                entry = tk.Entry(frame, textvariable=var,
                                 font=('Segoe UI', 9),
                                 relief='flat', bd=1)
                entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

                browse_btn = tk.Button(frame, text="📁",
                                       command=lambda v=var: self.browse_folder(v),
                                       bg=self.colors['surface'],
                                       relief='flat', cursor='hand2',
                                       font=('Segoe UI', 8))
                browse_btn.pack(side='right')

            elif field_type == "file":
                frame = tk.Frame(row_frame, bg='#ffffff')
                frame.pack(side='left', fill='x', expand=True)

                var = tk.StringVar()
                var.set(default_value)
                entry = tk.Entry(frame, textvariable=var,
                                 font=('Segoe UI', 9),
                                 relief='flat', bd=1)
                entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

                browse_btn = tk.Button(frame, text="📄",
                                       command=lambda v=var: self.browse_file(v),
                                       bg=self.colors['surface'],
                                       relief='flat', cursor='hand2',
                                       font=('Segoe UI', 8))
                browse_btn.pack(side='right')

            elif field_type == "password":
                var = tk.StringVar()
                var.set(default_value)
                widget = tk.Entry(row_frame, textvariable=var,
                                  show='*',
                                  font=('Segoe UI', 9),
                                  relief='flat', bd=1,
                                  width=40)
                widget.pack(side='left', fill='x', expand=True)

            else:  # text, email, number
                var = tk.StringVar()
                var.set(default_value)
                widget = tk.Entry(row_frame, textvariable=var,
                                  font=('Segoe UI', 9),
                                  relief='flat', bd=1,
                                  width=40)
                widget.pack(side='left', fill='x', expand=True)

            # Сохраняем переменную
            self.settings_vars[var_name] = var

    def browse_folder(self, var):
        """Выбор папки"""
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            var.set(folder)

    def browse_file(self, var):
        """Выбор файла"""
        file = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file:
            var.set(file)

    def save_settings(self, window):
        """Сохранение настроек с горячим применением"""
        try:
            # === 1. ПРИМЕНЯЕМ НАСТРОЙКИ СРАЗУ В ПАМЯТИ ===
            self.apply_settings_runtime()

            # === 2. СОХРАНЯЕМ В ФАЙЛ config.py ===
            config_content = f"""# Конфигурационный файл для парсера
# Автоматически сгенерирован панелью управления

# Данные для авторизации
EMAIL = "{self.settings_vars['EMAIL'].get()}"
PASSWORD = "{self.settings_vars['PASSWORD'].get()}"

# Путь к папке, где будут создаваться папки с номерами
base_path = r"{self.settings_vars['base_path'].get()}"

# Путь к файлу Telegram.exe
telegram_exe_path = r"{self.settings_vars['telegram_exe_path'].get()}"

# URL для парсинга
BASE_URL = "https://secondtg.org/orders"
START_PAGE = {self.settings_vars['START_PAGE'].get()}
END_PAGE = {self.settings_vars['END_PAGE'].get()}

# Настройки браузера
HEADLESS_MODE = {self.settings_vars['HEADLESS_MODE'].get()}

# Максимальное время ожидания загрузки страницы (в секундах)
# Примечание: Парсер автоматически переходит к следующей странице после завершения парсинга
PAGE_DELAY = {self.settings_vars['PAGE_DELAY'].get()}

# Фильтр для номеров телефонов
PHONE_PREFIX = "{self.settings_vars['PHONE_PREFIX'].get()}"
MIN_PHONE_LENGTH = {self.settings_vars['MIN_PHONE_LENGTH'].get()}

# Ожидаемое количество номеров на странице (для быстрого переключения)
EXPECTED_NUMBERS_PER_PAGE = {self.settings_vars['EXPECTED_NUMBERS_PER_PAGE'].get()}

# Файл для сохранения номеров телефонов
PHONE_NUMBERS_FILE = "phone_numbers.txt"
"""

            # Сохраняем в файл
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(config_content)

            self.log_message("Настройки сохранены и применены немедленно", 'SUCCESS')
            messagebox.showinfo("Успех", "Настройки сохранены и применены!")

            window.destroy()

        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек: {str(e)}", 'ERROR')
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")

    def apply_settings_runtime(self):
        """Применение настроек в текущей сессии без перезапуска"""
        import sys

        # Обновляем глобальные переменные в модуле config
        if 'config' in sys.modules:
            config_module = sys.modules['config']

            # Обновляем настройки авторизации
            config_module.EMAIL = self.settings_vars['EMAIL'].get()
            config_module.PASSWORD = self.settings_vars['PASSWORD'].get()

            # Обновляем пути
            config_module.base_path = self.settings_vars['base_path'].get()
            config_module.telegram_exe_path = self.settings_vars['telegram_exe_path'].get()

            # Обновляем настройки парсинга
            config_module.START_PAGE = int(self.settings_vars['START_PAGE'].get())
            config_module.END_PAGE = int(self.settings_vars['END_PAGE'].get())
            config_module.PHONE_PREFIX = self.settings_vars['PHONE_PREFIX'].get()
            config_module.MIN_PHONE_LENGTH = int(self.settings_vars['MIN_PHONE_LENGTH'].get())
            config_module.PAGE_DELAY = int(self.settings_vars['PAGE_DELAY'].get())
            config_module.EXPECTED_NUMBERS_PER_PAGE = int(self.settings_vars['EXPECTED_NUMBERS_PER_PAGE'].get())

            # Обновляем настройки интерфейса
            config_module.HEADLESS_MODE = self.settings_vars['HEADLESS_MODE'].get()

            self.log_message("🔥 Настройки применены в текущей сессии", 'SUCCESS')

        # Также обновляем глобальные переменные в основном модуле
        import __main__
        if hasattr(__main__, '__file__'):
            globals().update({
                'EMAIL': self.settings_vars['EMAIL'].get(),
                'PASSWORD': self.settings_vars['PASSWORD'].get(),
                'base_path': self.settings_vars['base_path'].get(),
                'telegram_exe_path': self.settings_vars['telegram_exe_path'].get(),
                'START_PAGE': int(self.settings_vars['START_PAGE'].get()),
                'END_PAGE': int(self.settings_vars['END_PAGE'].get()),
                'PHONE_PREFIX': self.settings_vars['PHONE_PREFIX'].get(),
                'MIN_PHONE_LENGTH': int(self.settings_vars['MIN_PHONE_LENGTH'].get()),
                'PAGE_DELAY': int(self.settings_vars['PAGE_DELAY'].get()),
                'EXPECTED_NUMBERS_PER_PAGE': int(self.settings_vars['EXPECTED_NUMBERS_PER_PAGE'].get()),
                'HEADLESS_MODE': self.settings_vars['HEADLESS_MODE'].get()
            })

        # Если есть активные экземпляры парсера или отправителя - обновляем их настройки
        if hasattr(self, 'parser') and self.parser:
            try:
                # Обновляем настройки парсера
                self.parser.start_page = int(self.settings_vars['START_PAGE'].get())
                self.parser.end_page = int(self.settings_vars['END_PAGE'].get())
                self.log_message("📡 Настройки парсера обновлены", 'INFO')
            except:
                pass

        if hasattr(self, 'auto_sender') and self.auto_sender:
            try:
                # Обновляем базовый путь для отправителя
                self.auto_sender.base_path = self.settings_vars['base_path'].get()
                self.log_message("📤 Настройки отправителя обновлены", 'INFO')
            except:
                pass

    def apply_settings_only(self):
        """Применение настроек без сохранения в файл"""
        try:
            self.apply_settings_runtime()
            self.log_message("🔥 Настройки применены в текущей сессии (не сохранены)", 'SUCCESS')
            messagebox.showinfo("Применено",
                                "⚡ Настройки применены в текущей сессии!\n💡 Для постоянного сохранения нажмите 'Сохранить'")
        except Exception as e:
            self.log_message(f"Ошибка применения настроек: {str(e)}", 'ERROR')
            messagebox.showerror("Ошибка", f"Не удалось применить настройки:\n{str(e)}")

    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        result = messagebox.askyesno("Подтверждение",
                                     "Сбросить все настройки к значениям по умолчанию?")
        if result:
            # Устанавливаем значения по умолчанию
            defaults = {
                'EMAIL': '',
                'PASSWORD': '',
                'base_path': '',
                'telegram_exe_path': '',
                'START_PAGE': '1',
                'END_PAGE': '1',
                'PHONE_PREFIX': '+55',
                'MIN_PHONE_LENGTH': '13',
                'PAGE_DELAY': '1',
                'EXPECTED_NUMBERS_PER_PAGE': '15',
                'HEADLESS_MODE': False
            }

            for key, default in defaults.items():
                if key in self.settings_vars:
                    if isinstance(self.settings_vars[key], tk.BooleanVar):
                        self.settings_vars[key].set(default)
                    else:
                        self.settings_vars[key].set(str(default))

            messagebox.showinfo("Готово", "Настройки сброшены к значениям по умолчанию")

    def clear_data(self):
        """Очистка данных"""
        result = messagebox.askyesno("Подтверждение",
                                     "Удалить все данные и сбросить статистику?")
        if result:
            try:
                # Очистка файлов
                files_to_clear = [
                    os.path.join('data', 'phone_numbers.txt'),
                ]

                for file_path in files_to_clear:
                    if os.path.exists(file_path):
                        os.remove(file_path)

                # Сброс статистики
                self.reset_stats()

                self.log_message("Все данные очищены", 'WARNING')
                self.update_status("Данные очищены", 'WARNING')

            except Exception as e:
                self.log_message(f"Ошибка очистки: {str(e)}", 'ERROR')

    def update_stats(self):
        """Обновление статистики из файлов"""
        try:
            # Подсчет статистики из файла номеров
            phone_file = os.path.join('data', 'phone_numbers.txt')
            if os.path.exists(phone_file):
                with open(phone_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                total = 0
                processed = 0
                banned = 0
                no_code = 0

                for line in lines:
                    if '+55' in line:
                        total += 1
                        if '+' in line and 'OTP код:' in line:
                            processed += 1
                        elif '- BAN' in line:
                            banned += 1
                        elif '- nocode' in line:
                            no_code += 1

                self.stats.update({
                    'total': total,
                    'processed': processed,
                    'banned': banned,
                    'no_code': no_code
                })

                self.message_queue.put(('stats',))

        except Exception as e:
            self.log_message(f"Ошибка обновления статистики: {str(e)}", 'WARNING')

    def run(self):
        """Запуск панели управления"""
        self.log_message("Панель управления запущена", 'SUCCESS')
        self.log_message("Система готова к работе", 'INFO')
        self.root.mainloop()


if __name__ == "__main__":
    # Проверка наличия необходимых файлов
    required_files = ['config.py', 'auto_telegram_sender.py', 'phone_parser.py', 'create_telegram_folders.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print("❌ Отсутствуют необходимые файлы:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nУбедитесь, что все файлы находятся в одной папке с панелью управления.")
        input("Нажмите Enter для выхода...")
    else:
        # Запуск панели управления
        app = TelegramControlPanel()
        app.run()
