# -*- coding: utf-8 -*-
# Логика иконки в системном трее
from pathlib import Path
from typing import List, Dict, Tuple

from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QMessageBox

from app.config_manager import ConfigManager
from app.file_watcher import FileWatcher
from app.history_manager import HistoryManager
from app.icon_generator import IconGenerator
from app.notification_aggregator import NotificationAggregator
from app.startup_manager import StartupManager
from app.ui.main_window import HistoryWindow
from app.ui.settings_window import SettingsWindow
from app.ui.help_window import HelpWindow


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
        self.help_window = None
        self.app_name = app_name
        self._current_watched_items = watched_items

        self._last_icon_fill_percentage = 0.0
        self._last_formatted_undoit_storage_size = self.tr("Н/Д")
        self._last_formatted_free_disk_space = self.tr("Н/Д")
        self._last_tooltip_percentage = 0.0

        self.aggregator = NotificationAggregator(self)
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(self._current_watched_items)
        self.startup_manager = StartupManager(app_name, app_executable_path)

        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.setInterval(QApplication.doubleClickInterval())
        self.single_click_timer.timeout.connect(self._open_history_window)

        self.setIcon(self.icon_generator.get_dynamic_icon(self._last_icon_fill_percentage))
        self.setToolTip(self.tr("Undoit: Инициализация..."))
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        self.activated.connect(self._on_icon_activated)

        self.aggregator.aggregated_notification_ready.connect(self._show_native_notification)

        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        self.watcher.file_watcher_notification.connect(self._on_watcher_notification)
        self.watcher.rules_reloaded.connect(self._on_rules_reloaded) # НОВЫЙ СИГНАЛ

        self.history_manager.scan_started.connect(self._on_scan_started)
        self.history_manager.scan_finished.connect(self._on_scan_finished)
        self.history_manager.scan_progress.connect(self._on_scan_progress)
        self.history_manager.cleanup_started.connect(self._on_cleanup_started)
        self.history_manager.cleanup_finished.connect(self._on_cleanup_finished)
        self.history_manager.history_notification.connect(self._on_history_notification)
        self.history_manager.storage_info_updated.connect(self._on_storage_info_updated)

        self.config_manager.watched_items_changed.connect(self._on_watched_items_changed)
        self.config_manager.startup_changed.connect(self._on_startup_setting_changed)

        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        self._apply_initial_startup_setting()
        QTimer.singleShot(0, self._initial_startup_operations)

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_icon_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == self.ActivationReason.DoubleClick:
            self.single_click_timer.stop()
            self._open_settings_window()
        elif reason == self.ActivationReason.Trigger:
            self.single_click_timer.start()
        elif reason == self.ActivationReason.MiddleClick:
            if self.toggle_watch_action.isEnabled():
                self.toggle_watch_action.trigger()

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
        self.show_notification(self.tr("Undoit - История"), msg, icon, topic="history_events")

    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        self.show_notification(self.tr("Undoit - Автозапуск"), message, icon_type, topic="settings")

    @Slot(float, str, str, float)
    def _on_storage_info_updated(self, icon_fill_percentage: float, undoit_storage_size: str, free_disk_space: str, tooltip_percentage: float):
        self._last_icon_fill_percentage = icon_fill_percentage
        self._last_formatted_undoit_storage_size = undoit_storage_size
        self._last_formatted_free_disk_space = free_disk_space
        self._last_tooltip_percentage = tooltip_percentage
        self._update_monitoring_ui_state()

    @Slot()
    def _on_rules_reloaded(self):
        """
        Слот, вызываемый при изменении .gitignore файлов.
        Запускает очистку истории для применения новых правил.
        """
        self.history_manager.start_cleanup(
            self._current_watched_items, 
            self.watcher._ignore_manager
        )

    def _initial_startup_operations(self):
        self._update_monitoring_ui_state()
        if self._current_watched_items:
            # Передаем ignore_manager в start_scan
            self.history_manager.start_scan(
                self._current_watched_items, 
                self.watcher._ignore_manager
            )
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
        self.history_manager.files_deleted.connect(self._on_history_files_deleted)
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

        self.help_action = QAction(self.tr("Помощь"), self)
        self.help_action.triggered.connect(self._open_help_window)
        self.menu.addAction(self.help_action)

        self.about_action = QAction(self.tr("О программе"), self)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.menu.addAction(self.about_action)

        self.menu.addSeparator()

        self.quit_action = QAction(self.tr("Выход"), self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _open_history_window(self):
        if self.history_window is None:
            self.history_window = HistoryWindow(
                history_manager=self.history_manager,
                config_manager=self.config_manager,
                app_icon=self.app_icon
            )
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
        self.history_window.show()
        self.history_window.activateWindow()
        self.history_window.raise_()

    def _open_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(config_manager=self.config_manager, app_icon=self.app_icon)
            # Соединяем сигналы
            self.config_manager.watched_items_changed.connect(self.settings_window._load_settings)
            # При закрытии окна вызываем специальный слот для очистки
            self.settings_window.finished.connect(self._on_settings_window_closed)

        if not self.settings_window.isVisible():
            self.settings_window.exec()
        else:
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    @Slot()
    def _on_settings_window_closed(self):
        """Слот для корректной очистки после закрытия окна настроек."""
        if self.settings_window:
            # Сначала отсоединяем сигнал, пока ссылка на окно еще существует
            self.config_manager.watched_items_changed.disconnect(self.settings_window._load_settings)
            # Теперь обнуляем ссылку
            self.settings_window = None

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
        base_tooltip = self.tr("Undoit: ")
        formatted_percentage_for_tooltip = ""
        if self._last_tooltip_percentage > 0 and self._last_tooltip_percentage < 0.1:
            formatted_percentage_for_tooltip = self.tr("< 0.1%")
        else:
            formatted_percentage_for_tooltip = f"{self._last_tooltip_percentage:.1f}%"

        storage_info_text = self.tr(
            "Занято {0} из {1} свободного места ({2})"
        ).format(
            self._last_formatted_undoit_storage_size,
            self._last_formatted_free_disk_space,
            formatted_percentage_for_tooltip
        )

        if self.history_manager._is_scan_running:
            self.setIcon(self.icon_generator.get_icon('saving'))
            self.setToolTip(base_tooltip + self.tr("Идет сканирование файлов...\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Сканирование..."))
            self.toggle_watch_action.setEnabled(False)
            return

        if self.history_manager._is_cleanup_running:
            self.setIcon(self.icon_generator.get_icon('error'))
            self.setToolTip(base_tooltip + self.tr("Идет очистка истории...\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Очистка истории..."))
            self.toggle_watch_action.setEnabled(False)
            return

        if not self._current_watched_items:
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(base_tooltip + self.tr("Нет элементов для отслеживания.\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Нет элементов для отслеживания"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            if self.watcher.is_running():
                self.watcher.stop()
            return

        if self.watcher.is_paused():
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip(base_tooltip + self.tr("Мониторинг приостановлен.\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание"))
            self.toggle_watch_action.setChecked(True)
            self.toggle_watch_action.setEnabled(True)
        elif self.watcher.is_running():
            self.setIcon(self.icon_generator.get_dynamic_icon(self._last_icon_fill_percentage))
            self.setToolTip(base_tooltip + self.tr("Мониторинг активен.\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Приостановить отслеживание"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True)
        else:
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(base_tooltip + self.tr("Мониторинг неактивен.\n") + storage_info_text)
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
        old_paths = {item['path'] for item in self._current_watched_items}
        new_paths = {item['path'] for item in new_items}

        added_paths = new_paths - old_paths
        removed_paths = old_paths - new_paths
        only_exclusions_changed = not added_paths and not removed_paths

        self._current_watched_items = new_items
        self.watcher.update_items(new_items)

        if removed_paths or only_exclusions_changed or (len(old_paths) != len(new_paths)):
            self.history_manager.start_cleanup(
                new_items, 
                self.watcher._ignore_manager
            )

        if added_paths:
            added_items = [item for item in new_items if item['path'] in added_paths]
            self.history_manager.start_scan(
                added_items, 
                self.watcher._ignore_manager
            )

        self._attempt_start_monitoring()

        if self.history_window and self.history_window.isVisible():
            self.history_window.refresh_file_list()

    def _open_help_window(self):
        if self.help_window is None:
            self.help_window = HelpWindow(app_icon=self.app_icon)
            self.help_window.finished.connect(lambda: setattr(self, 'help_window', None))

        if not self.help_window.isVisible():
            self.help_window.show()

        self.help_window.activateWindow()
        self.help_window.raise_()

    def _show_about_dialog(self):
        repo_url = "https://github.com/kobaltgit/Undoit"
        about_text = self.tr(
            "<h3>{app_name}</h3>"
            "<p>Программа для фонового отслеживания и версионирования файлов.</p>"
            "<p>Автор: kobaltgit<br/>"
            "Профиль: <a href='https://github.com/kobaltgit'>github.com/kobaltgit</a><br/>"
            "Репозиторий: <a href='{repo_url}'>{repo_url}</a></p>"
            "<p>Сделано с помощью PySide6 и Qt.</p>"
        ).format(app_name=self.app_name, repo_url=repo_url)

        QMessageBox.about(None, self.tr("О программе {0}").format(self.app_name), about_text)

    def _apply_initial_startup_setting(self):
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)

    @Slot(list)
    def _on_history_files_deleted(self, deleted_files_info: List[Tuple[int, str]]):
        if not deleted_files_info:
            return

        current_watched_items = self.config_manager.get_watched_items()
        deleted_paths_posix = {Path(original_path_str).as_posix() for _, original_path_str in deleted_files_info}

        new_watched_items = []
        changed = False
        for item in current_watched_items:
            if item["path"] in deleted_paths_posix:
                changed = True
                self.show_notification(
                    self.tr("Undoit - Настройки"),
                    self.tr("Файл '{0}' был удален из истории и из списка отслеживания.").format(Path(item["path"]).name),
                    QSystemTrayIcon.Information,
                    topic="settings"
                )
            else:
                new_watched_items.append(item)

        if changed:
            self.config_manager.set_watched_items(new_watched_items)

    def _on_quit(self):
        self.show_notification(self.app_name, self.tr("Приложение закрывается. Останавливаю сервисы..."), QSystemTrayIcon.Information)
        self.watcher.stop()
        self.history_manager.close()
        self.show_notification(self.app_name, self.tr("Сервисы остановлены."), QSystemTrayIcon.Information)