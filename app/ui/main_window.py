# -*- coding: utf-8 -*-
# GUI: Окно истории версий
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot, QSize, QEvent # Добавлен QEvent для resizeEvent
from PySide6.QtWidgets import (QFileDialog, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QWidget, QHBoxLayout,
                               QSplitter, QListWidget, QTextEdit, QVBoxLayout,
                               QLabel, QLineEdit, QStackedWidget)
from PySide6.QtGui import QIcon, QPixmap, QResizeEvent # Добавлен QResizeEvent


from app.history_manager import HistoryManager


class HistoryWindow(QMainWindow):
    """
    Главное окно приложения для просмотра истории и восстановления файлов.
    """
    def __init__(self, history_manager: HistoryManager, app_icon: QIcon, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager

        self.setWindowTitle(self.tr("Undoit - История версий"))
        self.setWindowIcon(app_icon)
        self.resize(1200, 700)

        # Сохраняем полный список файлов для поиска
        self._all_tracked_files_data = [] # [(file_id, full_path), ...]
        self.current_object_path: Optional[Path] = None # Путь к файлу в хранилище для текущей выбранной версии
        self.current_original_file_path: Optional[Path] = None # Оригинальный путь к файлу для текущей выбранной версии
        self._current_original_pixmap: Optional[QPixmap] = None # Оригинальное изображение для предпросмотра (немасштабированное)

        self._init_ui()
        self._load_styles()
        self.refresh_file_list() # Первоначальная загрузка

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

        self.files_list = QListWidget()

        files_layout.addWidget(QLabel(self.tr("Отслеживаемые файлы:")))
        files_layout.addWidget(self.search_input)
        files_layout.addWidget(self.files_list)

        # --- Панель 2: Список версий ---
        versions_panel = QWidget()
        versions_layout = QVBoxLayout(versions_panel)
        versions_layout.setContentsMargins(0, 0, 0, 0)
        versions_layout.setSpacing(8)

        self.versions_list = QListWidget()

        versions_layout.addWidget(QLabel(self.tr("Сохраненные версии:")))
        versions_layout.addWidget(self.versions_list)

        # --- Панель 3: Превью и действия ---
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        # --- Заменяем QTextEdit на QStackedWidget для разных типов предпросмотра ---
        self.preview_stacked_widget = QStackedWidget()
        self.preview_stacked_widget.setObjectName("PreviewStackedWidget")

        self.text_preview_widget = QTextEdit()
        self.text_preview_widget.setReadOnly(True)
        self.text_preview_widget.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_preview_widget.setObjectName("TextPreviewWidget") # Для стилей

        self.image_preview_widget = QLabel()
        self.image_preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.image_preview_widget.setScaledContents(True) # Убрано, т.к. будем масштабировать вручную
        self.image_preview_widget.setObjectName("ImagePreviewWidget") # Для стилей

        self.info_preview_widget = QLabel() # Для PDF, неподдерживаемых файлов или ошибок
        self.info_preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_preview_widget.setWordWrap(True) # Перенос слов
        self.info_preview_widget.setObjectName("InfoPreviewWidget") # Для стилей

        self.preview_stacked_widget.addWidget(self.text_preview_widget) # Индекс 0
        self.preview_stacked_widget.addWidget(self.image_preview_widget) # Индекс 1
        self.preview_stacked_widget.addWidget(self.info_preview_widget) # Индекс 2

        # Создаем контейнер для кнопок
        buttons_layout = QHBoxLayout()
        self.save_as_button = QPushButton(self.tr("Сохранить как..."))
        self.restore_button = QPushButton(self.tr("Восстановить эту версию"))

        # Кнопки изначально неактивны
        self.save_as_button.setEnabled(False)
        self.restore_button.setEnabled(False)

        buttons_layout.addWidget(self.save_as_button)
        buttons_layout.addWidget(self.restore_button)

        preview_layout.addWidget(QLabel(self.tr("Предпросмотр:")))
        preview_layout.addWidget(self.preview_stacked_widget) # Добавляем стек вместо QTextEdit
        preview_layout.addLayout(buttons_layout)

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
        self.files_list.currentItemChanged.connect(self._on_file_selected)
        self.versions_list.currentItemChanged.connect(self._on_version_selected)
        self.save_as_button.clicked.connect(self._on_save_as)
        self.restore_button.clicked.connect(self._on_restore)
        self.search_input.textChanged.connect(self._on_search_text_changed)

    @Slot()
    def refresh_file_list(self):
        """(СЛОТ) Загружает и отображает список отслеживаемых файлов."""
        # Сохраняем ID текущего выбранного файла, чтобы восстановить выбор
        current_id = None
        if self.files_list.currentItem():
            current_id = self.files_list.currentItem().data(Qt.ItemDataRole.UserRole)

        # Очищаем _all_tracked_files_data и files_list
        self._all_tracked_files_data.clear()
        self.files_list.clear()

        # Загружаем все отслеживаемые файлы
        tracked_files = self.history_manager.get_all_tracked_files()
        self._all_tracked_files_data.extend(tracked_files)

        # Добавляем все элементы в список, но фильтруем их сразу, если есть текст поиска
        search_text = self.search_input.text().strip()
        item_to_select = None

        for file_id, full_path in self._all_tracked_files_data:
            item = QListWidgetItem()
            item.setText(Path(full_path).name)
            item.setToolTip(full_path)
            item.setData(Qt.ItemDataRole.UserRole, file_id)
            self.files_list.addItem(item)

            # Применяем фильтр поиска сразу
            if search_text and search_text.lower() not in Path(full_path).name.lower():
                item.setHidden(True)

            if file_id == current_id:
                item_to_select = item

        # Если ранее был выбранный элемент, выбираем его снова
        if item_to_select and not item_to_select.isHidden():
            self.files_list.setCurrentItem(item_to_select)
        elif item_to_select and item_to_select.isHidden():
            # Если выбранный элемент скрыт, сбрасываем выбор и очищаем версии/превью
            self.files_list.setCurrentItem(None)
            self.versions_list.clear()
            # Очищаем все виджеты предпросмотра и деактивируем кнопки
            self.text_preview_widget.clear()
            self.image_preview_widget.clear()
            self.info_preview_widget.clear()
            self.save_as_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            self.current_object_path = None
            self.current_original_file_path = None
            self._current_original_pixmap = None # Сброс оригинального Pixmap


    @Slot(str)
    def _on_search_text_changed(self, text: str):
        """
        Слот, вызываемый при изменении текста в поле поиска.
        Фильтрует отображаемые файлы в списке.
        """
        search_lower = text.strip().lower()

        # Сохраняем ID текущего выбранного файла, если он есть
        current_id = None
        if self.files_list.currentItem():
            current_id = self.files_list.currentItem().data(Qt.ItemDataRole.UserRole)

        found_item_to_select = None

        # Перебираем все элементы в QListWidget и показываем/скрываем их
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            file_name = item.text().lower()
            if search_lower in file_name:
                item.setHidden(False)
                if item.data(Qt.ItemDataRole.UserRole) == current_id:
                    found_item_to_select = item
            else:
                item.setHidden(True)

        # Восстанавливаем выбор, если выбранный элемент остался видимым
        if found_item_to_select and not found_item_to_select.isHidden():
            self.files_list.setCurrentItem(found_item_to_select)
        elif current_id is not None:
            # Если выбранный элемент стал невидимым или его не было,
            # сбрасываем выбор и очищаем панели версий/превью.
            self.files_list.setCurrentItem(None)
            self.versions_list.clear()
            # Очищаем все виджеты предпросмотра
            self.text_preview_widget.clear()
            self.image_preview_widget.clear()
            self.info_preview_widget.clear()
            self.save_as_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            self.current_object_path = None
            self.current_original_file_path = None
            self._current_original_pixmap = None # Сброс оригинального Pixmap

    @Slot(int)
    def refresh_version_list_if_selected(self, updated_file_id: int):
        """(СЛОТ) Обновляет список версий, если измененный файл выбран в UI."""
        if not self.files_list.currentItem():
            return

        selected_file_id = self.files_list.currentItem().data(Qt.ItemDataRole.UserRole)
        if selected_file_id == updated_file_id:
            # Просто вызываем существующий обработчик, чтобы он перезагрузил версии
            # Это имитирует выбор файла заново
            self._on_file_selected(self.files_list.currentItem(), None)

    def _on_file_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Слот, вызываемый при выборе файла в левом списке."""
        self.versions_list.clear()
        self.text_preview_widget.clear()
        self.image_preview_widget.clear()
        self.info_preview_widget.clear()
        self.current_object_path = None # Сбрасываем путь к объекту
        self.current_original_file_path = None # Сбрасываем оригинальный путь
        self._current_original_pixmap = None # Сброс оригинального Pixmap

        if not current_item:
            self.save_as_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            self.preview_stacked_widget.setCurrentIndex(0) # Показываем текстовый предпросмотр по умолчанию (пустой)
            return

        file_id = current_item.data(Qt.ItemDataRole.UserRole)
        versions = self.history_manager.get_versions_for_file(file_id)

        for timestamp_str, sha256_hash, file_size in versions:
            dt_object = datetime.fromisoformat(timestamp_str)
            formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")

            formatted_size = self._format_size(file_size)

            item = QListWidgetItem(self.tr("{0} ({1})").format(formatted_time, formatted_size))
            item.setData(Qt.ItemDataRole.UserRole, sha256_hash)
            self.versions_list.addItem(item)

        # После загрузки версий, кнопки остаются отключенными, пока не выбрана конкретная версия
        self.save_as_button.setEnabled(False)
        self.restore_button.setEnabled(False)


    def _on_version_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Слот, вызываемый при выборе версии в центральном списке."""
        # Сбрасываем все предпросмотры и текущий путь к объекту
        self.text_preview_widget.clear()
        self.image_preview_widget.clear()
        self.info_preview_widget.clear()
        self.current_object_path = None
        self.current_original_file_path = None
        self._current_original_pixmap = None # Сброс оригинального Pixmap

        is_version_selected = current_item is not None
        self.save_as_button.setEnabled(is_version_selected)
        self.restore_button.setEnabled(is_version_selected)

        if not is_version_selected:
            self.preview_stacked_widget.setCurrentIndex(0) # Показываем текстовый предпросмотр по умолчанию (пустой)
            return

        sha256_hash = current_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)
        self.current_object_path = object_path # Сохраняем путь для кнопок "Сохранить как" / "Восстановить"

        file_item = self.files_list.currentItem()
        if not file_item:
            self._show_preview_message(self.tr("Ошибка: не выбран оригинальный файл."))
            return

        original_path_str = file_item.toolTip()
        self.current_original_file_path = Path(original_path_str)
        original_file_extension = self.current_original_file_path.suffix


        if not object_path:
            self._show_preview_message(
                self.tr("Ошибка: не удалось найти файл с хешем {0}...").format(sha256_hash[:8])
            )
            return

        content_type, content_data = self.history_manager.get_file_content_for_preview(
            object_path, original_file_extension
        )

        if content_type == "text":
            self.text_preview_widget.setText(content_data)
            self.preview_stacked_widget.setCurrentIndex(0) # Показываем QTextEdit
        elif content_type == "image":
            # Загружаем оригинальный QPixmap
            pixmap = QPixmap(str(object_path))
            if not pixmap.isNull():
                self._current_original_pixmap = pixmap # Сохраняем оригинал
                self._display_current_image() # Отображаем масштабированную версию
                self.preview_stacked_widget.setCurrentIndex(1) # Показываем QLabel для изображений
            else:
                self._show_preview_message(
                    self.tr("Не удалось загрузить изображение. Возможно, файл поврежден или не является корректным изображением.")
                )
        elif content_type == "pdf_page_count":
            self._show_preview_message(
                self.tr("PDF-файл, {0} страниц. Полный предпросмотр не поддерживается, но вы можете сохранить или восстановить файл.").format(content_data)
            )
        elif content_type == "unsupported":
            self._show_preview_message(
                self.tr("Предпросмотр недоступен для этого типа файла.")
            )
        elif content_type == "error":
            self._show_preview_message(
                self.tr("Ошибка при предпросмотре: {0}").format(content_data)
            )
        else: # Fallback на текстовый, если что-то пошло не так
            self.text_preview_widget.setText(self.tr("Неизвестный тип контента для предпросмотра."))
            self.preview_stacked_widget.setCurrentIndex(0)

    def _display_current_image(self):
        """Отображает текущее изображение в image_preview_widget, масштабируя его пропорционально."""
        if self._current_original_pixmap and not self._current_original_pixmap.isNull():
            # Получаем доступный размер для отображения изображения
            available_size = self.image_preview_widget.size()

            # Масштабируем QPixmap с сохранением пропорций
            scaled_pixmap = self._current_original_pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation # Для лучшего качества при масштабировании
            )
            self.image_preview_widget.setPixmap(scaled_pixmap)
        else:
            self.image_preview_widget.clear() # Если нет изображения, очищаем QLabel

    def _show_preview_message(self, message: str):
        """Вспомогательный метод для отображения сообщений в информационном виджете."""
        self.info_preview_widget.setText(message)
        self.preview_stacked_widget.setCurrentIndex(2) # Показываем QLabel для информации/ошибок

    def resizeEvent(self, event: QResizeEvent):
        """Обрабатывает изменение размера окна."""
        super().resizeEvent(event)
        # Если текущий виджет в стеке - это виджет изображения и есть что отображать,
        # то перемасштабируем изображение.
        if self.preview_stacked_widget.currentIndex() == 1 and self._current_original_pixmap:
            self._display_current_image()

    def _on_save_as(self):
        """Слот для кнопки 'Сохранить как...'."""
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item or not self.current_object_path:
            return

        if not self.current_original_file_path:
            QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось определить оригинальный путь файла."))
            return

        original_path = self.current_original_file_path
        object_path = self.current_object_path

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
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item or not self.current_object_path:
            return

        if not self.current_original_file_path:
            QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось определить оригинальный путь файла."))
            return

        original_path_str = str(self.current_original_file_path)
        original_path = self.current_original_file_path
        object_path = self.current_object_path

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
                self.history_manager.add_file_version(original_path_str)

                shutil.copy2(object_path, original_path)

                self._on_file_selected(file_item, None)

                QMessageBox.information(self, self.tr("Успех"), self.tr("Файл успешно восстановлен."))
            except (IOError, OSError) as e:
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось восстановить файл:\n{0}").format(e))

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
