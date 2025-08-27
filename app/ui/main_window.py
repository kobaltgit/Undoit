# -*- coding: utf-8 -*-
# GUI: Окно истории версий
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QFileDialog, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QWidget, QHBoxLayout,
                               QSplitter, QListWidget, QTextEdit, QVBoxLayout,
                               QLabel, QLineEdit)
from PySide6.QtGui import QIcon

from app.history_manager import HistoryManager


class HistoryWindow(QMainWindow):
    """
    Главное окно приложения для просмотра истории и восстановления файлов.
    """
    def __init__(self, history_manager: HistoryManager, app_icon: QIcon, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager

        self.setWindowTitle(self.tr("Backdraft - История версий")) # <-- Размечено для перевода
        self.setWindowIcon(app_icon)
        self.resize(1200, 700)

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
        self.search_input.setPlaceholderText(self.tr("Поиск файлов...")) # <-- Размечено для перевода
        self.search_input.setMinimumHeight(32)

        self.files_list = QListWidget()

        files_layout.addWidget(QLabel(self.tr("Отслеживаемые файлы:"))) # <-- Размечено для перевода
        files_layout.addWidget(self.search_input)
        files_layout.addWidget(self.files_list)

        # --- Панель 2: Список версий ---
        versions_panel = QWidget()
        versions_layout = QVBoxLayout(versions_panel)
        versions_layout.setContentsMargins(0, 0, 0, 0)
        versions_layout.setSpacing(8)

        self.versions_list = QListWidget()

        versions_layout.addWidget(QLabel(self.tr("Сохраненные версии:"))) # <-- Размечено для перевода
        versions_layout.addWidget(self.versions_list)

        # --- Панель 3: Превью и действия ---
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Создаем контейнер для кнопок
        buttons_layout = QHBoxLayout()
        self.save_as_button = QPushButton(self.tr("Сохранить как...")) # <-- Размечено для перевода
        self.restore_button = QPushButton(self.tr("Восстановить эту версию")) # <-- Размечено для перевода

        # Кнопки изначально неактивны
        self.save_as_button.setEnabled(False)
        self.restore_button.setEnabled(False)

        buttons_layout.addWidget(self.save_as_button)
        buttons_layout.addWidget(self.restore_button)

        preview_layout.addWidget(QLabel(self.tr("Предпросмотр:"))) # <-- Размечено для перевода
        preview_layout.addWidget(self.preview_text)
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

    @Slot()
    def refresh_file_list(self):
        """(СЛОТ) Загружает и отображает список отслеживаемых файлов."""
        # Сохраняем ID текущего выбранного файла, чтобы восстановить выбор
        current_id = None
        if self.files_list.currentItem():
            current_id = self.files_list.currentItem().data(Qt.ItemDataRole.UserRole)

        self.files_list.clear()
        tracked_files = self.history_manager.get_all_tracked_files()

        item_to_select = None
        for file_id, full_path in tracked_files:
            item = QListWidgetItem()
            item.setText(Path(full_path).name)
            item.setToolTip(full_path)
            item.setData(Qt.ItemDataRole.UserRole, file_id)
            self.files_list.addItem(item)
            if file_id == current_id:
                item_to_select = item

        # Если ранее был выбранный элемент, выбираем его снова
        if item_to_select:
            self.files_list.setCurrentItem(item_to_select)

    @Slot(int)
    def refresh_version_list_if_selected(self, updated_file_id: int):
        """(СЛОТ) Обновляет список версий, если измененный файл выбран в UI."""
        if not self.files_list.currentItem():
            return

        selected_file_id = self.files_list.currentItem().data(Qt.ItemDataRole.UserRole)
        if selected_file_id == updated_file_id:
            # Просто вызываем существующий обработчик, чтобы он перезагрузил версии
            self._on_file_selected(self.files_list.currentItem(), None)

    def _on_file_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Слот, вызываемый при выборе файла в левом списке."""
        self.versions_list.clear()
        self.preview_text.clear()

        if not current_item:
            return

        file_id = current_item.data(Qt.ItemDataRole.UserRole)
        versions = self.history_manager.get_versions_for_file(file_id)

        for timestamp_str, sha256_hash, file_size in versions:
            dt_object = datetime.fromisoformat(timestamp_str)
            formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")

            formatted_size = self._format_size(file_size)

            # <-- Форматированная строка для перевода
            item = QListWidgetItem(self.tr("{0} ({1})").format(formatted_time, formatted_size))
            item.setData(Qt.ItemDataRole.UserRole, sha256_hash)
            self.versions_list.addItem(item)

    def _on_version_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Слот, вызываемый при выборе версии в центральном списке."""
        self.preview_text.clear()

        is_version_selected = current_item is not None
        self.save_as_button.setEnabled(is_version_selected)
        self.restore_button.setEnabled(is_version_selected)

        if not is_version_selected:
            return

        sha256_hash = current_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)

        if not object_path:
            # <-- Сообщение для перевода
            self.preview_text.setText(self.tr("Ошибка: не удалось найти файл с хешем {0}...").format(sha256_hash[:8]))
            return

        try:
            with open(object_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.preview_text.setText(content)
        except (UnicodeDecodeError, IOError):
            self.preview_text.setText(self.tr("Предпросмотр недоступен для этого типа файла.")) # <-- Размечено для перевода

    def _on_save_as(self):
        """Слот для кнопки 'Сохранить как...'."""
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item:
            return

        original_path = Path(file_item.toolTip())
        sha256_hash = version_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)

        # <-- Форматированная строка для имени файла
        suggested_name = self.tr("{0} (восстановлено){1}").format(original_path.stem, original_path.suffix)

        save_path, _ = QFileDialog.getSaveFileName(self, 
            self.tr("Сохранить версию как..."), # <-- Размечено для перевода
            str(original_path.parent / suggested_name)
        )

        if save_path:
            try:
                shutil.copy2(object_path, save_path)
            except IOError as e:
                # <-- Сообщение для перевода
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось сохранить файл:\n{0}").format(e))

    def _on_restore(self):
        """Слот для кнопки 'Восстановить'."""
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item:
            return

        original_path_str = file_item.toolTip()
        original_path = Path(original_path_str)
        sha256_hash = version_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)

        reply = QMessageBox.question(self, 
            self.tr("Подтверждение"), # <-- Размечено для перевода
            self.tr( # <-- Сообщение для перевода
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

                # <-- Сообщение для перевода
                QMessageBox.information(self, self.tr("Успех"), self.tr("Файл успешно восстановлен."))
            except (IOError, OSError) as e:
                # <-- Сообщение для перевода
                QMessageBox.critical(self, self.tr("Ошибка"), self.tr("Не удалось восстановить файл:\n{0}").format(e))

    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла в удобочитаемый вид."""
        if size_bytes < 1024:
            return self.tr("{0} B").format(size_bytes) # <-- Размечено для перевода
        elif size_bytes < 1024 ** 2:
            return self.tr("{0:.1f} KB").format(size_bytes / 1024) # <-- Размечено для перевода
        elif size_bytes < 1024 ** 3:
            return self.tr("{0:.1f} MB").format(size_bytes / (1024 ** 2)) # <-- Размечено для перевода
        else:
            return self.tr("{0:.1f} GB").format(size_bytes / (1024 ** 3)) # <-- Размечено для перевода

    def _load_styles(self):
        """Загружает и применяет стили QSS."""
        self.setObjectName("HistoryWindow")
