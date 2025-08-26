# -*- coding: utf-8 -*-
# GUI: Окно настроек
from pathlib import Path
from typing import List

from PySide6.QtCore import (QEasingCurve, QPoint, QPointF, QPropertyAnimation,
                            Qt, Signal, Slot)
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from app.config_manager import ConfigManager


class Switch(QWidget):
    """Кастомный виджет-переключатель (toggle switch)."""
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

        self._circle_position = 3
        self._bg_color = QColor("#808080")  # Серый (выключено)
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.animation.setDuration(200)

    @property
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def setChecked(self, checked):
        self._checked = checked
        start_pos = 25 if checked else 3
        end_pos = 3 if checked else 25
        self.animation.setStartValue(end_pos)
        self.animation.setEndValue(start_pos)
        self.animation.start()
        self._bg_color = QColor("#0078D4") if checked else QColor("#808080")

    def isChecked(self):
        return self._checked

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Рисуем фон (дорожку)
        rect = self.rect()
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(rect, 14, 14)
        
        # Рисуем круг (бегунок)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(self._circle_position, 3, 22, 22)

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.setChecked(self._checked)
        self.toggled.emit(self._checked)


class SettingsWindow(QDialog):
    """Окно для управления настройками приложения."""
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        self.setWindowTitle("Backdraft - Настройки")
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Секция "Отслеживаемые папки" ---
        folders_group = QGroupBox("Отслеживаемые папки")
        folders_layout = QVBoxLayout()
        
        self.paths_list = QListWidget()
        self.paths_list.itemSelectionChanged.connect(self._update_buttons_state)
        
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить папку")
        self.remove_button = QPushButton("Удалить выбранную")
        add_button.clicked.connect(self._add_path)
        self.remove_button.clicked.connect(self._remove_path)
        
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(self.remove_button)
        
        folders_layout.addWidget(self.paths_list)
        folders_layout.addLayout(buttons_layout)
        folders_group.setLayout(folders_layout)
        
        # --- Секция "Основные настройки" ---
        general_group = QGroupBox("Основные")
        general_layout = QHBoxLayout()
        self.startup_switch = Switch()
        general_layout.addWidget(QLabel("Запускать при старте системы"))
        general_layout.addStretch()
        general_layout.addWidget(self.startup_switch)
        general_group.setLayout(general_layout)

        # --- Секция "Внешний вид" ---
        appearance_group = QGroupBox("Внешний вид")
        appearance_layout = QVBoxLayout()
        
        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Авто", "Светлая", "Темная"])
        theme_layout.addWidget(QLabel("Тема приложения:"))
        theme_layout.addWidget(self.theme_combo)
        
        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Авто", "Русский", "English"])
        lang_layout.addWidget(QLabel("Язык интерфейса:"))
        lang_layout.addWidget(self.lang_combo)
        
        appearance_layout.addLayout(theme_layout)
        appearance_layout.addLayout(lang_layout)
        appearance_group.setLayout(appearance_layout)

        # --- Кнопка закрытия ---
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)

        main_layout.addWidget(folders_group)
        main_layout.addWidget(general_group)
        main_layout.addWidget(appearance_group)
        main_layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignRight)
        
        # Соединяем изменения с сохранением в конфиг
        self.startup_switch.toggled.connect(
            lambda checked: self.config_manager.set("launch_on_startup", checked)
        )
        self.theme_combo.currentTextChanged.connect(
            lambda text: self.config_manager.set("theme", text.lower())
        )
        self.lang_combo.currentTextChanged.connect(
            lambda text: self.config_manager.set("language", text.lower())
        )

    def _load_settings(self):
        """Загружает текущие настройки в элементы UI."""
        # Папки
        self.paths_list.clear()
        paths = self.config_manager.get_watched_paths()
        for path in paths:
            self.paths_list.addItem(QListWidgetItem(path))
        self._update_buttons_state()

        # Переключатель
        self.startup_switch.setChecked(self.config_manager.get("launch_on_startup", False))
        
        # Выпадающие списки
        theme_map = {"auto": "Авто", "light": "Светлая", "dark": "Темная"}
        current_theme_key = self.config_manager.get("theme", "auto")
        self.theme_combo.setCurrentText(theme_map.get(current_theme_key, "Авто"))

        lang_map = {"auto": "Авто", "ru": "Русский", "en": "English"}
        current_lang_key = self.config_manager.get("language", "auto")
        self.lang_combo.setCurrentText(lang_map.get(current_lang_key, "Авто"))

    def _update_buttons_state(self):
        """Обновляет состояние кнопок (вкл/выкл)."""
        self.remove_button.setEnabled(len(self.paths_list.selectedItems()) > 0)

    @Slot()
    def _add_path(self):
        """Открывает диалог выбора папки и добавляет ее в список."""
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку для отслеживания")
        if dir_path:
            current_paths = [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
            if dir_path not in current_paths:
                self.paths_list.addItem(QListWidgetItem(dir_path))
                current_paths.append(dir_path)
                self.config_manager.set_watched_paths(current_paths)

    @Slot()
    def _remove_path(self):
        """Удаляет выбранную папку из списка."""
        selected_items = self.paths_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.paths_list.takeItem(self.paths_list.row(item))
            
        current_paths = [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
        self.config_manager.set_watched_paths(current_paths)