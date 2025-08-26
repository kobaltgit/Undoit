# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PySide6.QtGui import QAction

from app.icon_generator import IconGenerator


class TrayIcon(QSystemTrayIcon):
    """
    Класс для управления иконкой приложения в системном трее.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. Инициализируем наш генератор иконок
        self.icon_generator = IconGenerator()

        # 2. Устанавливаем начальную иконку и всплывающую подсказку
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip("Backdraft: Мониторинг активен.")

        # 3. Создаем контекстное меню
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # TODO: Добавить обработчики для смены состояния (saving, paused, error)

    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        # --- Действие "Настройки" ---
        self.settings_action = QAction("Настройки", self)
        self.settings_action.triggered.connect(self._on_settings)
        self.menu.addAction(self.settings_action)

        # --- Действие "Пауза/Возобновить" ---
        self.toggle_watch_action = QAction("Приостановить отслеживание", self)
        self.toggle_watch_action.setCheckable(True) # Делаем его переключателем
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        self.menu.addAction(self.toggle_watch_action)

        # --- Разделитель ---
        self.menu.addSeparator()

        # --- Действие "Выход" ---
        self.quit_action = QAction("Выход", self)
        # Подключаем к стандартному слоту выхода из приложения
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _on_settings(self):
        """Слот для открытия окна настроек."""
        # TODO: Реализовать открытие окна настроек
        print("Действие: Открыть настройки")

    def _on_toggle_watch(self, checked: bool):
        """Слот для приостановки/возобновления отслеживания файлов."""
        if checked:
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip("Backdraft: Мониторинг приостановлен.")
            self.toggle_watch_action.setText("Возобновить отслеживание")
            print("Статус: Мониторинг приостановлен")
            # TODO: Добавить логику реальной остановки file_watcher
        else:
            self.setIcon(self.icon_generator.get_icon('normal'))
            self.setToolTip("Backdraft: Мониторинг активен.")
            self.toggle_watch_action.setText("Приостановить отслеживание")
            print("Статус: Мониторинг активен")
            # TODO: Добавить логику реального возобновления file_watcher