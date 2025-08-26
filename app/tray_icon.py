# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.file_watcher import FileWatcher
from app.history_manager import HistoryManager
from app.icon_generator import IconGenerator
from app.ui.main_window import HistoryWindow


class TrayIcon(QSystemTrayIcon):
    """
    Класс для управления иконкой приложения в системном трее.
    Является главным координатором, управляющим всеми сервисами.
    """
    def __init__(self, storage_path: Path, paths_to_watch: List[str], parent=None):
        super().__init__(parent)
        
        # Переменная для хранения единственного экземпляра окна
        self.history_window = None

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
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        self.history_manager.initial_scan_started.connect(self._on_scan_started)
        self.history_manager.initial_scan_finished.connect(self._on_scan_finished)
        
        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Запускаем первичное сканирование
        self.history_manager.start_initial_scan(paths_to_watch)

    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        # --- Действие "Открыть историю" ---
        self.history_action = QAction("Открыть историю версий", self)
        self.history_action.triggered.connect(self._open_history_window)
        self.menu.addAction(self.history_action)

        # --- Действие "Пауза/Возобновить" ---
        self.toggle_watch_action = QAction("Приостановить отслеживание", self)
        self.toggle_watch_action.setCheckable(True)
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        self.toggle_watch_action.setEnabled(False)
        self.menu.addAction(self.toggle_watch_action)

        self.menu.addSeparator()

        # --- Действие "Выход" ---
        self.quit_action = QAction("Выход", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _open_history_window(self):
        """Создает (если нужно) и показывает окно истории."""
        if self.history_window is None:
            # Окно создается только один раз при первом вызове
            self.history_window = HistoryWindow(history_manager=self.history_manager)
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)

        # Показываем окно и делаем его активным
        self.history_window.show()
        self.history_window.activateWindow()
        self.history_window.raise_() # Для macOS и некоторых оконных менеджеров Linux

    @Slot()
    def _on_scan_started(self):
        """Слот, вызываемый при начале первичного сканирования."""
        print("TrayIcon: Получен сигнал о начале сканирования.")
        self.setIcon(self.icon_generator.get_icon('saving'))
        self.setToolTip("Backdraft: Идет сканирование файлов...")
        self.toggle_watch_action.setEnabled(False)

    @Slot()
    def _on_scan_finished(self):
        """Слот, вызываемый по завершении сканирования."""
        print("TrayIcon: Получен сигнал о завершении сканирования.")
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip("Backdraft: Мониторинг активен.")
        self.toggle_watch_action.setEnabled(True)
        self.watcher.start()

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