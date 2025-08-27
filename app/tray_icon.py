# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List, Set

from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.config_manager import ConfigManager
from app.file_watcher import FileWatcher
from app.history_manager import HistoryManager
from app.icon_generator import IconGenerator
from app.notification_aggregator import NotificationAggregator
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
        self.app_name = app_name
        self._current_watched_paths: Set[Path] = {Path(p).resolve() for p in paths_to_watch if Path(p).exists()}

        # 1. Инициализируем сервисы и новый агрегатор уведомлений
        self.aggregator = NotificationAggregator(self)
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(list(self._current_watched_paths))
        self.startup_manager = StartupManager(app_name, app_executable_path)

        # 2. Устанавливаем начальную иконку
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip(self.tr("Backdraft: Инициализация..."))

        # 3. Создаем контекстное меню
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 4. Соединяем компоненты с новой системой уведомлений
        self.aggregator.aggregated_notification_ready.connect(self._show_native_notification)
        
        # Соединяем сигналы от сервисов с соответствующими слотами-обработчиками в TrayIcon
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        self.watcher.file_watcher_notification.connect(self._on_watcher_notification)
        
        self.history_manager.scan_started.connect(self._on_scan_started)
        self.history_manager.scan_finished.connect(self._on_scan_finished)
        self.history_manager.scan_progress.connect(self._on_scan_progress) # <-- Новый сигнал
        self.history_manager.cleanup_started.connect(self._on_cleanup_started)
        self.history_manager.cleanup_finished.connect(self._on_cleanup_finished)
        self.history_manager.history_notification.connect(self._on_history_notification)

        self.config_manager.startup_changed.connect(self._on_startup_setting_changed)
        self.config_manager.watched_paths_changed.connect(self._on_watched_paths_changed)

        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Применяем начальные настройки
        self._apply_initial_startup_setting()

        # 7. Отложенный запуск
        QTimer.singleShot(0, self._initial_startup_operations)

    # --- Новая система уведомлений ---

    def show_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon, topic: str = ""):
        """
        Центральный диспетчер уведомлений. Передает запрос агрегатору.
        """
        self.aggregator.add_notification(topic, title, message, icon_type)

    @Slot(str, str, QSystemTrayIcon.MessageIcon)
    def _show_native_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        """
        Конечный метод, который непосредственно показывает уведомление.
        Вызывается только агрегатором.
        """
        self.showMessage(title, message, icon_type, 5000)

    # --- Слоты для приема сигналов от сервисов ---

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_config_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """Публичный слот для уведомлений от ConfigManager (из main.py)."""
        self.show_notification(self.tr("Backdraft - Настройки"), msg, icon, topic="settings")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_locale_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """Публичный слот для уведомлений от LocaleManager (из main.py)."""
        self.show_notification(self.tr("Backdraft - Локализация"), msg, icon, topic="settings")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_theme_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """Публичный слот для уведомлений от ThemeManager (из main.py)."""
        self.show_notification(self.tr("Backdraft - Тема"), msg, icon, topic="settings")

    @Slot(str)
    def _on_scan_progress(self, file_name: str):
        """Слот для обработки прогресса сканирования файлов."""
        self.show_notification(
            self.tr("Backdraft - Сканирование"), file_name, QSystemTrayIcon.Information, topic="scan_progress"
        )

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_watcher_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """Слот для уведомлений от FileWatcher."""
        self.show_notification(self.tr("Backdraft - Отслеживание"), msg, icon) # Без темы - показываем сразу
        self._update_monitoring_ui_state()

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_history_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """Слот для общих уведомлений от HistoryManager."""
        self.show_notification(self.tr("Backdraft - История"), msg, icon) # Без темы - показываем сразу
    
    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        """Слот для уведомлений от StartupManager."""
        self.show_notification(self.tr("Backdraft - Автозапуск"), message, icon_type, topic="settings")

    # --- Остальная логика класса (без изменений) ---

    def _initial_startup_operations(self):
        """Выполняет операции, необходимые при первом запуске TrayIcon."""
        self._update_monitoring_ui_state()
        if self._current_watched_paths:
            self.history_manager.start_scan([str(p) for p in self._current_watched_paths])
        else:
            self.show_notification(
                self.tr("Backdraft - Отслеживание"),
                self.tr("Нет настроенных папок для отслеживания. Добавьте их в настройках."),
                QSystemTrayIcon.Information
            )
            self._attempt_start_monitoring()

    def _create_actions(self):
        """Создает и настраивает действия (пункты) для контекстного меню."""
        self.history_action = QAction(self.tr("Открыть историю версий"), self)
        self.history_action.triggered.connect(self._open_history_window)
        self.menu.addAction(self.history_action)

        self.settings_action = QAction(self.tr("Настройки"), self)
        self.settings_action.triggered.connect(self._open_settings_window)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.toggle_watch_action = QAction(self.tr("Приостановить отслеживание"), self)
        self.toggle_watch_action.setCheckable(True)
        self.toggle_watch_action.triggered.connect(self._on_toggle_watch)
        self.menu.addAction(self.toggle_watch_action)

        self.menu.addSeparator()

        self.quit_action = QAction(self.tr("Выход"), self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _open_history_window(self):
        """Создает (если нужно) и показывает окно истории."""
        if self.history_window is None:
            self.history_window = HistoryWindow(
                history_manager=self.history_manager,
                app_icon=self.app_icon
            )
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)

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

    def _attempt_start_monitoring(self):
        """Пытается запустить FileWatcher, если все условия для этого соблюдены."""
        if self._current_watched_paths and \
           not self.history_manager._is_scan_running and \
           not self.history_manager._is_cleanup_running and \
           not self.watcher.is_paused() and \
           not self.watcher.is_running():
            self.watcher.start()
        else:
            self._update_monitoring_ui_state()

    def _update_monitoring_ui_state(self):
        """Централизованно обновляет UI трея на основе текущего состояния."""
        if self.history_manager._is_scan_running:
            self.setIcon(self.icon_generator.get_icon('saving'))
            self.setToolTip(self.tr("Backdraft: Идет сканирование файлов..."))
            self.toggle_watch_action.setText(self.tr("Сканирование..."))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            return

        if self.history_manager._is_cleanup_running:
            self.setIcon(self.icon_generator.get_icon('error'))
            self.setToolTip(self.tr("Backdraft: Идет очистка истории..."))
            self.toggle_watch_action.setText(self.tr("Очистка истории..."))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            return

        if not self._current_watched_paths:
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(self.tr("Backdraft: Нет папок для отслеживания."))
            self.toggle_watch_action.setText(self.tr("Нет папок для отслеживания"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            if self.watcher.is_running():
                self.watcher.stop()
            return

        if self.watcher.is_paused():
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip(self.tr("Backdraft: Мониторинг приостановлен."))
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание"))
            self.toggle_watch_action.setChecked(True)
            self.toggle_watch_action.setEnabled(True)
            if self.watcher.is_running():
                self.watcher.stop()
        elif self.watcher.is_running():
            self.setIcon(self.icon_generator.get_icon('normal'))
            self.setToolTip(self.tr("Backdraft: Мониторинг активен."))
            self.toggle_watch_action.setText(self.tr("Приостановить отслеживание"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True)
        else:
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(self.tr("Backdraft: Мониторинг неактивен."))
            self.toggle_watch_action.setText(self.tr("Мониторинг неактивен"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True)

    @Slot()
    def _on_scan_started(self):
        self._update_monitoring_ui_state()

    @Slot()
    def _on_scan_finished(self):
        self._update_monitoring_ui_state()
        self._attempt_start_monitoring()

    @Slot()
    def _on_cleanup_started(self):
        self._update_monitoring_ui_state()

    @Slot()
    def _on_cleanup_finished(self):
        self._update_monitoring_ui_state()
        self._attempt_start_monitoring()

    def _on_toggle_watch(self, checked: bool):
        if checked:
            self.watcher.stop(user_initiated=True)
        else:
            if self._current_watched_paths:
                self.watcher.start()
            else:
                self.show_notification(
                    self.tr("Backdraft - Мониторинг"),
                    self.tr("Нет папок для отслеживания. Мониторинг не может быть возобновлен."),
                    QSystemTrayIcon.Warning
                )
                self.toggle_watch_action.setChecked(True)
        self._update_monitoring_ui_state()

    @Slot(bool)
    def _on_startup_setting_changed(self, enabled: bool):
        self.startup_manager.update_startup_setting(enabled)

    @Slot(list)
    def _on_watched_paths_changed(self, new_paths_str_list: List[str]):
        valid_new_paths_set = set()
        for path_str in new_paths_str_list:
            path = Path(path_str)
            if path.exists():
                valid_new_paths_set.add(path.resolve())
            else:
                self.show_notification(
                    self.tr("Backdraft - Отслеживание"),
                    self.tr("Внимание: Указанный путь '{0}' не существует и будет проигнорирован.").format(path_str),
                    QSystemTrayIcon.Warning
                )
        
        added_paths_obj = valid_new_paths_set - self._current_watched_paths
        removed_paths_obj = self._current_watched_paths - valid_new_paths_set

        if not added_paths_obj and not removed_paths_obj:
            return

        self.watcher.update_paths([str(p) for p in valid_new_paths_set])
        self._current_watched_paths = valid_new_paths_set

        if removed_paths_obj:
            self.history_manager.start_cleanup([str(p) for p in self._current_watched_paths])
        if added_paths_obj:
            self.history_manager.start_scan([str(p) for p in added_paths_obj])
        
        self._attempt_start_monitoring()

    def _apply_initial_startup_setting(self):
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)

    def _on_quit(self):
        self.show_notification(
            self.app_name,
            self.tr("Приложение закрывается. Останавливаю сервисы..."),
            QSystemTrayIcon.Information
        )
        self.watcher.stop()
        self.history_manager.close()
        self.show_notification(
            self.app_name,
            self.tr("Сервисы остановлены."),
            QSystemTrayIcon.Information
        )