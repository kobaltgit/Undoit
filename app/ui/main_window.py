# -*- coding: utf-8 -*-
# GUI: Окно истории версий
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QListWidgetItem, QMainWindow,
                               QMessageBox, QPushButton, QWidget, QHBoxLayout,
                               QSplitter, QListWidget, QTextEdit, QVBoxLayout,
                               QLabel, QLineEdit)

from app.history_manager import HistoryManager


class HistoryWindow(QMainWindow):
    """
    Главное окно приложения для просмотра истории и восстановления файлов.
    """
    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager

        self.setWindowTitle("Backdraft - История версий")
        self.resize(1200, 700)
        
        self._init_ui()
        self._load_styles()
        self._load_initial_data()

    def _init_ui(self):
        # ... (код создания панелей остается почти без изменений) ...
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        files_panel = QWidget()
        files_layout = QVBoxLayout(files_panel)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск файлов...")
        self.search_input.setMinimumHeight(32)
        self.files_list = QListWidget()
        files_layout.addWidget(QLabel("Отслеживаемые файлы:"))
        files_layout.addWidget(self.search_input)
        files_layout.addWidget(self.files_list)
        versions_panel = QWidget()
        versions_layout = QVBoxLayout(versions_panel)
        versions_layout.setContentsMargins(0, 0, 0, 0)
        versions_layout.setSpacing(8)
        self.versions_list = QListWidget()
        versions_layout.addWidget(QLabel("Сохраненные версии:"))
        versions_layout.addWidget(self.versions_list)
        
        # --- Панель 3: Добавляем кнопки ---
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Создаем контейнер для кнопок
        buttons_layout = QHBoxLayout()
        self.save_as_button = QPushButton("Сохранить как...")
        self.restore_button = QPushButton("Восстановить эту версию")
        
        # Кнопки изначально неактивны
        self.save_as_button.setEnabled(False)
        self.restore_button.setEnabled(False)

        buttons_layout.addWidget(self.save_as_button)
        buttons_layout.addWidget(self.restore_button)
        
        preview_layout.addWidget(QLabel("Предпросмотр:"))
        preview_layout.addWidget(self.preview_text)
        preview_layout.addLayout(buttons_layout) # Добавляем кнопки внизу

        # --- Сборка панелей ---
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

    # ... методы _load_initial_data, _on_file_selected, _format_size, _load_styles ...
    # ... остаются без изменений ...
    def _load_initial_data(self):
        self.files_list.clear()
        tracked_files = self.history_manager.get_all_tracked_files()
        for file_id, full_path in tracked_files:
            item = QListWidgetItem(); item.setText(Path(full_path).name)
            item.setToolTip(full_path); item.setData(Qt.ItemDataRole.UserRole, file_id)
            self.files_list.addItem(item)
    
    def _on_file_selected(self, current_item, previous_item):
        self.versions_list.clear()
        self.preview_text.clear()
        if not current_item: return
        file_id = current_item.data(Qt.ItemDataRole.UserRole)
        versions = self.history_manager.get_versions_for_file(file_id)
        for ts, h, size in versions:
            dt = datetime.fromisoformat(ts); ft = dt.strftime("%Y-%m-%d %H:%M:%S")
            fs = self._format_size(size); item = QListWidgetItem(f"{ft} ({fs})")
            item.setData(Qt.ItemDataRole.UserRole, h); self.versions_list.addItem(item)
    
    def _on_version_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        self.preview_text.clear()
        # Активируем или деактивируем кнопки
        is_version_selected = current_item is not None
        self.save_as_button.setEnabled(is_version_selected)
        self.restore_button.setEnabled(is_version_selected)
        
        if not is_version_selected: return
        sha256_hash = current_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)
        if not object_path:
            self.preview_text.setText(f"Ошибка: не удалось найти файл с хешем {sha256_hash[:8]}...")
            return
        try:
            with open(object_path, 'r', encoding='utf-8') as f:
                self.preview_text.setText(f.read())
        except (UnicodeDecodeError, IOError):
            self.preview_text.setText("Предпросмотр недоступен для этого типа файла.")

    def _on_save_as(self):
        """Слот для кнопки 'Сохранить как...'."""
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item: return

        original_path = Path(file_item.toolTip())
        sha256_hash = version_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)
        
        # Предлагаем имя файла по умолчанию
        suggested_name = f"{original_path.stem} (восстановлено){original_path.suffix}"
        
        # Открываем системный диалог сохранения файла
        save_path, _ = QFileDialog.getSaveFileName(self, "Сохранить версию как...", str(original_path.parent / suggested_name))
        
        if save_path:
            try:
                shutil.copy2(object_path, save_path)
            except IOError as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def _on_restore(self):
        """Слот для кнопки 'Восстановить'."""
        file_item = self.files_list.currentItem()
        version_item = self.versions_list.currentItem()
        if not file_item or not version_item: return

        original_path_str = file_item.toolTip()
        original_path = Path(original_path_str)
        sha256_hash = version_item.data(Qt.ItemDataRole.UserRole)
        object_path = self.history_manager.get_object_path(sha256_hash)

        # Диалог подтверждения
        reply = QMessageBox.question(self, "Подтверждение", 
            f"Вы уверены, что хотите восстановить файл:\n\n{original_path_str}\n\n"
            f"Текущая версия файла будет перезаписана (но предварительно сохранена в истории).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Наша "сеть безопасности": сохраняем текущую версию ПЕРЕД перезаписью
                self.history_manager.add_file_version(original_path_str)
                
                # Выполняем восстановление
                shutil.copy2(object_path, original_path)
                
                # Обновляем список версий, чтобы показать только что сохраненную
                self._on_file_selected(file_item, None)
                
                QMessageBox.information(self, "Успех", "Файл успешно восстановлен.")
            except (IOError, OSError) as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить файл:\n{e}")
                
    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2: return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3: return f"{size_bytes / (1024 ** 2):.1f} MB"
        else: return f"{size_bytes / (1024 ** 3):.1f} GB"
        
    def _load_styles(self):
        self.setObjectName("HistoryWindow")