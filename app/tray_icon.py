# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List, Dict

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
                 watched_items: List[Dict], app_name: str, app_executable_path: Path,
                 app_icon: QIcon,
                 parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.app_icon = app_icon
        self.history_window = None
        self.settings_window = None
        self.app_name = app_name
        self._current_watched_items = watched_items

        # 1. Инициализируем сервисы
        self.aggregator = NotificationAggregator(self)
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(self._current_watched_items) # <-- Используем новую структуру
        self.startup_manager = StartupManager(app_name, app_executable_path)

        # 2. Устанавливаем иконку и меню
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip(self.tr("Undoit: Инициализация..."))
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 4. Соединяем компоненты
        self.aggregator.aggregated_notification_ready.connect(self._show_native_notification)
        
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        self.watcher.file_watcher_notification.connect(self._on_watcher_notification)
        
        self.history_manager.scan_started.connect(self._on_scan_started)
        self.history_manager.scan_finished.connect(self._on_scan_finished)
        self.history_manager.scan_progress.connect(self._on_scan_progress)
        self.history_manager.cleanup_started.connect(self._on_cleanup_started)
        self.history_manager.cleanup_finished.connect(self._on_cleanup_finished)
        self.history_manager.history_notification.connect(self._on_history_notification)

        # <-- Подключаемся к обновленному сигналу
        self.config_manager.watched_items_changed.connect(self._on_watched_items_changed)
        self.config_manager.startup_changed.connect(self._on_startup_setting_changed)
        
        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        # 5. Подключаем очистку
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Применяем настройки
        self._apply_initial_startup_setting()

        # 7. Отложенный запуск
        QTimer.singleShot(0, self._initial_startup_operations)

    def show_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon, topic: str = ""):
        self.aggregator.add_notification(topic, title, message, icon_type)

    @Slot(str, str, QSystemTrayIcon.MessageIcon)
    def _show_native_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        self.showMessage(title, message, icon_type, 5000)

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_config_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Настройки"), msg, icon, topic="settings")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_locale_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Локализация"), msg, icon, topic="settings")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def on_theme_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Тема"), msg, icon, topic="settings")

    @Slot(str)
    def _on_scan_progress(self, file_name: str):
        self.show_notification(self.tr("Undoit - Сканирование"), file_name, QSystemTrayIcon.Information, topic="scan_progress")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_watcher_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Отслеживание"), msg, icon)
        self._update_monitoring_ui_state()

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_history_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - История"), msg, icon)
    
    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Автозапуск"), message, icon_type, topic="settings")

    def _initial_startup_operations(self):
        self._update_monitoring_ui_state()
        if self._current_watched_items: # <-- Проверка по новой переменной
            self.history_manager.start_scan(self._current_watched_items) # <-- Передаем новую структуру
        else:
            self.show_notification(
                self.tr("Undoit - Отслеживание"),
                self.tr("Нет настроенных элементов для отслеживания. Добавьте их в настройках."),
                QSystemTrayIcon.Information
            )
            self._attempt_start_monitoring()

    def _create_actions(self):
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
        if self.history_window is None:
            self.history_window = HistoryWindow(history_manager=self.history_manager, app_icon=self.app_icon)
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
        self.history_window.show()
        self.history_window.activateWindow()
        self.history_window.raise_()

    def _open_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(config_manager=self.config_manager, app_icon=self.app_icon)
            self.settings_window.finished.connect(lambda: setattr(self, 'settings_window', None))
        if not self.settings_window.isVisible():
            self.settings_window.exec()
        else:
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    def _attempt_start_monitoring(self):
        if self._current_watched_items and \
           not self.history_manager._is_scan_running and \
           not self.history_manager._is_cleanup_running and \
           not self.watcher.is_paused() and \
           not self.watcher.is_running():
            self.watcher.start()
        else:
            self._update_monitoring_ui_state()

    def _update_monitoring_ui_state(self):
        if self.history_manager._is_scan_running:
            self.setIcon(self.icon_generator.get_icon('saving'))
            self.setToolTip(self.tr("Undoit: Идет сканирование файлов..."))
            self.toggle_watch_action.setText(self.tr("Сканирование..."))
            self.toggle_watch_action.setEnabled(False)
            return

        if self.history_manager._is_cleanup_running:
            self.setIcon(self.icon_generator.get_icon('error'))
            self.setToolTip(self.tr("Undoit: Идет очистка истории..."))
            self.toggle_watch_action.setText(self.tr("Очистка истории..."))
            self.toggle_watch_action.setEnabled(False)
            return

        if not self._current_watched_items: # <-- Проверка по новой переменной
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(self.tr("Undoit: Нет элементов для отслеживания."))
            self.toggle_watch_action.setText(self.tr("Нет элементов для отслеживания"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            if self.watcher.is_running():
                self.watcher.stop()
            return

        if self.watcher.is_paused():
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip(self.tr("Undoit: Мониторинг приостановлен."))
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание"))
            self.toggle_watch_action.setChecked(True)
            self.toggle_watch_action.setEnabled(True)
        elif self.watcher.is_running():
            self.setIcon(self.icon_generator.get_icon('normal'))
            self.setToolTip(self.tr("Undoit: Мониторинг активен."))
            self.toggle_watch_action.setText(self.tr("Приостановить отслеживание"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True)
        else:
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(self.tr("Undoit: Мониторинг неактивен."))
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание"))
            self.toggle_watch_action.setEnabled(True)

    @Slot()
    def _on_scan_started(self): self._update_monitoring_ui_state()
    @Slot()
    def _on_scan_finished(self): self._update_monitoring_ui_state(); self._attempt_start_monitoring()
    @Slot()
    def _on_cleanup_started(self): self._update_monitoring_ui_state()
    @Slot()
    def _on_cleanup_finished(self): self._update_monitoring_ui_state(); self._attempt_start_monitoring()

    def _on_toggle_watch(self, checked: bool):
        if checked:
            self.watcher.stop(user_initiated=True)
        else:
            if self._current_watched_items:
                self.watcher.start()
            else:
                self.show_notification(
                    self.tr("Undoit - Мониторинг"),
                    self.tr("Нет элементов для отслеживания. Мониторинг не может быть возобновлен."),
                    QSystemTrayIcon.Warning
                )
                self.toggle_watch_action.setChecked(True)
        self._update_monitoring_ui_state()

    @Slot(bool)
    def _on_startup_setting_changed(self, enabled: bool):
        self.startup_manager.update_startup_setting(enabled)

    @Slot(list)
    def _on_watched_items_changed(self, new_items: List[Dict]):
        """
        Обрабатывает изменения в списке отслеживаемых элементов, включая
        добавление, удаление и изменение исключений.
        """
        # Используем set из путей для простого определения добавленных/удаленных элементов
        old_paths = {item['path'] for item in self._current_watched_items}
        new_paths = {item['path'] for item in new_items}

        added_paths = new_paths - old_paths
        removed_paths = old_paths - new_paths
        
        # Если сигнал пришел, но пути верхнего уровня не изменились,
        # значит, изменился список исключений внутри одного из элементов.
        only_exclusions_changed = not added_paths and not removed_paths

        # 1. Обновляем внутреннее состояние и передаем полный список наблюдателю
        self._current_watched_items = new_items
        self.watcher.update_items(new_items)
        
        # 2. Запускаем очистку, если что-то удалили ИЛИ изменили исключения.
        #    Это ключевое исправление.
        if removed_paths or only_exclusions_changed:
            self.history_manager.start_cleanup(new_items)
        
        # 3. Запускаем сканирование только для НОВЫХ добавленных элементов
        if added_paths:
            added_items = [item for item in new_items if item['path'] in added_paths]
            self.history_manager.start_scan(added_items)
        
        # 4. Пытаемся запустить/обновить мониторинг в любом случае
        self._attempt_start_monitoring()

    def _apply_initial_startup_setting(self):
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)

    def _on_quit(self):
        self.show_notification(self.app_name, self.tr("Приложение закрывается. Останавливаю сервисы..."), QSystemTrayIcon.Information)
        self.watcher.stop()
        self.history_manager.close()
        self.show_notification(self.app_name, self.tr("Сервисы остановлены."), QSystemTrayIcon.Information)