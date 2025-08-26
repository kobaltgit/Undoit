# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PySide6.QtCore import Slot

from app.file_watcher import FileWatcher
from app.history_manager import HistoryManager
from app.icon_generator import IconGenerator


class TrayIcon(QSystemTrayIcon):
    """
    Класс для управления иконкой приложения в системном трее.
    Является главным координатором, управляющим всеми сервисами.
    """
    def __init__(self, storage_path: Path, paths_to_watch: List[str], parent=None):
        super().__init__(parent)

        # 1. Инициализируем сервисы
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(paths_to_watch)

        # 2. Устанавливаем начальную иконку
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip("Backdraft: Инициализация...")

        # 3. Создаем контекстное меню
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 4. Соединяем компоненты
        # Сигнал об изменении файла от watcher'а к history_manager'у
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        # Сигналы о сканировании от history_manager'а к TrayIcon'у
        self.history_manager.initial_scan_started.connect(self._on_scan_started)
        self.history_manager.initial_scan_finished.connect(self._on_scan_finished)
        
        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Запускаем первичное сканирование (вместо watcher.start())
        self.history_manager.start_initial_scan(paths_to_watch)

    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        self.settings_action = QAction("Настройки", self)
        self.settings_action.triggered.connect(self._on_settings)
        self.menu.addAction(self.settings_action)

        self.toggle_watch_action = QAction("Приостановить отслеживание", self)
        self.toggle_watch_action.setCheckable(True)
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        self.toggle_watch_action.setEnabled(False) # Отключено во время сканирования
        self.menu.addAction(self.toggle_watch_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Выход", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    @Slot()
    def _on_scan_started(self):
        """Слот, вызываемый при начале первичного сканирования."""
        print("TrayIcon: Получен сигнал о начале сканирования.")
        self.setIcon(self.icon_generator.get_icon('saving'))
        self.setToolTip("Backdraft: Идет сканирование файлов...")
        self.toggle_watch_action.setEnabled(False) # Блокируем кнопку "Пауза"

    @Slot()
    def _on_scan_finished(self):
        """Слот, вызываемый по завершении сканирования."""
        print("TrayIcon: Получен сигнал о завершении сканирования.")
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip("Backdraft: Мониторинг активен.")
        self.toggle_watch_action.setEnabled(True) # Разблокируем кнопку "Пауза"
        self.watcher.start() # <-- ЗАПУСКАЕМ ОТСЛЕЖИВАНИЕ ТОЛЬКО СЕЙЧАС

    def _on_settings(self):
        """Слот для открытия окна настроек."""
        print("Действие: Открыть настройки")

    def _on_toggle_watch(self, checked: bool):
        """Слот для приостановки/возобновления отслеживания файлов."""
        if checked:
            self.watcher.stop()
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip("Backdraft: Мониторинг приостановлен.")
            self.toggle_watch_action.setText("Возобновить отслеживание")
        else:
            self.watcher.start()
            self.setIcon(self.icon_generator.get_icon('normal'))
            self.setToolTip("Backdraft: Мониторинг активен.")
            self.toggle_watch_action.setText("Приостановить отслеживание")

    def _on_quit(self):
        """Слот, который вызывается перед закрытием приложения для очистки."""
        print("Приложение закрывается, останавливаем сервисы...")
        self.watcher.stop()
        self.history_manager.close()
        print("Сервисы остановлены.")