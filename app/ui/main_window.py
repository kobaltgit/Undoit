# -*- coding: utf-8 -*-
# GUI: Окно истории версий
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Set, Tuple, Dict
from PySide6.QtWidgets import QSizePolicy

from PySide6.QtCore import Qt, Slot, QSize, QEvent, QPoint
from PySide6.QtWidgets import (QFileDialog, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QWidget, QHBoxLayout,
                               QSplitter, QListWidget, QTextEdit, QVBoxLayout,
                               QLabel, QLineEdit, QStackedWidget, QMenu,
                               QSystemTrayIcon, QTreeWidget, QTreeWidgetItem, 
                               QTreeWidgetItemIterator, QStyle, QApplication) # Добавлен импорт QTreeWidgetItemIterator
from PySide6.QtGui import QIcon, QPixmap, QResizeEvent, QAction


from app.history_manager import HistoryManager
from app.config_manager import ConfigManager # Добавлен импорт ConfigManager
# Константы для предпросмотра изображений
MAX_PREVIEW_IMAGE_WIDTH = 800  # Максимальная ширина изображения в предпросмотре
MAX_PREVIEW_IMAGE_HEIGHT = 600 # Максимальная высота изображения в предпросмотре



class HistoryWindow(QMainWindow):
    """
    Главное окно приложения для просмотра истории и восстановления файлов.
    """
    def __init__(self, history_manager: HistoryManager, config_manager: ConfigManager, app_icon: QIcon, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.config_manager = config_manager # Сохраняем ссылку на ConfigManager

        self.setWindowTitle(self.tr("Undoit - История версий"))
        self.setWindowIcon(app_icon)
        self.resize(1200, 700)

        # Сохраняем полный список файлов для поиска
        # Теперь это словарь, где ключи - file_id, значения - (QTreeWidgetItem, full_path)
        self._all_tracked_files_data: Dict[int, Tuple[QTreeWidgetItem, str]] = {} 
        self._current_selected_file_id: Optional[int] = None # ID текущего выбранного файла в списке файлов
        self._current_selected_version_data: Optional[Tuple[int, str, str, int]] = None # (version_id, timestamp_str, sha256_hash, file_size)

        self.current_object_path: Optional[Path] = None # Путь к файлу в хранилище для текущей выбранной версии
        self.current_original_file_path: Optional[Path] = None # Оригинальный путь к файлу для текущей выбранной версии
        self._current_original_pixmap: Optional[QPixmap] = None # Оригинальное изображение для предпросмотра (немасштабированное)

        # Иконки для папок и файлов в QTreeWidget
        self._folder_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._file_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        self._init_ui()
        self._load_styles()
        self.refresh_file_list() # Первоначальная загрузка

        # Подключение новых сигналов от HistoryManager
        self.history_manager.version_added.connect(self.refresh_version_list_if_selected) # Обновление версий
        self.history_manager.version_deleted.connect(self.refresh_version_list_if_selected) # Удаление версий
        self.history_manager.files_deleted.connect(self.refresh_file_list_after_deletion) # Удаление файлов

    def _init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # --- Панель 1: Список файлов ---
        files_panel = QWidget()
        files_layout = QVBoxLayout(files_panel)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Поиск файлов..."))
        self.search_input.setMinimumHeight(32)

        # !!! ИЗМЕНЕНИЕ: QListWidget заменен на QTreeWidget
        self.files_list = QTreeWidget()
        self.files_list.setHeaderLabels([self.tr("Файл / Папка")]) # Устанавливаем заголовок
        self.files_list.setIndentation(20) # Добавляем отступ для дочерних элементов
        self.files_list.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection) # Разрешаем множественный выбор
        self.files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu) # Включаем кастомное контекстное меню
        self.files_list.customContextMenuRequested.connect(self._open_file_context_menu)


        files_buttons_layout = QHBoxLayout()
        self.delete_selected_files_button = QPushButton(self.tr("Удалить выбранные"))
        self.delete_selected_files_button.setEnabled(False) # Изначально неактивна
        files_buttons_layout.addWidget(self.delete_selected_files_button)

        files_layout.addWidget(QLabel(self.tr("Отслеживаемые файлы:")))
        files_layout.addWidget(self.search_input)
        files_layout.addWidget(self.files_list)
        files_layout.addLayout(files_buttons_layout)


        # --- Панель 2: Список версий ---
        versions_panel = QWidget()
        versions_layout = QVBoxLayout(versions_panel)
        versions_layout.setContentsMargins(0, 0, 0, 0)
        versions_layout.setSpacing(8)

        self.versions_list = QListWidget()
        self.versions_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection) # Разрешаем множественный выбор
        self.versions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu) # Включаем кастомное контекстное меню
        self.versions_list.customContextMenuRequested.connect(self._open_version_context_menu)


        versions_buttons_layout = QHBoxLayout() # Новый Layout для кнопок версий
        self.delete_single_version_button = QPushButton(self.tr("Удалить версию")) # Переименовано
        self.delete_single_version_button.setEnabled(False) # Изначально неактивна

        self.delete_selected_versions_button = QPushButton(self.tr("Удалить выбранные версии")) # Новая кнопка
        self.delete_selected_versions_button.setEnabled(False) # Изначально неактивна

        versions_buttons_layout.addWidget(self.delete_single_version_button)
        versions_buttons_layout.addWidget(self.delete_selected_versions_button)


        versions_layout.addWidget(QLabel(self.tr("Сохраненные версии:")))
        versions_layout.addWidget(self.versions_list)
        versions_layout.addLayout(versions_buttons_layout) # Добавляем новый Layout с кнопками

        # --- Панель 3: Превью и действия ---
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        # --- Заменяем QTextEdit на QStackedWidget для разных типов предпросмотра ---
        self.preview_stacked_widget = QStackedWidget()
        self.preview_stacked_widget.setObjectName("PreviewStackedWidget")
        self.preview_stacked_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding # <--- ДОБАВЛЕНО
        )

        self.text_preview_widget = QTextEdit()
        self.text_preview_widget.setReadOnly(True)
        self.text_preview_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_preview_widget.setObjectName("TextPreviewWidget") # Для стилей

        self.image_preview_widget = QLabel()
        self.image_preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_widget.setScaledContents(False) # <--- ВЕРНУЛИ НА FALSE: теперь мы масштабируем вручную
        self.image_preview_widget.setObjectName("ImagePreviewWidget") # Для стилей
        self.image_preview_widget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed # <--- НОВАЯ ПОЛИТИКА: QLabel будет подстраиваться под Pixmap, а не расширяться
        )
        # Убрали setMinimumSize(1,1), так как QLabel будет подстраиваться под размер установленного Pixmap.


        self.info_preview_widget = QLabel() # Для PDF, неподдерживаемых файлов или ошибок
        self.info_preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_preview_widget.setWordWrap(True) # Перенос слов
        self.info_preview_widget.setObjectName("InfoPreviewWidget") # Для стилей
        self.info_preview_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding # <--- ДОБАВЛЕНО
        )

        self.preview_stacked_widget.addWidget(self.text_preview_widget) # Индекс 0

        # --- Центрирующий контейнер для виджета предпросмотра изображения ---
        image_centering_widget = QWidget() # <--- НОВЫЙ КОНТЕЙНЕР
        image_centering_layout = QVBoxLayout(image_centering_widget) # <--- НОВЫЙ МАКЕТ
        image_centering_layout.setContentsMargins(0, 0, 0, 0) # Убираем лишние отступы внутри контейнера

        image_centering_layout.addStretch(1) # Растяжка сверху для вертикального центрирования
        # Добавляем QLabel. AlignCenter здесь центрирует его по горизонтали внутри макета.
        # Поскольку QLabel имеет фиксированный размер, он не будет растягиваться.
        image_centering_layout.addWidget(self.image_preview_widget, 0, Qt.AlignmentFlag.AlignCenter) 
        image_centering_layout.addStretch(1) # Растяжка снизу для вертикального центрирования

        self.preview_stacked_widget.addWidget(image_centering_widget) # <--- ДОБАВЛЯЕМ КОНТЕЙНЕР В STACKED WIDGET
        self.preview_stacked_widget.addWidget(self.info_preview_widget) # Индекс 2

        # Создаем контейнер для кнопок
        preview_buttons_layout = QHBoxLayout() # Переименовано в preview_buttons_layout
        self.save_as_button = QPushButton(self.tr("Сохранить как..."))
        self.restore_button = QPushButton(self.tr("Восстановить эту версию"))

        # Кнопки изначально неактивны
        self.save_as_button.setEnabled(False)
        self.restore_button.setEnabled(False)

        preview_buttons_layout.addWidget(self.save_as_button)
        preview_buttons_layout.addWidget(self.restore_button)


        preview_layout.addWidget(QLabel(self.tr("Предпросмотр:")))
        preview_layout.addWidget(self.preview_stacked_widget) # Добавляем стек вместо QTextEdit
        preview_layout.addLayout(preview_buttons_layout) # Используем preview_buttons_layout


        # --- Сборка панелей с помощью QSplitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.addWidget(files_panel)
        splitter.addWidget(versions_panel)
        splitter.addWidget(preview_panel)

        splitter.setSizes([250, 250, 700])

        main_layout.addWidget(splitter)

        self.setCentralWidget(main_container)

        # --- СОЕДИНЯЕМ СИГНАЛЫ И СЛОТЫ ---
        # !!! ИЗМЕНЕНИЕ: Соединение для QTreeWidget
        self.files_list.currentItemChanged.connect(self._on_file_selected)
        self.files_list.itemSelectionChanged.connect(self._update_file_buttons_state) # Для активации/деактивации кнопки удаления файлов

        self.versions_list.currentItemChanged.connect(self._on_version_selected)
        self.versions_list.itemSelectionChanged.connect(self._update_version_buttons_state) # НОВОЕ СОЕДИНЕНИЕ

        self.save_as_button.clicked.connect(self._on_save_as)
        self.restore_button.clicked.connect(self._on_restore)
        self.delete_single_version_button.clicked.connect(self._on_delete_single_version) # Соединяем новую кнопку
        self.delete_selected_versions_button.clicked.connect(self._on_delete_selected_versions) # НОВОЕ СОЕДИНЕНИЕ

        self.delete_selected_files_button.clicked.connect(self._on_delete_selected_files) # Соединяем новую кнопку пакетного удаления
        self.search_input.textChanged.connect(self._on_search_text_changed)

    def _get_item_type(self, item: QTreeWidgetItem) -> str:
        """Вспомогательный метод для определения, является ли элемент файла или папкой."""
        # Мы храним тип 'file' или 'folder' в UserRole для корневых элементов.
        # Для дочерних элементов (файлов) их тип всегда 'file'.
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and 'type' in data:
            return data['type']
        # Если это дочерний элемент (файл), у него будет просто file_id и full_path
        if isinstance(data, tuple) and len(data) == 2:
            return 'file'
        return 'unknown'

    # НОВЫЙ ВСПОМОГАТЕЛЬНЫЙ МЕТОД
    def _is_any_actual_file_selected_in_tree(self) -> bool:
        """
        Проверяет, выбран ли в QTreeWidget хотя бы один элемент,
        который является файлом (а не папкой).
        """
        for item in self.files_list.selectedItems():
            if self._get_item_type(item) == 'file':
                return True
        return False

    @Slot(list)
    def refresh_file_list_after_deletion(self, deleted_files_info: List[Tuple[int, str]]): # <--- ИЗМЕНЕНО
        """
        (СЛОТ) Обновляет список файлов после удаления одного или нескольких файлов.
        """
        if not deleted_files_info: # <--- ДОБАВЛЕНО
            return # <--- ДОБАВЛЕНО

        # Извлекаем только file_ids из новой структуры (file_id, original_path_str)
        deleted_file_ids = {info[0] for info in deleted_files_info} # <--- НОВОЕ

        # Сначала собираем все элементы QTreeWidget, которые нужно удалить
        items_to_remove: List[QTreeWidgetItem] = []

        # Проходим по всем корневым элементам
        iterator = QTreeWidgetItemIterator(self.files_list)
        while iterator.value():
            item = iterator.value()
            if self._get_item_type(item) == 'file':
                file_id, _ = item.data(0, Qt.ItemDataRole.UserRole)
                if file_id in deleted_file_ids:
                    items_to_remove.append(item)
            iterator += 1

        for item in items_to_remove:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
                # Если папка стала пустой после удаления, можно ее скрыть или удалить
                if parent.childCount() == 0:
                    parent.setHidden(True) # Скрываем пустую папку
            else:
                # Если это был одиночный файл на верхнем уровне
                self.files_list.takeTopLevelItem(self.files_list.indexOfTopLevelItem(item))

        # Сбрасываем текущий выбранный файл, если он был удален
        if self._current_selected_file_id in deleted_file_ids:
            self.files_list.setCurrentItem(None)
            self._current_selected_file_id = None
            self.versions_list.clear()
            self._reset_preview_panel()
            self._update_all_buttons_state() # Обновляем состояние всех кнопок

        # Обновляем _all_tracked_files_data
        for file_id in deleted_file_ids:
            self._all_tracked_files_data.pop(file_id, None)

    @Slot()
    def refresh_file_list(self):
        """(СЛОТ) Загружает и отображает список отслеживаемых файлов, группируя по папкам."""
        # Сохраняем ID текущего выбранного файла, чтобы восстановить выбор
        current_id = self._current_selected_file_id

        self.files_list.clear()
        self._all_tracked_files_data.clear()

        # Получаем отслеживаемые элементы из ConfigManager
        watched_items = self.config_manager.get_watched_items()

        # Получаем все отслеживаемые файлы из HistoryManager
        all_tracked_files_raw = self.history_manager.get_all_tracked_files() # [(file_id, original_path)]

        # Создаем словарь для быстрого поиска файлов по их полному пути
        tracked_files_by_path = {Path(p).resolve(): (f_id, p) for f_id, p in all_tracked_files_raw}

        # Словарь для хранения QTreeWidgetItem для папок
        folder_tree_items: Dict[Path, QTreeWidgetItem] = {}

        # Специальная "папка" для индивидуальных файлов
        individual_files_item = QTreeWidgetItem([self.tr("Другие файлы")])
        individual_files_item.setIcon(0, self._folder_icon)
        individual_files_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'folder', 'path': '__individual_files__'}) # Используем фиктивный путь

        has_individual_files = False

        # 1. Создаем элементы для отслеживаемых папок и добавляем их на верхний уровень
        for item_data in watched_items:
            path_str = item_data.get("path")
            item_type = item_data.get("type")

            if not path_str or not Path(path_str).exists():
                continue # Игнорируем несуществующие пути

            path_obj = Path(path_str).resolve()

            if item_type == 'folder':
                folder_item = QTreeWidgetItem([path_obj.name])
                folder_item.setIcon(0, self._folder_icon)
                folder_item.setToolTip(0, str(path_obj))
                # Сохраняем исходные данные элемента, включая исключения
                folder_item.setData(0, Qt.ItemDataRole.UserRole, item_data) 
                self.files_list.addTopLevelItem(folder_item)
                folder_tree_items[path_obj] = folder_item

        # 2. Распределяем отслеживаемые файлы по папкам или в "Другие файлы"
        # Необходимо пройти по всем tracked_files_by_path, а не по all_tracked_files_raw напрямую,
        # так как tracked_files_by_path содержит разрешенные пути.

        # Сначала создадим список кортежей (resolved_path, (file_id, original_path))
        # для более удобной итерации
        all_resolved_tracked_files = [(resolved_path, data) for resolved_path, data in tracked_files_by_path.items()]

        for resolved_file_path, (file_id, original_path_str) in all_resolved_tracked_files:
            file_added_to_folder = False

            # Проверяем, принадлежит ли файл какой-либо отслеживаемой папке (с учетом исключений)
            for folder_path_obj, folder_item in folder_tree_items.items():
                if resolved_file_path.is_relative_to(folder_path_obj):
                    # Проверяем исключения для этой папки
                    folder_item_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
                    exclusions = folder_item_data.get("exclusions", [])
                    is_excluded = any(resolved_file_path.is_relative_to(Path(ex).resolve()) for ex in exclusions)

                    if not is_excluded:
                        file_child_item = QTreeWidgetItem([resolved_file_path.name])
                        file_child_item.setIcon(0, self._file_icon)
                        file_child_item.setToolTip(0, original_path_str)
                        # Сохраняем file_id и оригинальный_путь в UserRole для файлов
                        file_child_item.setData(0, Qt.ItemDataRole.UserRole, (file_id, original_path_str))
                        folder_item.addChild(file_child_item)
                        self._all_tracked_files_data[file_id] = (file_child_item, original_path_str)
                        file_added_to_folder = True
                        break # Файл найден в папке, дальше не ищем

            # Если файл не добавлен ни в одну из отслеживаемых папок, добавляем его в "Другие файлы"
            if not file_added_to_folder:
                file_child_item = QTreeWidgetItem([resolved_file_path.name])
                file_child_item.setIcon(0, self._file_icon)
                file_child_item.setToolTip(0, original_path_str)
                file_child_item.setData(0, Qt.ItemDataRole.UserRole, (file_id, original_path_str))
                individual_files_item.addChild(file_child_item)
                self._all_tracked_files_data[file_id] = (file_child_item, original_path_str)
                has_individual_files = True

        # Если есть индивидуальные файлы, добавляем их контейнер на верхний уровень
        if has_individual_files:
            self.files_list.addTopLevelItem(individual_files_item)

        # Сортируем корневые элементы (папки и "Другие файлы")
        self.files_list.sortItems(0, Qt.SortOrder.AscendingOrder)

        # Применяем фильтр поиска сразу (если есть)
        search_text = self.search_input.text().strip()
        if search_text:
            self._apply_search_filter(search_text)

        # Восстанавливаем выбор, если ранее был выбранный элемент
        item_to_select = None
        if current_id in self._all_tracked_files_data:
            item_to_select, _ = self._all_tracked_files_data[current_id]
            if item_to_select and not item_to_select.isHidden():
                # Разворачиваем родительские элементы, чтобы выбранный файл был виден
                parent = item_to_select.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.files_list.setCurrentItem(item_to_select)

        if not item_to_select or item_to_select.isHidden():
            self.files_list.setCurrentItem(None)
            self._current_selected_file_id = None
            self.versions_list.clear()
            self._reset_preview_panel()
            self._update_all_buttons_state()


    @Slot(int)
    def refresh_version_list_if_selected(self, file_id: int):
        """
        (СЛОТ) Обновляет список версий, если 'file_id' соответствует текущему выбранному файлу.
        """
        # Если выбранный файл совпадает с тем, для которого добавлена/удалена версия,
        # то перезагружаем список версий для этого файла.
        if self._current_selected_file_id == file_id:
            # Получаем текущий выбранный элемент файла из QTreeWidget
            # И вызываем _on_file_selected, чтобы обновить список версий
            current_file_tree_item = self.files_list.currentItem()
            if current_file_tree_item:
                # _on_file_selected ожидает (current_item, previous_item)
                # Передаем None для previous_item, т.к. мы не меняем выбор, а обновляем его.
                self._on_file_selected(current_file_tree_item, None)


    @Slot(str)
    def _on_search_text_changed(self, text: str):
        """
        Слот, вызываемый при изменении текста в поле поиска.
        Фильтрует отображаемые файлы в QTreeWidget.
        """
        self._apply_search_filter(text.strip())

    def _apply_search_filter(self, search_text: str):
        """Применяет фильтр поиска к QTreeWidget."""
        search_lower = search_text.lower()

        current_id_before_search = self._current_selected_file_id
        item_to_select = None

        # Проходим по всем элементам дерева (включая дочерние)
        iterator = QTreeWidgetItemIterator(self.files_list)
        while iterator.value():
            item = iterator.value()
            item.setHidden(True) # Скрываем по умолчанию все элементы

            item_text = item.text(0).lower()
            item_type = self._get_item_type(item)

            # Если элемент является файлом или папкой (корневой), проверяем соответствие поисковому запросу
            if search_lower in item_text:
                item.setHidden(False)
                # Если это файл, и он был выбран до поиска, запоминаем его для восстановления выбора
                if item_type == 'file':
                    file_id, _ = item.data(0, Qt.ItemDataRole.UserRole)
                    if file_id == current_id_before_search:
                        item_to_select = item
                # Если это корневой элемент (папка), разворачиваем его
                if item.parent() is None:
                    item.setExpanded(True)


            # Если это дочерний элемент (файл), и он соответствует поиску, то показать его и его родителя
            if item.parent() and item_type == 'file' and search_lower in item_text:
                item.setHidden(False)
                item.parent().setHidden(False) # Показываем родительскую папку
                item.parent().setExpanded(True) # Разворачиваем родительскую папку

                file_id, _ = item.data(0, Qt.ItemDataRole.UserRole)
                if file_id == current_id_before_search:
                    item_to_select = item

            iterator += 1

        # Восстанавливаем выбор, если выбранный элемент остался видимым
        if item_to_select and not item_to_select.isHidden():
            self.files_list.setCurrentItem(item_to_select)
        else:
            self.files_list.setCurrentItem(None)
            self._current_selected_file_id = None
            self.versions_list.clear()
            self._reset_preview_panel()
            self._update_all_buttons_state() # Обновляем состояние всех кнопок

    # !!! ИЗМЕНЕНИЕ: Тип аргументов на QTreeWidgetItem
    @Slot(QTreeWidgetItem, QTreeWidgetItem)
    def _on_file_selected(self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem):
        """Слот, вызываемый при выборе файла в левом списке."""
        self.versions_list.clear()
        self._reset_preview_panel()

        self._current_selected_file_id = None
        self._current_selected_version_data = None

        if not current_item:
            self._update_all_buttons_state()
            return

        # Если выбранный элемент - это папка, не загружаем версии
        if self._get_item_type(current_item) == 'folder':
            self._update_all_buttons_state()
            return

        # Если выбранный элемент - это файл
        file_id, full_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        self._current_selected_file_id = file_id # Обновляем ID выбранного файла
        self.current_original_file_path = Path(full_path) # Обновляем оригинальный путь к файлу

        versions = self.history_manager.get_versions_for_file(file_id)

        for version_id, timestamp_str, sha256_hash, file_size in versions:
            dt_object = datetime.fromisoformat(timestamp_str)
            formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")

            formatted_size = self._format_size(file_size)

            item = QListWidgetItem(self.tr("{0} ({1})").format(formatted_time, formatted_size))
            # Сохраняем все данные о версии в ItemDataRole
            item.setData(Qt.ItemDataRole.UserRole, (version_id, timestamp_str, sha256_hash, file_size))
            self.versions_list.addItem(item)

        # После загрузки версий, сбрасываем выделение в списке версий и обновляем состояние кнопок
        self.versions_list.clearSelection() # <--- Важное изменение: сбрасываем выделение
        self._update_all_buttons_state()


    def _on_version_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """
        Слот, вызываемый при изменении текущего элемента в списке версий.
        Отвечает за отображение предпросмотра, если выбран ТОЛЬКО ОДИН элемент.
        """
        self._reset_preview_panel() # Всегда сбрасываем при новом выборе/изменении текущего элемента
        self._current_selected_version_data = None # Сброс данных о выбранной версии

        if not current_item:
            # Если текущий элемент недействителен (например, сняли выделение или выбрали несколько),
            # просто сбрасываем предпросмотр и выходим.
            # _update_version_buttons_state займется более сложной логикой.
            self._update_all_buttons_state()
            return

        # Пытаемся отобразить предпросмотр для current_item.
        # Если выбранных элементов на самом деле > 1, это будет исправлено
        # в _update_version_buttons_state, который очистит предпросмотр и выдаст уведомление.
        version_data = current_item.data(Qt.ItemDataRole.UserRole)
        self._current_selected_version_data = version_data
        sha256_hash = version_data[2]

        object_path = self.history_manager.get_object_path(sha256_hash)
        self.current_object_path = object_path

        # self.files_list.currentItem() теперь возвращает QTreeWidgetItem.
        file_tree_item = self.files_list.currentItem()
        if not file_tree_item or self._get_item_type(file_tree_item) == 'folder':
            self._show_preview_message(self.tr("Ошибка: не выбран оригинальный файл."))
            self._update_all_buttons_state()
            return

        # Данные файла из UserRole для QTreeWidgetItem
        _, original_path_str = file_tree_item.data(0, Qt.ItemDataRole.UserRole)
        self.current_original_file_path = Path(original_path_str)
        original_file_extension = self.current_original_file_path.suffix

        if not object_path:
            self._show_preview_message(
                self.tr("Ошибка: не удалось найти файл с хешем {0}...").format(sha256_hash[:8])
            )
            self._update_all_buttons_state()
            return

        content_type, content_data = self.history_manager.get_file_content_for_preview(
            object_path, original_file_extension
        )

        if content_type == "text":
            self.text_preview_widget.setText(content_data)
            self.preview_stacked_widget.setCurrentIndex(0)
        elif content_type == "image":
            pixmap = QPixmap(str(object_path))
            if not pixmap.isNull():
                self._current_original_pixmap = pixmap
                self._display_current_image()
                self.preview_stacked_widget.setCurrentIndex(1)
            else:
                self._show_preview_message(
                    self.tr("Не удалось загрузить изображение. Возможно, файл поврежден или не является корректным изображением.")
                )
        elif content_type == "unsupported":
            self._show_preview_message(
                self.tr("Предпросмотр недоступен для этого типа файла.")
            )
        elif content_type == "error":
            self._show_preview_message(
                self.tr("Ошибка при предпросмотре: {0}").format(content_data)
            )
        else:
            self.text_preview_widget.setText(self.tr("Неизвестный тип контента для предпросмотра."))
            self.preview_stacked_widget.setCurrentIndex(0)

        self._update_all_buttons_state()


    def _reset_preview_panel(self):
        """Сбрасывает состояние панели предпросмотра и связанные данные."""
        self.text_preview_widget.clear()
        self.image_preview_widget.clear()
        self.info_preview_widget.clear()
        self.current_object_path = None
        self.current_original_file_path = None
        self._current_original_pixmap = None
        self.preview_stacked_widget.setCurrentIndex(0) # Показываем текстовый предпросмотр по умолчанию (пустой)

    def _display_current_image(self):
        """
        Отображает текущее изображение в image_preview_widget,
        масштабируя его пропорционально до заданных максимальных размеров.
        """
        if self._current_original_pixmap and not self._current_original_pixmap.isNull():
            # Определяем максимальный размер для масштабирования
            max_display_size = QSize(MAX_PREVIEW_IMAGE_WIDTH, MAX_PREVIEW_IMAGE_HEIGHT) # <--- ИСПОЛЬЗУЕМ КОНСТАНТЫ

            # Масштабируем QPixmap с сохранением пропорций, не превышая max_display_size.
            # Если оригинальный размер меньше max_display_size, scaled() не увеличит его.
            scaled_pixmap = self._current_original_pixmap.scaled(
                max_display_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation # Для лучшего качества при масштабировании
            )
            self.image_preview_widget.setPixmap(scaled_pixmap)
            # После установки pixmap, обновляем фиксированный размер QLabel, чтобы он точно соответствовал
            # масштабированному изображению. Это предотвращает растягивание родительского макета.
            self.image_preview_widget.setFixedSize(scaled_pixmap.size()) # <--- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ
        else:
            self.image_preview_widget.clear() # Если нет изображения, очищаем QLabel
            self.image_preview_widget.setFixedSize(0, 0) # <--- Сброс размера, если нет изображения

    def _show_preview_message(self, message: str):
        """Отображает информационное или ошибочное сообщение в панели предпросмотра."""
        self.text_preview_widget.clear()
        self.image_preview_widget.clear()
        self._current_original_pixmap = None # Сброс, чтобы не пытаться масштабировать
        self.info_preview_widget.setText(self.tr("<i>{0}</i>").format(message))
        self.preview_stacked_widget.setCurrentIndex(2) # Индекс для info_preview_widget

    # def resizeEvent(self, event: QResizeEvent):
    #     """Обрабатывает изменение размера окна."""
    #     super().resizeEvent(event)
        # При использовании setScaledContents(True) QLabel сам обрабатывает масштабирование
        # при изменении размера. Больше не требуется вызывать _display_current_image() здесь.
        # Это предотвращает рекурсивные вызовы.

    def _on_save_as(self):
        """Слот для кнопки 'Сохранить как...'."""
        if not self._current_selected_version_data or not self._current_selected_file_id: # Обновлена проверка
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Для сохранения версии необходимо выбрать одну версию файла."))
            return

        # Эти проверки уже должны быть гарантированы _update_all_buttons_state
        # Но для надежности и прямого вызова через контекстное меню, лучше оставить.
        if len(self.versions_list.selectedItems()) != 1:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Для сохранения версии выберите ОДНУ версию файла."))
            return

        original_path = self.current_original_file_path
        object_path = self.current_object_path

        if not original_path or not object_path:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Не удалось определить пути к файлу."))
            return

        suggested_name = self.tr("{0} (восстановлено){1}").format(original_path.stem, original_path.suffix)

        save_path, _ = QFileDialog.getSaveFileName(self, 
            self.tr("Сохранить версию как..."),
            str(original_path.parent / suggested_name)
        )

        if save_path:
            try:
                shutil.copy2(object_path, save_path)
                QMessageBox.information(self, self.tr("Успех"), self.tr("Файл успешно сохранен."))
            except IOError as e:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось сохранить файл:\n{0}").format(e))

    def _on_restore(self):
        """Слот для кнопки 'Восстановить'."""
        if not self._current_selected_version_data or not self._current_selected_file_id: # Обновлена проверка
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Для восстановления версии необходимо выбрать одну версию файла."))
            return

        # Эти проверки уже должны быть гарантированы _update_all_buttons_state
        if len(self.versions_list.selectedItems()) != 1:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Для восстановления версии выберите ОДНУ версию файла."))
            return

        original_path_str = str(self.current_original_file_path)
        original_path = self.current_original_file_path
        object_path = self.current_object_path

        if not original_path or not object_path:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Не удалось определить пути к файлу."))
            return

        reply = QMessageBox.question(self, 
            self.tr("Подтверждение"),
            self.tr(
                "Вы уверены, что хотите восстановить файл:\n\n{0}\n\n"
                "Текущая версия файла будет перезаписана (но предварительно сохранена в истории)."
            ).format(original_path_str),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Сначала сохраняем текущую версию файла, прежде чем ее перезаписать
                self.history_manager.add_file_version(original_path_str)

                shutil.copy2(object_path, original_path)

                QMessageBox.information(self, self.tr("Успех"), self.tr("Файл успешно восстановлен."))
            except (IOError, OSError) as e:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось восстановить файл:\n{0}").format(e))

    @Slot()
    def _on_delete_single_version(self): # Переименовано
        """Слот для кнопки 'Удалить версию' и действия контекстного меню (одиночное удаление)."""
        if len(self.versions_list.selectedItems()) != 1:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Выберите ОДНУ версию для удаления."))
            return

        if not self._current_selected_version_data or not self._current_selected_file_id:
            return

        version_id, _, sha256_hash, _ = self._current_selected_version_data

        # Получаем имя текущего файла из QTreeWidget
        file_tree_item = self.files_list.currentItem()
        if not file_tree_item or self._get_item_type(file_tree_item) == 'folder':
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Не удалось определить родительский файл."))
            return

        current_file_name = file_tree_item.text(0)

        reply = QMessageBox.question(self,
            self.tr("Подтверждение удаления версии"),
            self.tr(
                "Вы уверены, что хотите безвозвратно удалить выбранную версию файла '{0}'?\n\n"
                "Это действие нельзя отменить."
            ).format(current_file_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.history_manager.delete_file_version(
                version_id=version_id,
                file_id=self._current_selected_file_id,
                sha256_hash=sha256_hash
            )
            if success:
                QMessageBox.information(self, self.tr("Успех"), self.tr("Версия успешно удалена."))
            else:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось удалить версию."))


    @Slot()
    def _on_delete_selected_versions(self): # НОВЫЙ СЛОТ
        """Слот для кнопки 'Удалить выбранные версии' и действия контекстного меню (пакетное удаление)."""
        selected_versions_items = self.versions_list.selectedItems()
        if not selected_versions_items:
            return

        if self._current_selected_file_id is None:
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Не удалось определить родительский файл для выбранных версий."))
            return

        versions_data_to_delete: List[Tuple[int, int, str]] = []
        for item in selected_versions_items:
            v_id, _, sha_hash, _ = item.data(Qt.ItemDataRole.UserRole)
            versions_data_to_delete.append((v_id, self._current_selected_file_id, sha_hash))

        # Получаем имя текущего файла из QTreeWidget
        file_tree_item = self.files_list.currentItem()
        if not file_tree_item or self._get_item_type(file_tree_item) == 'folder':
            QMessageBox.warning(self, self.tr("Ошибка"), self.tr("Не удалось определить родительский файл."))
            return

        file_name = file_tree_item.text(0)

        if len(versions_data_to_delete) == 1:
            confirmation_message = self.tr(
                "Вы уверены, что хотите безвозвратно удалить выбранную версию файла '{0}'?\n\n"
                "Это действие нельзя отменить."
            ).format(file_name)
            dialog_title = self.tr("Подтверждение удаления версии")
        else:
            confirmation_message = self.tr(
                "Вы уверены, что хотите безвозвратно удалить {0} выбранных версий файла '{1}'?\n\n"
                "Это действие нельзя отменить."
            ).format(len(versions_data_to_delete), file_name)
            dialog_title = self.tr("Подтверждение удаления версий")


        reply = QMessageBox.question(self,
            dialog_title,
            confirmation_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count, files_completely_removed = self.history_manager.delete_multiple_versions(versions_data_to_delete)
            if deleted_count > 0:
                QMessageBox.information(self, self.tr("Успех"), self.tr("Удалено {0} версий.").format(deleted_count))
            else:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось удалить версии."))


    @Slot()
    def _on_delete_selected_files(self):
        """Слот для кнопки 'Удалить выбранные' файлы и действия контекстного меню."""
        selected_items = self.files_list.selectedItems()
        if not selected_items:
            return

        file_ids_to_delete = set()
        file_names_to_delete = set()

        for item in selected_items:
            if self._get_item_type(item) == 'file': # Удаляем только файлы, не папки
                file_id, _ = item.data(0, Qt.ItemDataRole.UserRole)
                file_ids_to_delete.add(file_id)
                file_names_to_delete.add(item.text(0))
            # Если выбрана папка, мы не удаляем её через этот метод.
            # Пользователь должен удалить отслеживаемую папку в настройках.

        if not file_ids_to_delete:
            QMessageBox.warning(self, self.tr("Действие невозможно"), self.tr("Выберите хотя бы один файл для удаления. Папки не могут быть удалены из истории напрямую."))
            return


        if len(file_ids_to_delete) == 1:
            confirmation_message = self.tr(
                "Вы уверены, что хотите безвозвратно удалить файл '{0}' и все его версии?\n\n"
                "Это действие нельзя отменить."
            ).format(list(file_names_to_delete)[0])
            dialog_title = self.tr("Подтверждение удаления файла")
        else:
            confirmation_message = self.tr(
                "Вы уверены, что хотите безвозвратно удалить {0} выбранных файлов и все их версии?\n\n"
                "Это действие нельзя отменить."
            ).format(len(file_ids_to_delete))
            dialog_title = self.tr("Подтверждение удаления файлов")

        reply = QMessageBox.question(self,
            dialog_title,
            confirmation_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count, _ = self.history_manager.delete_tracked_files(file_ids_to_delete)
            if deleted_count > 0:
                QMessageBox.information(self, self.tr("Успех"), self.tr("Удалено {0} файлов.").format(deleted_count))
            else:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось удалить файлы."))


    def _update_file_buttons_state(self):
        """Обновляет состояние кнопки 'Удалить выбранные' для файлов."""
        is_any_actual_file_selected = self._is_any_actual_file_selected_in_tree()
        self.delete_selected_files_button.setEnabled(is_any_actual_file_selected)

        # Если выделение в списке файлов изменилось (особенно если стало 0),
        # нужно сбросить выделение в списке версий и состояние кнопок предпросмотра.
        if not is_any_actual_file_selected:
            self.versions_list.clearSelection() # Сброс выделения в версиях
            self._current_selected_file_id = None
            self._current_selected_version_data = None
            self._reset_preview_panel()
            self.versions_list.clear() # Очистить список версий
        # В любом случае (независимо от того, выбраны ли файлы или нет),
        # необходимо обновить состояние всех кнопок.
        self._update_all_buttons_state()


    @Slot()
    def _update_version_buttons_state(self): # НОВЫЙ СЛОТ
        """Обновляет состояние кнопок для версий и кнопок предпросмотра.
           Также управляет уведомлением о невозможности предпросмотра при множественном выборе."""
        self._update_all_buttons_state()

        num_selected_versions = len(self.versions_list.selectedItems())

        if num_selected_versions > 1:
            # Если выбрано несколько версий, сбрасываем предпросмотр и данные
            self._current_selected_version_data = None
            self._reset_preview_panel()
            self.history_manager.history_notification.emit(self.tr("Предпросмотр недоступен при множественном выборе версий."), QSystemTrayIcon.Information)
        elif num_selected_versions == 0:
            # Если ничего не выбрано, также сбрасываем предпросмотр и данные
            self._current_selected_version_data = None
            self._reset_preview_panel()
        # Если num_selected_versions == 1, предпросмотр уже был установлен _on_version_selected,
        # и здесь ничего дополнительно делать не нужно.


    def _update_all_buttons_state(self):
        """Обновляет состояние всех кнопок в окне."""
        is_single_file_item_selected = False
        selected_file_items = self.files_list.selectedItems()
        if len(selected_file_items) == 1 and self._get_item_type(selected_file_items[0]) == 'file':
            is_single_file_item_selected = True

        num_selected_versions = len(self.versions_list.selectedItems())
        is_single_version_selected = num_selected_versions == 1

        # Кнопка пакетного удаления файлов
        self.delete_selected_files_button.setEnabled(self._is_any_actual_file_selected_in_tree())

        # Кнопки для работы с ОДНОЙ выбранной версией (Сохранить как, Восстановить, Удалить версию)
        # Они активны, только если выбран ОДИН файл И ОДНА версия
        self.save_as_button.setEnabled(is_single_file_item_selected and is_single_version_selected)
        self.restore_button.setEnabled(is_single_file_item_selected and is_single_version_selected)
        self.delete_single_version_button.setEnabled(is_single_file_item_selected and is_single_version_selected)

        # Кнопка для работы с НЕСКОЛЬКИМИ (или одной) выбранными версиями (Удалить выбранные версии)
        # Она активна, если выбран ОДИН файл И хотя бы ОДНА версия
        self.delete_selected_versions_button.setEnabled(is_single_file_item_selected and num_selected_versions > 0)


    def _open_file_context_menu(self, position: QPoint):
        """Открывает контекстное меню для списка файлов."""
        context_menu = QMenu(self)

        selected_items = self.files_list.selectedItems()
        num_selected_files = 0
        is_single_file_selected_in_tree = False

        # Определяем, сколько файлов (не папок) выбрано
        for item in selected_items:
            if self._get_item_type(item) == 'file':
                num_selected_files += 1

        if num_selected_files == 1:
            is_single_file_selected_in_tree = True

        # Действия для одной версии
        save_as_action = QAction(self.tr("Сохранить как..."), self)
        save_as_action.triggered.connect(self._on_save_as)

        restore_action = QAction(self.tr("Восстановить эту версию"), self)
        restore_action.triggered.connect(self._on_restore)

        # Действие для удаления файлов
        delete_files_action = QAction(self.tr("Удалить выбранный(е) файл(ы)"), self)
        delete_files_action.triggered.connect(self._on_delete_selected_files)

        # Логика активации для Save As / Restore
        # Активны, только если выбран ОДИН файл (не папка) в QTreeWidget
        # И выбрана ОДНА версия в QListWidget для этого файла.
        is_single_version_selected = len(self.versions_list.selectedItems()) == 1

        save_as_action.setEnabled(is_single_file_selected_in_tree and is_single_version_selected)
        restore_action.setEnabled(is_single_file_selected_in_tree and is_single_version_selected)

        # Действие для удаления файлов активно, если выбран хотя бы один файл (не папка)
        delete_files_action.setEnabled(num_selected_files > 0)


        context_menu.addAction(save_as_action)
        context_menu.addAction(restore_action)
        context_menu.addSeparator()
        context_menu.addAction(delete_files_action)

        context_menu.exec(self.files_list.mapToGlobal(position))

    def _open_version_context_menu(self, position: QPoint):
        """Открывает контекстное меню для списка версий."""
        context_menu = QMenu(self)

        # Действия для одной версии
        save_as_action = QAction(self.tr("Сохранить как..."), self)
        save_as_action.triggered.connect(self._on_save_as)

        restore_action = QAction(self.tr("Восстановить эту версию"), self)
        restore_action.triggered.connect(self._on_restore)

        delete_single_version_action = QAction(self.tr("Удалить версию"), self)
        delete_single_version_action.triggered.connect(self._on_delete_single_version)

        # Действие для множества версий
        delete_multiple_versions_action = QAction(self.tr("Удалить выбранные версии"), self)
        delete_multiple_versions_action.triggered.connect(self._on_delete_selected_versions)

        # Проверяем, выбран ли один файл в дереве (родительский элемент для версий)
        selected_file_items = self.files_list.selectedItems()
        is_single_file_selected_in_tree = len(selected_file_items) == 1 and self._get_item_type(selected_file_items[0]) == 'file'


        num_selected_versions = len(self.versions_list.selectedItems())

        if num_selected_versions == 1 and is_single_file_selected_in_tree:
            save_as_action.setEnabled(True)
            restore_action.setEnabled(True)
            delete_single_version_action.setEnabled(True)
            delete_multiple_versions_action.setEnabled(False) # Отключаем, если выбрана только одна

            context_menu.addAction(save_as_action)
            context_menu.addAction(restore_action)
            context_menu.addSeparator()
            context_menu.addAction(delete_single_version_action)

        elif num_selected_versions > 1 and is_single_file_selected_in_tree:
            save_as_action.setEnabled(False) # Невозможно для нескольких версий
            restore_action.setEnabled(False) # Невозможно для нескольких версий
            delete_single_version_action.setEnabled(False) # Отключаем, если выбрано несколько
            delete_multiple_versions_action.setEnabled(True)

            context_menu.addAction(delete_multiple_versions_action)
        else:
            # Ничего не выбрано, или выбрано некорректно (не один файл в дереве)
            save_as_action.setEnabled(False)
            restore_action.setEnabled(False)
            delete_single_version_action.setEnabled(False)
            delete_multiple_versions_action.setEnabled(False)

        context_menu.exec(self.versions_list.mapToGlobal(position))


    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла в удобочитаемый вид."""
        if size_bytes < 1024:
            return self.tr("{0} B").format(size_bytes)
        elif size_bytes < 1024 ** 2:
            return self.tr("{0:.1f} KB").format(size_bytes / 1024)
        elif size_bytes < 1024 ** 3:
            return self.tr("{0:.1f} MB").format(size_bytes / (1024 ** 2))
        else:
            return self.tr("{0:.1f} GB").format(size_bytes / (1024 ** 3))

    def _load_styles(self):
        """Загружает и применяет стили QSS."""
        self.setObjectName("HistoryWindow")
