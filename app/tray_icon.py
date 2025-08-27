# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List

from PySide6.QtCore import Slot, QTimer # <-- Добавлен импорт QTimer
from PySide6.QtGui import QAction, QIcon
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
                 app_icon: QIcon,
                 parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.app_icon = app_icon
        self.history_window = None
        self.settings_window = None
        self.app_name = app_name # Сохраняем имя приложения

        # 1. Инициализируем сервисы
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        # Инициализируем watcher с пустым списком, так как реальный список будет передан позже
        self.watcher = FileWatcher([]) # <-- Инициализация с пустым списком
        self.startup_manager = StartupManager(app_name, app_executable_path)

        # 2. Устанавливаем начальную иконку для трея (генерируемую программно)
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip(self.tr("Backdraft: Инициализация...")) # <-- Размечено для перевода

        # 3. Создаем контекстное меню
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 4. Соединяем компоненты
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        self.history_manager.initial_scan_started.connect(self._on_scan_started)
        self.history_manager.initial_scan_finished.connect(self._on_scan_finished)
        # Соединяем сигнал уведомлений HistoryManager со слотом TrayIcon
        self.history_manager.history_notification.connect(lambda msg, icon: self.show_notification(
            self.tr("Backdraft - История"), msg, icon
        ))

        self.config_manager.settings_changed.connect(self._on_settings_changed)
        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Запускаем первичное сканирование (или обновляем пути, если уже был вызов из main)
        # Откладываем запуск сканирования, чтобы ensure_paths_watched мог сначала установить пути
        QTimer.singleShot(0, lambda: self.ensure_paths_watched(paths_to_watch))

        # 7. Применяем текущие настройки автозапуска при старте
        self._apply_initial_startup_setting()

    @Slot(str, str, QSystemTrayIcon.MessageIcon)
    def show_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information):
        """
        Показывает всплывающее уведомление в системном трее.
        Это общий слот для всех уведомлений.
        """
        self.showMessage(title, message, icon_type, 5000)

    def update_watched_paths(self, new_paths: List[str]):
        """
        Обновляет список отслеживаемых папок для FileWatcher.
        Останавливает текущий watcher и создает новый, если пути изменились.
        """
        if sorted(self.watcher._paths) == sorted(new_paths):
            # print("TrayIcon: Список отслеживаемых папок не изменился.")
            return

        # Если watcher активен, останавливаем его
        if self.watcher._observer.is_alive():
            self.watcher.stop()

        # Обновляем пути и перезапускаем watcher
        self.watcher._paths = new_paths
        if new_paths: # Запускаем только если есть пути для отслеживания
            # print(f"TrayIcon: Обновляю отслеживаемые папки: {new_paths}. Перезапускаю watcher.")
            self.show_notification(
                self.tr("Backdraft - Отслеживание"),
                self.tr("Список отслеживаемых папок обновлен. Перезапускаю мониторинг."),
                QSystemTrayIcon.Information
            )
            self.watcher.start()
        else:
            self.show_notification(
                self.tr("Backdraft - Отслеживание"),
                self.tr("Нет папок для отслеживания. Мониторинг остановлен."),
                QSystemTrayIcon.Warning
            )


    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        self.history_action = QAction(self.tr("Открыть историю версий"), self) # <-- Размечено для перевода
        self.history_action.triggered.connect(self._open_history_window)
        self.menu.addAction(self.history_action)

        self.settings_action = QAction(self.tr("Настройки"), self) # <-- Размечено для перевода
        self.settings_action.triggered.connect(self._open_settings_window)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.toggle_watch_action = QAction(self.tr("Приостановить отслеживание"), self) # <-- Размечено для перевода
        self.toggle_watch_action.setCheckable(True)
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        # Изначально кнопка отключена до завершения первичного сканирования
        self.toggle_watch_action.setEnabled(False) 
        self.menu.addAction(self.toggle_watch_action)

        self.menu.addSeparator()

        self.quit_action = QAction(self.tr("Выход"), self) # <-- Размечено для перевода
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _open_history_window(self):
        """Создает (если нужно) и показывает окно истории."""
        if self.history_window is None:
            self.history_window = HistoryWindow(
                history_manager=self.history_manager,
                app_icon=self.app_icon
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
                app_icon=self.app_icon
            )
            self.settings_window.finished.connect(lambda: setattr(self, 'settings_window', None))

        if not self.settings_window.isVisible():
            self.settings_window.exec()
        else:
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    def ensure_paths_watched(self, paths: List[str]):
        """
        Устанавливает пути для отслеживания и запускает сканирование/мониторинг.
        Этот метод вызывается после того, как `main.py` проверит начальные пути.
        """
        self.watcher._paths = paths # Устанавливаем пути для watcher
        self.history_manager.start_initial_scan(paths)


    @Slot()
    def _on_scan_started(self):
        """Слот, вызываемый при начале первичного сканирования."""
        # print(self.tr("TrayIcon: Получен сигнал о начале сканирования.")) # <-- Размечено для перевода (хотя это лог)
        self.setIcon(self.icon_generator.get_icon('saving'))
        self.setToolTip(self.tr("Backdraft: Идет сканирование файлов...")) # <-- Размечено для перевода
        self.toggle_watch_action.setEnabled(False)

    @Slot()
    def _on_scan_finished(self):
        """Слот, вызываемый по завершении сканирования."""
        # print(self.tr("TrayIcon: Получен сигнал о завершении сканирования.")) # <-- Размечено для перевода (хотя это лог)
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip(self.tr("Backdraft: Мониторинг активен.")) # <-- Размечено для перевода
        self.toggle_watch_action.setEnabled(True)
        # Запускаем watcher только после завершения сканирования и если есть пути
        if self.watcher._paths:
            self.watcher.start()
        else:
            self.show_notification(
                self.tr("Backdraft - Отслеживание"),
                self.tr("Нет папок для отслеживания. Мониторинг не запущен."),
                QSystemTrayIcon.Warning
            )


    def _on_toggle_watch(self, checked: bool):
        """Слот для приостановки/возобновления отслеживания файлов."""
        if checked:
            self.watcher.stop()
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip(self.tr("Backdraft: Мониторинг приостановлен.")) # <-- Размечено для перевода
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание")) # <-- Размечено для перевода
            self.show_notification(
                self.tr("Backdraft - Мониторинг"),
                self.tr("Отслеживание файлов приостановлено."),
                QSystemTrayIcon.Information
            )
        else:
            # Проверяем, есть ли пути для отслеживания перед стартом
            if self.watcher._paths:
                self.watcher.start()
                self.setIcon(self.icon_generator.get_icon('normal'))
                self.setToolTip(self.tr("Backdraft: Мониторинг активен.")) # <-- Размечено для перевода
                self.toggle_watch_action.setText(self.tr("Приостановить отслеживание")) # <-- Размечено для перевода
                self.show_notification(
                    self.tr("Backdraft - Мониторинг"),
                    self.tr("Отслеживание файлов возобновлено."),
                    QSystemTrayIcon.Information
                )
            else:
                self.show_notification(
                    self.tr("Backdraft - Мониторинг"),
                    self.tr("Нет папок для отслеживания. Мониторинг не может быть возобновлен."),
                    QSystemTrayIcon.Warning
                )
                self.toggle_watch_action.setChecked(True) # Возвращаем в состояние "приостановлено", т.к. не смогли возобновить

    @Slot()
    def _on_settings_changed(self):
        """
        Слот, вызываемый при изменении любых настроек в ConfigManager.
        Проверяет настройку 'launch_on_startup' и соответствующим образом
        обновляет автозапуск через StartupManager, а также обновляет
        список отслеживаемых папок.
        """
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)
        # print(f"TrayIcon: Настройка 'launch_on_startup' изменена на: {enable_startup}")
        # Уведомление об изменении будет генерироваться сигналом startup_action_completed

        # Обновляем список отслеживаемых папок, если он изменился
        new_watched_paths = self.config_manager.get_watched_paths()
        # Проверяем на существование, как это делается в main
        valid_new_paths = []
        for path in new_watched_paths:
            if Path(path).exists():
                valid_new_paths.append(path)
            else:
                self.show_notification(
                    self.tr("Backdraft - Отслеживание"),
                    self.tr("Внимание: Указанный путь '{0}' не существует и будет проигнорирован.").format(path),
                    QSystemTrayIcon.Warning
                )

        self.update_watched_paths(valid_new_paths)


    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        """
        Слот, вызываемый по завершении операции StartupManager (добавление/удаление в автозапуск).
        Показывает всплывающее уведомление.
        """
        self.show_notification(
            self.tr("Backdraft - Автозапуск"), # <-- Размечено для перевода
            message,
            icon_type,
        )

    def _apply_initial_startup_setting(self):
        """Применяет настройку автозапуска при первом старте TrayIcon."""
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)
        # print(f"TrayIcon: Инициализация автозапуска в соответствии с настройкой: {enable_startup}")
        # Уведомление будет сгенерировано StartupManager'ом, если произойдет фактическое изменение.

    def _on_quit(self):
        """Слот, который вызывается перед закрытием приложения для очистки."""
        # print(self.tr("Приложение закрывается, останавливаем сервисы...")) # <-- Размечено для перевода (хотя это лог)
        self.show_notification(
            self.app_name,
            self.tr("Приложение закрывается. Останавливаю сервисы..."),
            QSystemTrayIcon.Information
        )
        self.watcher.stop()
        self.history_manager.close()
        # print(self.tr("Сервисы остановлены.")) # <-- Размечено для перевода (хотя это лог)
        self.show_notification(
            self.app_name,
            self.tr("Сервисы остановлены."),
            QSystemTrayIcon.Information
        )
