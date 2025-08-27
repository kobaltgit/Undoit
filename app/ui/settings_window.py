# -*- coding: utf-8 -*-
# GUI: Окно настроек
from pathlib import Path
from typing import List

from PySide6.QtCore import (QEasingCurve, QPoint, QPointF, QPropertyAnimation,
                            Qt, Signal, Slot, Property)
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QIcon
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QGroupBox,
                               QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from app.config_manager import ConfigManager


class Switch(QWidget):
    """Кастомный виджет-переключатель (toggle switch)."""
    toggled = Signal(bool)

    # Приватное хранилище для значения свойства circle_position
    _circle_position_val: float = 0.0

    # Геттер для свойства Qt
    def _get_circle_position(self) -> float:
        return self._circle_position_val

    # Сеттер для свойства Qt, который также вызывает перерисовку
    def _set_circle_position(self, pos: float):
        self._circle_position_val = pos
        self.update() # Запрашиваем перерисовку при изменении позиции

    # Объявление свойства Qt: тип, геттер, сеттер
    circle_position = Property(float, _get_circle_position, _set_circle_position)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

        self._circle_offset = 3  # Смещение круга сверху/снизу
        self._circle_diameter = 22 # Диаметр круга
        self._track_height = 28 # Высота дорожки
        self._track_radius = 14 # Радиус скругления дорожки (половина _track_height)

        # Инициализируем хранилище свойства начальным значением "выключено"
        self._circle_position_val = float(self._circle_offset)

        self._bg_color_off = QColor("#808080")  # Серый (выключено)
        self._bg_color_on = QColor("#0078D4")   # Акцентный синий (включено)
        self._current_bg_color = self._bg_color_off

        # Анимация теперь будет анимировать объявленное свойство Qt 'circle_position'
        self.animation = QPropertyAnimation(self, b"circle_position", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.animation.setDuration(200)

        # Устанавливаем начальное состояние без анимации
        self.setChecked(self._checked, animate=False)

    def setChecked(self, checked: bool, animate: bool = True):
        if self._checked == checked:
            return

        self._checked = checked

        # Рассчитываем целевую позицию круга на основе текущей ширины виджета
        target_position = float((self.width() - self._circle_offset - self._circle_diameter) if self._checked else self._circle_offset)

        if animate:
            # Начальное значение берется из текущего состояния свойства Qt
            self.animation.setStartValue(self.circle_position) 
            self.animation.setEndValue(target_position)
            self.animation.start()
        else:
            # Если без анимации, напрямую устанавливаем свойство Qt.
            # Это вызовет _set_circle_position и self.update().
            self.circle_position = target_position 

        self._current_bg_color = self._bg_color_on if self._checked else self._bg_color_off

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Рисуем фон (дорожку)
        rect = self.rect()
        painter.setBrush(self._current_bg_color)
        painter.drawRoundedRect(rect, self._track_radius, self._track_radius)

        # Рисуем круг (бегунок). Используем int() для координат.
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(int(self.circle_position), self._circle_offset, self._circle_diameter, self._circle_diameter)
        painter.end()

    def mouseReleaseEvent(self, event):
        # Только если кнопка была нажата и отпущена внутри виджета
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mouseReleaseEvent(event) # Вызываем родительский метод для обработки других событий

class SettingsWindow(QDialog):
    """Окно для управления настройками приложения."""
    def __init__(self, config_manager: ConfigManager, app_icon: QIcon, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        self.setWindowTitle(self.tr("Backdraft - Настройки")) # <-- Размечено для перевода
        self.setWindowIcon(app_icon)
        self.setMinimumWidth(500)

        # <-- ИСПРАВЛЕНИЕ: Словари для прямого и обратного сопоставления с _переводимыми_ ключами
        self._theme_display_to_key_map = {
            self.tr("Авто"): "auto", 
            self.tr("Светлая"): "light", 
            self.tr("Темная"): "dark"
        }
        self._theme_key_to_display_map = {v: k for k, v in self._theme_display_to_key_map.items()}

        self._lang_display_to_key_map = {
            self.tr("Авто"): "auto", 
            self.tr("Русский"): "ru", 
            self.tr("English"): "en"
        }
        self._lang_key_to_display_map = {v: k for k, v in self._lang_display_to_key_map.items()}
        # -->

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Секция "Отслеживаемые папки" ---
        folders_group = QGroupBox(self.tr("Отслеживаемые папки")) # <-- Размечено для перевода
        folders_layout = QVBoxLayout()

        self.paths_list = QListWidget()
        # self.paths_list.setPlaceholderText(self.tr("Добавьте папки для отслеживания")) # Можно добавить плейсхолдер
        self.paths_list.itemSelectionChanged.connect(self._update_buttons_state)

        buttons_layout = QHBoxLayout()
        add_button = QPushButton(self.tr("Добавить папку")) # <-- Размечено для перевода
        self.remove_button = QPushButton(self.tr("Удалить выбранную")) # <-- Размечено для перевода
        add_button.clicked.connect(self._add_path)
        self.remove_button.clicked.connect(self._remove_path)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(self.remove_button)

        folders_layout.addWidget(self.paths_list)
        folders_layout.addLayout(buttons_layout)
        folders_group.setLayout(folders_layout)

        # --- Секция "Основные настройки" ---
        general_group = QGroupBox(self.tr("Основные")) # <-- Размечено для перевода
        general_layout = QHBoxLayout()
        self.startup_switch = Switch()
        general_layout.addWidget(QLabel(self.tr("Запускать при старте системы"))) # <-- Размечено для перевода
        general_layout.addStretch()
        general_layout.addWidget(self.startup_switch)
        general_group.setLayout(general_layout)

        # --- Секция "Внешний вид" ---
        appearance_group = QGroupBox(self.tr("Внешний вид")) # <-- Размечено для перевода
        appearance_layout = QVBoxLayout()

        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self._theme_display_to_key_map.keys())) # <-- Используем переводимые ключи отображения
        theme_layout.addWidget(QLabel(self.tr("Тема приложения:"))) # <-- Размечено для перевода
        theme_layout.addWidget(self.theme_combo)

        lang_layout = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(self._lang_display_to_key_map.keys())) # <-- Используем переводимые ключи отображения
        lang_layout.addWidget(QLabel(self.tr("Язык интерфейса:"))) # <-- Размечено для перевода
        lang_layout.addWidget(self.lang_combo)

        appearance_layout.addLayout(theme_layout)
        appearance_layout.addLayout(lang_layout)
        appearance_group.setLayout(appearance_layout)

        # --- Кнопка закрытия ---
        self.close_button = QPushButton(self.tr("Закрыть")) # <-- Размечено для перевода
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
            lambda text: self.config_manager.set("theme", self._theme_display_to_key_map.get(text, "auto"))
        )
        self.lang_combo.currentTextChanged.connect(
            lambda text: self.config_manager.set("language", self._lang_display_to_key_map.get(text, "auto"))
        )

    def _load_settings(self):
        """Загружает текущие настройки в элементы UI."""
        # Папки
        self.paths_list.clear()
        paths = self.config_manager.get_watched_paths()
        for path in paths:
            self.paths_list.addItem(QListWidgetItem(path))
        self._update_buttons_state()

        # Переключатель - устанавливаем без анимации
        self.startup_switch.setChecked(self.config_manager.get("launch_on_startup", False), animate=False)

        # Выпадающие списки
        current_theme_key = self.config_manager.get("theme", "auto")
        self.theme_combo.setCurrentText(self._theme_key_to_display_map.get(current_theme_key, self.tr("Авто"))) # <-- Используем переводимый "Авто"

        current_lang_key = self.config_manager.get("language", "auto")
        self.lang_combo.setCurrentText(self._lang_key_to_display_map.get(current_lang_key, self.tr("Авто"))) # <-- Используем переводимый "Авто"

    def _update_buttons_state(self):
        """Обновляет состояние кнопок (вкл/выкл)."""
        self.remove_button.setEnabled(len(self.paths_list.selectedItems()) > 0)

    @Slot()
    def _add_path(self):
        """Открывает диалог выбора папки и добавляет ее в список."""
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Выберите папку для отслеживания")) # <-- Размечено для перевода
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
