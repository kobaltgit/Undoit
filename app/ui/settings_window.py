# -*- coding: utf-8 -*-
# GUI: Окно настроек
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import (QEasingCurve, QPoint, QPointF, QPropertyAnimation,
                            Qt, Signal, Slot, Property)
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QIcon
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget, QStyle)

from app.config_manager import ConfigManager


class Switch(QWidget):
    """Кастомный виджет-переключатель (toggle switch)."""
    toggled = Signal(bool)
    _circle_position_val: float = 0.0

    def _get_circle_position(self) -> float:
        return self._circle_position_val

    def _set_circle_position(self, pos: float):
        self._circle_position_val = pos
        self.update()

    circle_position = Property(float, _get_circle_position, _set_circle_position)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._circle_offset = 3
        self._circle_diameter = 22
        self._track_height = 28
        self._track_radius = 14
        self._circle_position_val = float(self._circle_offset)
        self._bg_color_off = QColor("#808080")
        self._bg_color_on = QColor("#0078D4")
        self._current_bg_color = self._bg_color_off
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.animation.setDuration(200)
        self.setChecked(self._checked, animate=False)

    def setChecked(self, checked: bool, animate: bool = True):
        if self._checked == checked:
            return
        self._checked = checked
        target_position = float((self.width() - self._circle_offset - self._circle_diameter) if self._checked else self._circle_offset)
        if animate:
            self.animation.setStartValue(self.circle_position)
            self.animation.setEndValue(target_position)
            self.animation.start()
        else:
            self.circle_position = target_position
        self._current_bg_color = self._bg_color_on if self._checked else self._bg_color_off

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect()
        painter.setBrush(self._current_bg_color)
        painter.drawRoundedRect(rect, self._track_radius, self._track_radius)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(int(self.circle_position), self._circle_offset, self._circle_diameter, self._circle_diameter)
        painter.end()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mouseReleaseEvent(event)


class SettingsWindow(QDialog):
    """Окно для управления настройками приложения."""
    def __init__(self, config_manager: ConfigManager, app_icon: QIcon, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        self.setWindowTitle(self.tr("Undoit - Настройки"))
        self.setWindowIcon(app_icon)
        self.setMinimumWidth(750) # Увеличим минимальную ширину для нового интерфейса

        self._theme_display_to_key_map = {
            self.tr("Авто"): "auto", self.tr("Светлая"): "light", self.tr("Темная"): "dark"
        }
        self._theme_key_to_display_map = {v: k for k, v in self._theme_display_to_key_map.items()}

        self._lang_display_to_key_map = {
            self.tr("Авто"): "auto", self.tr("Русский"): "ru", self.tr("English"): "en"
        }
        self._lang_key_to_display_map = {v: k for k, v in self._lang_display_to_key_map.items()}

        # Получаем стандартные иконки
        self.folder_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.file_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- НОВАЯ СЕКЦИЯ "Отслеживаемые элементы" ---
        items_group = QGroupBox(self.tr("Отслеживаемые элементы"))
        items_main_layout = QHBoxLayout()

        # Левая панель: Список отслеживаемых файлов и папок
        items_list_layout = QVBoxLayout()
        self.items_list = QListWidget()
        self.items_list.itemSelectionChanged.connect(self._on_item_selection_changed)
        
        items_buttons_layout = QHBoxLayout()
        add_folder_button = QPushButton(self.tr("Добавить папку"))
        add_files_button = QPushButton(self.tr("Добавить файл(ы)"))
        self.remove_item_button = QPushButton(self.tr("Удалить выбранное"))
        
        add_folder_button.clicked.connect(self._add_folder)
        add_files_button.clicked.connect(self._add_files)
        self.remove_item_button.clicked.connect(self._remove_item)

        items_buttons_layout.addWidget(add_folder_button)
        items_buttons_layout.addWidget(add_files_button)
        items_buttons_layout.addWidget(self.remove_item_button)
        
        items_list_layout.addWidget(self.items_list)
        items_list_layout.addLayout(items_buttons_layout)

        # Правая панель: Список исключений для выбранной папки
        exclusions_layout = QVBoxLayout()
        self.exclusions_group = QGroupBox(self.tr("Исключения для папки"))
        exclusions_group_layout = QVBoxLayout()

        self.exclusions_list = QListWidget()
        self.exclusions_list.itemSelectionChanged.connect(self._update_buttons_state)

        exclusions_buttons_layout = QHBoxLayout()
        self.add_exclusion_button = QPushButton(self.tr("Добавить исключение"))
        self.remove_exclusion_button = QPushButton(self.tr("Удалить исключение"))

        self.add_exclusion_button.clicked.connect(self._add_exclusion)
        self.remove_exclusion_button.clicked.connect(self._remove_exclusion)

        exclusions_buttons_layout.addWidget(self.add_exclusion_button)
        exclusions_buttons_layout.addWidget(self.remove_exclusion_button)

        exclusions_group_layout.addWidget(self.exclusions_list)
        exclusions_group_layout.addLayout(exclusions_buttons_layout)
        self.exclusions_group.setLayout(exclusions_group_layout)
        exclusions_layout.addWidget(self.exclusions_group)

        items_main_layout.addLayout(items_list_layout, 2) # Левая панель в 2 раза шире
        items_main_layout.addLayout(exclusions_layout, 1) # Правая панель
        items_group.setLayout(items_main_layout)


        # --- Остальные секции (без изменений) ---
        general_group = QGroupBox(self.tr("Основные"))
        general_layout = QHBoxLayout()
        self.startup_switch = Switch()
        general_layout.addWidget(QLabel(self.tr("Запускать при старте системы")))
        general_layout.addStretch()
        general_layout.addWidget(self.startup_switch)
        general_group.setLayout(general_layout)

        appearance_group = QGroupBox(self.tr("Внешний вид"))
        appearance_layout = QVBoxLayout()
        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self._theme_display_to_key_map.keys()))
        theme_layout.addWidget(QLabel(self.tr("Тема приложения:")))
        theme_layout.addWidget(self.theme_combo)
        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(self._lang_display_to_key_map.keys()))
        lang_layout.addWidget(QLabel(self.tr("Язык интерфейса:")))
        lang_layout.addWidget(self.lang_combo)
        appearance_layout.addLayout(theme_layout)
        appearance_layout.addLayout(lang_layout)
        appearance_group.setLayout(appearance_layout)

        self.close_button = QPushButton(self.tr("Закрыть"))
        self.close_button.clicked.connect(self.accept)

        main_layout.addWidget(items_group)
        main_layout.addWidget(general_group)
        main_layout.addWidget(appearance_group)
        main_layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignRight)

        # Соединяем изменения с сохранением в конфиг
        self.startup_switch.toggled.connect(lambda c: self.config_manager.set("launch_on_startup", c))
        self.theme_combo.currentTextChanged.connect(lambda t: self.config_manager.set("theme", self._theme_display_to_key_map.get(t, "auto")))
        self.lang_combo.currentTextChanged.connect(lambda t: self.config_manager.set("language", self._lang_display_to_key_map.get(t, "auto")))

    def _load_settings(self):
        """Загружает текущие настройки в элементы UI."""
        self.items_list.clear()
        self.exclusions_list.clear()
        
        watched_items = self.config_manager.get_watched_items()
        for item_data in watched_items:
            path_str = item_data.get("path")
            item_type = item_data.get("type")

            list_item = QListWidgetItem(path_str)
            # Сохраняем весь словарь с данными прямо в элементе списка
            list_item.setData(Qt.ItemDataRole.UserRole, item_data)

            if item_type == "folder":
                list_item.setIcon(self.folder_icon)
            elif item_type == "file":
                list_item.setIcon(self.file_icon)
            
            self.items_list.addItem(list_item)
        
        self.startup_switch.setChecked(self.config_manager.get("launch_on_startup", False), animate=False)
        current_theme_key = self.config_manager.get("theme", "auto")
        self.theme_combo.setCurrentText(self._theme_key_to_display_map.get(current_theme_key, self.tr("Авто")))
        current_lang_key = self.config_manager.get("language", "auto")
        self.lang_combo.setCurrentText(self._lang_key_to_display_map.get(current_lang_key, self.tr("Авто")))
        
        self._update_buttons_state()

    def _save_changes(self):
        """Собирает данные из UI и сохраняет их в ConfigManager."""
        new_items_list = []
        for i in range(self.items_list.count()):
            list_item = self.items_list.item(i)
            item_data = list_item.data(Qt.ItemDataRole.UserRole)
            new_items_list.append(item_data)
        
        self.config_manager.set_watched_items(new_items_list)

    @Slot()
    def _on_item_selection_changed(self):
        """Обновляет панель исключений при выборе элемента в основном списке."""
        self.exclusions_list.clear()
        selected_items = self.items_list.selectedItems()

        if not selected_items:
            self.exclusions_group.setEnabled(False)
            self.exclusions_group.setTitle(self.tr("Исключения (выберите папку)"))
            self._update_buttons_state()
            return

        selected_item = selected_items[0]
        item_data = selected_item.data(Qt.ItemDataRole.UserRole)

        if item_data.get("type") == "folder":
            self.exclusions_group.setEnabled(True)
            self.exclusions_group.setTitle(self.tr("Исключения для: {0}").format(Path(item_data["path"]).name))
            exclusions = item_data.get("exclusions", [])
            for ex_path in exclusions:
                self.exclusions_list.addItem(QListWidgetItem(ex_path))
        else:
            self.exclusions_group.setEnabled(False)
            self.exclusions_group.setTitle(self.tr("Исключения (только для папок)"))
        
        self._update_buttons_state()

    def _update_buttons_state(self):
        """Обновляет состояние кнопок (вкл/выкл)."""
        is_item_selected = len(self.items_list.selectedItems()) > 0
        self.remove_item_button.setEnabled(is_item_selected)

        is_folder_selected = False
        if is_item_selected:
            item_data = self.items_list.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            is_folder_selected = item_data.get("type") == "folder"
            
        self.add_exclusion_button.setEnabled(is_folder_selected)
        self.remove_exclusion_button.setEnabled(is_folder_selected and len(self.exclusions_list.selectedItems()) > 0)

    @Slot()
    def _add_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Выберите папку для отслеживания"))
        if dir_path:
            self._add_item_to_list({"path": dir_path, "type": "folder", "exclusions": []})
    
    @Slot()
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Выберите файл(ы) для отслеживания"))
        if files:
            for file_path in files:
                self._add_item_to_list({"path": file_path, "type": "file", "exclusions": []})

    def _add_item_to_list(self, new_item_data: Dict):
        """Вспомогательный метод для добавления нового элемента в список."""
        new_path = Path(new_item_data["path"])
        # Проверяем, что такого пути еще нет
        for i in range(self.items_list.count()):
            item = self.items_list.item(i)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if Path(item_data["path"]).resolve() == new_path.resolve():
                return # Уже существует

        list_item = QListWidgetItem(new_item_data["path"])
        list_item.setData(Qt.ItemDataRole.UserRole, new_item_data)
        if new_item_data["type"] == "folder":
            list_item.setIcon(self.folder_icon)
        else:
            list_item.setIcon(self.file_icon)
        
        self.items_list.addItem(list_item)
        self._save_changes()

    @Slot()
    def _remove_item(self):
        for item in self.items_list.selectedItems():
            self.items_list.takeItem(self.items_list.row(item))
        self._save_changes()
        # После удаления сбрасываем панель исключений
        self._on_item_selection_changed()

    @Slot()
    def _add_exclusion(self):
        selected_items = self.items_list.selectedItems()
        if not selected_items: return
        
        folder_item = selected_items[0]
        folder_data = folder_item.data(Qt.ItemDataRole.UserRole)
        base_path = Path(folder_data["path"])

        ex_path = QFileDialog.getExistingDirectory(self, self.tr("Выберите папку для исключения"), str(base_path))
        
        if ex_path:
            ex_path_obj = Path(ex_path)
            # Валидация: убеждаемся, что исключение находится внутри отслеживаемой папки
            if not ex_path_obj.is_relative_to(base_path):
                # Здесь можно показать QMessageBox с предупреждением
                return

            current_exclusions = folder_data.get("exclusions", [])
            if ex_path not in current_exclusions:
                current_exclusions.append(ex_path)
                folder_data["exclusions"] = current_exclusions
                folder_item.setData(Qt.ItemDataRole.UserRole, folder_data)
                
                self.exclusions_list.addItem(QListWidgetItem(ex_path))
                self._save_changes()

    @Slot()
    def _remove_exclusion(self):
        selected_items = self.items_list.selectedItems()
        if not selected_items: return
        
        folder_item = selected_items[0]
        folder_data = folder_item.data(Qt.ItemDataRole.UserRole)
        
        exclusions_to_remove = {item.text() for item in self.exclusions_list.selectedItems()}
        current_exclusions = folder_data.get("exclusions", [])
        
        new_exclusions = [ex for ex in current_exclusions if ex not in exclusions_to_remove]
        
        if len(new_exclusions) != len(current_exclusions):
            folder_data["exclusions"] = new_exclusions
            folder_item.setData(Qt.ItemDataRole.UserRole, folder_data)
            
            # Обновляем UI
            self.exclusions_list.clear()
            for ex in new_exclusions:
                self.exclusions_list.addItem(QListWidgetItem(ex))
            
            self._save_changes()