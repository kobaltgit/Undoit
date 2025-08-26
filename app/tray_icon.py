# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon # <-- Добавлен импорт QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.config_manager import ConfigManager
from app.file_watcher import FileWatcher
from app.history_manager import HistoryManager
from app.icon_generator import IconGenerator
from app.startup_manager import StartupManager
from app.ui.main_window import HistoryWindow
from app.ui.settings_window import SettingsWindow


class TrayIcon(QSystemTrayIcon):
    """
    Класс для управления иконкой приложения в системном трее.
    Является главным координатором, управляющим всеми сервисами.
    """
    def __init__(self, config_manager: ConfigManager, storage_path: Path, 
                 paths_to_watch: List[str], app_name: str, app_executable_path: Path,
                 app_icon: QIcon, # <-- Добавлен новый параметр app_icon
                 parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.app_icon = app_icon # <-- Сохраняем адаптивную иконку приложения
        self.history_window = None
        self.settings_window = None

        # 1. Инициализируем сервисы
        self.icon_generator = IconGenerator() # icon_generator тут остается для генерации *иконок трея*
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(paths_to_watch)
        self.startup_manager = StartupManager(app_name, app_executable_path)

        # 2. Устанавливаем начальную иконку для трея (генерируемую программно)
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

        self.config_manager.settings_changed.connect(self._on_settings_changed)
        # <-- Подключаем сигнал от StartupManager для показа уведомлений
        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Запускаем первичное сканирование
        self.history_manager.start_initial_scan(paths_to_watch)

        # 7. Применяем текущие настройки автозапуска при старте
        self._apply_initial_startup_setting()


    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        self.history_action = QAction("Открыть историю версий", self)
        self.history_action.triggered.connect(self._open_history_window)
        self.menu.addAction(self.history_action)

        self.settings_action = QAction("Настройки", self)
        self.settings_action.triggered.connect(self._open_settings_window)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.toggle_watch_action = QAction("Приостановить отслеживание", self)
        self.toggle_watch_action.setCheckable(True)
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        self.toggle_watch_action.setEnabled(False)
        self.menu.addAction(self.toggle_watch_action)

        self.menu.addSeparator()

        self.quit_action = QAction("Выход", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _open_history_window(self):
        """Создает (если нужно) и показывает окно истории."""
        if self.history_window is None:
            self.history_window = HistoryWindow(
                history_manager=self.history_manager,
                app_icon=self.app_icon # <-- Передаем иконку приложения
            )
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)

        self.history_window.show()
        self.history_window.activateWindow()
        self.history_window.raise_()

    def _open_settings_window(self):
        """Создает (если нужно) и показывает окно настроек."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                config_manager=self.config_manager,
                app_icon=self.app_icon # <-- Передаем иконку приложения
            )
            self.settings_window.finished.connect(lambda: setattr(self, 'settings_window', None))

        if not self.settings_window.isVisible():
            self.settings_window.exec()
        else:
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    @Slot()
    def _on_scan_started(self):
        """Слот, вызываемый при начале первичного сканирования."""
        print("TrayIcon: Получен сигнал о начале сканирования.")
        self.setIcon(self.icon_generator.get_icon('saving')) # Используем генерируемую иконку трея
        self.setToolTip("Backdraft: Идет сканирование файлов...")
        self.toggle_watch_action.setEnabled(False)

    @Slot()
    def _on_scan_finished(self):
        """Слот, вызываемый по завершении сканирования."""
        print("TrayIcon: Получен сигнал о завершении сканирования.")
        self.setIcon(self.icon_generator.get_icon('normal')) # Используем генерируемую иконку трея
        self.setToolTip("Backdraft: Мониторинг активен.")
        self.toggle_watch_action.setEnabled(True)
        self.watcher.start()

    def _on_toggle_watch(self, checked: bool):
        """Слот для приостановки/возобновления отслеживания файлов."""
        if checked:
            self.watcher.stop()
            self.setIcon(self.icon_generator.get_icon('paused')) # Используем генерируемую иконку трея
            self.setToolTip("Backdraft: Мониторинг приостановлен.")
            self.toggle_watch_action.setText("Возобновить отслеживание")
        else:
            self.watcher.start()
            self.setIcon(self.icon_generator.get_icon('normal')) # Используем генерируемую иконку трея
            self.setToolTip("Backdraft: Мониторинг активен.")
            self.toggle_watch_action.setText("Приостановить отслеживание")

    @Slot()
    def _on_settings_changed(self):
        """
        Слот, вызываемый при изменении любых настроек в ConfigManager.
        Проверяет настройку 'launch_on_startup' и соответствующим образом
        обновляет автозапуск через StartupManager.
        """
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)
        # print(f"TrayIcon: Настройка 'launch_on_startup' изменена на: {enable_startup}")
        # Уведомление об изменении будет генерироваться сигналом startup_action_completed

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        """
        Слот, вызываемый по завершении операции StartupManager (добавление/удаление в автозапуск).
        Показывает всплывающее уведомление.
        """
        self.showMessage(
            "Backdraft - Автозапуск",
            message,
            icon_type, # Используем тип иконки (Information, Warning, Critical)
            5000 # Время отображения в мс
        )
        # Примечание: Основная иконка приложения в уведомлении (если ОС ее показывает)
        # будет та, что установлена через QApplication.setWindowIcon() в main.py.

    def _apply_initial_startup_setting(self):
        """Применяет настройку автозапуска при первом старте TrayIcon."""
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)
        # print(f"TrayIcon: Инициализация автозапуска в соответствии с настройкой: {enable_startup}")
        # Уведомление будет сгенерировано StartupManager'ом, если произойдет фактическое изменение.

    def _on_quit(self):
        """Слот, который вызывается перед закрытием приложения для очистки."""
        print("Приложение закрывается, останавливаем сервисы...")
        self.watcher.stop()
        self.history_manager.close()
        print("Сервисы остановлены.")
