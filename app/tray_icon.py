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

        # Сохраняем последнее состояние использования хранилища для отображения в тултипе
        self._last_icon_fill_percentage = 0.0 # Процент для иконки (0.0-1.0)
        self._last_formatted_undoit_storage_size = self.tr("Н/Д") # Размер хранилища Undoit
        self._last_formatted_free_disk_space = self.tr("Н/Д") # Свободное место на диске
        self._last_tooltip_percentage = 0.0 # Процент для тултипа (0.0-100.0)

        # 1. Инициализируем сервисы
        self.aggregator = NotificationAggregator(self)
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        self.watcher = FileWatcher(self._current_watched_items)
        self.startup_manager = StartupManager(app_name, app_executable_path)

        # --- Таймер для обработки одиночного клика ---
        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.setInterval(QApplication.doubleClickInterval())
        self.single_click_timer.timeout.connect(self._open_history_window)

        # 2. Устанавливаем иконку и меню
        # Изначально устанавливаем иконку на основе последнего состояния хранилища (0% заполнения)
        self.setIcon(self.icon_generator.get_dynamic_icon(self._last_icon_fill_percentage))
        self.setToolTip(self.tr("Undoit: Инициализация..."))
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 3. Соединяем клики по иконке с действиями
        self.activated.connect(self._on_icon_activated)

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
        self.history_manager.storage_info_updated.connect(self._on_storage_info_updated) # НОВОЕ СОЕДИНЕНИЕ

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

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_icon_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Обрабатывает клики по иконке в системном трее, решая конфликт одиночного и двойного клика."""
        if reason == self.ActivationReason.DoubleClick:
            # При двойном клике останавливаем таймер одиночного клика и открываем настройки
            self.single_click_timer.stop()
            self._open_settings_window()
        elif reason == self.ActivationReason.Trigger:
            # При одиночном клике просто запускаем таймер
            self.single_click_timer.start()
        elif reason == self.ActivationReason.MiddleClick:
            # Средний клик работает как и раньше
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
        """
        Слот для обновления информации о хранилище.
        Обновляет внутренние переменные и вызывает перерисовку иконки/тултипа.
        """
        self._last_icon_fill_percentage = icon_fill_percentage
        self._last_formatted_undoit_storage_size = undoit_storage_size
        self._last_formatted_free_disk_space = free_disk_space
        self._last_tooltip_percentage = tooltip_percentage
        self._update_monitoring_ui_state() # Перерисовываем иконку и тултип


    def _initial_startup_operations(self):
        self._update_monitoring_ui_state()
        if self._current_watched_items:
            self.history_manager.start_scan(self._current_watched_items)
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
                config_manager=self.config_manager, # Добавлен config_manager
                app_icon=self.app_icon
            )
            # При инициализации окна, оно уже вызывает refresh_file_list().
            # Если _all_tracked_files_data (Dict) пуст, то ничего не будет выбрано,
            # но UI будет в корректном состоянии.
            # Теперь refresh_file_list_after_deletion обрабатывает удаление,
            # а refresh_version_list_if_selected обновляет версии для выбранного файла.
            # Если файл удален, files_deleted сигнал вызовет refresh_file_list_after_deletion,
            # которая сама обновит _all_tracked_files_data и UI.
            # Если версия добавлена, version_added сигнал вызовет refresh_version_list_if_selected.
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
            # file_list_updated сигнал больше не нужен, так как refresh_file_list вызывается при инициализации
            # и после удаления файлов через files_deleted.
            self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
        self.history_window.show()
        self.history_window.activateWindow()
        self.history_window.raise_()

    # def _open_history_window(self):
    #     if self.history_window is None:
    #         self.history_window = HistoryWindow(history_manager=self.history_manager, app_icon=self.app_icon)
    #         self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
    #         self.history_manager.file_list_updated.connect(self.history_window.refresh_file_list)
    #     self.history_window.show()
    #     self.history_window.activateWindow()
    #     self.history_window.raise_()

    def _open_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(config_manager=self.config_manager, app_icon=self.app_icon)

            # --- НОВЫЕ СОЕДИНЕНИЯ СИГНАЛОВ ---
            # Когда список отслеживаемых элементов меняется (например, удален файл из истории),
            # обновляем список в окне настроек.
            self.config_manager.watched_items_changed.connect(self.settings_window._load_settings) # <--- ДОБАВЛЕНО

            # Отсоединяем сигнал, когда окно настроек закрывается, чтобы избежать утечек памяти
            self.settings_window.finished.connect(lambda: self.config_manager.watched_items_changed.disconnect(self.settings_window._load_settings)) # <--- ДОБАВЛЕНО

            # Старое соединение для очистки ссылки на окно
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
        """
        Обновляет состояние иконки в трее и всплывающей подсказки
        на основе текущего статуса приложения и использования хранилища.
        """
        base_tooltip = self.tr("Undoit: ") # Используем новое имя

        # Форматирование процента для тултипа: если меньше 0.1%, но не 0, показать "< 0.1%"
        formatted_percentage_for_tooltip = ""
        if self._last_tooltip_percentage > 0 and self._last_tooltip_percentage < 0.1:
            formatted_percentage_for_tooltip = self.tr("< 0.1%")
        else:
            formatted_percentage_for_tooltip = f"{self._last_tooltip_percentage:.1f}%"

        # Строка с информацией о хранилище
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
            # Здесь используем динамическую иконку
            self.setIcon(self.icon_generator.get_dynamic_icon(self._last_icon_fill_percentage))
            self.setToolTip(base_tooltip + self.tr("Мониторинг активен.\n") + storage_info_text)
            self.toggle_watch_action.setText(self.tr("Приостановить отслеживание"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True)
        else: # Состояние "неактивен", но не по причине отсутствия watched_items
            self.setIcon(self.icon_generator.get_icon('inactive')) # Можно также использовать get_dynamic_icon с 0%
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
        """
        Обрабатывает изменения в списке отслеживаемых элементов, включая
        добавление, удаление и изменение исключений.
        """
        old_paths = {item['path'] for item in self._current_watched_items}
        new_paths = {item['path'] for item in new_items}

        added_paths = new_paths - old_paths
        removed_paths = old_paths - new_paths

        only_exclusions_changed = not added_paths and not removed_paths

        # 1. Обновляем внутреннее состояние и передаем полный список наблюдателю
        self._current_watched_items = new_items
        self.watcher.update_items(new_items)

        # 2. Запускаем очистку, если что-то удалили ИЛИ изменили исключения.
        # ИЛИ если изменилось хоть что-то, чтобы гарантировать актуальность БД.
        if removed_paths or only_exclusions_changed or (len(old_paths) != len(new_paths)):
            self.history_manager.start_cleanup(new_items)

        # 3. Запускаем сканирование только для НОВЫХ добавленных элементов
        if added_paths:
            added_items = [item for item in new_items if item['path'] in added_paths]
            self.history_manager.start_scan(added_items)

        # 4. Пытаемся запустить/обновить мониторинг в любом случае
        self._attempt_start_monitoring()

        # 5. Если окно истории открыто, обновляем список файлов
        if self.history_window and self.history_window.isVisible():
            self.history_window.refresh_file_list()

    def _open_help_window(self):
        """Создает (если нужно) и показывает окно помощи."""
        if self.help_window is None:
            self.help_window = HelpWindow(app_icon=self.app_icon)
            # Сбрасываем self.help_window, когда окно закрывается
            self.help_window.finished.connect(lambda: setattr(self, 'help_window', None))

        if not self.help_window.isVisible():
            self.help_window.show()

        self.help_window.activateWindow()
        self.help_window.raise_()

    def _show_about_dialog(self):
        """Показывает стандартный диалог 'О программе'."""
        # TODO: Заменить 'Undoit' на новое имя после рефакторинга
        repo_url = "https://github.com/kobaltgit/Backdraft"
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
    def _on_history_files_deleted(self, deleted_files_info: List[Tuple[int, str]]): # <--- ИЗМЕНЕНО: теперь принимает список кортежей (file_id, original_path_str)
        """
        Слот, вызываемый при удалении файлов из истории.
        Обновляет список отслеживаемых элементов в ConfigManager.
        """
        if not deleted_files_info:
            return

        current_watched_items = self.config_manager.get_watched_items()

        # Собираем set из POSIX-путей удаленных файлов
        deleted_paths_posix = {Path(original_path_str).as_posix() for _, original_path_str in deleted_files_info} # <--- НОВОЕ

        new_watched_items = []
        changed = False
        for item in current_watched_items:
            # Пути в config_manager уже хранятся в POSIX-формате благодаря _normalize_items_for_storage
            if item["path"] in deleted_paths_posix: # <--- ИЗМЕНЕНО: сравнение с новым set'ом
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
            self.config_manager.set_watched_items(new_watched_items) # Это вызовет _on_watched_items_changed, который обновит HistoryWindow

    def _on_quit(self):
        self.show_notification(self.app_name, self.tr("Приложение закрывается. Останавливаю сервисы..."), QSystemTrayIcon.Information)
        self.watcher.stop()
        self.history_manager.close()
        self.show_notification(self.app_name, self.tr("Сервисы остановлены."), QSystemTrayIcon.Information)