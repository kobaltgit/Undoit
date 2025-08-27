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

        # Сохраняем текущий список отслеживаемых путей для сравнения при изменениях
        # Нормализуем сразу, чтобы избежать проблем со слэшами и регистром
        self._current_watched_paths: Set[Path] = {Path(p).resolve() for p in paths_to_watch if Path(p).exists()}


        # 1. Инициализируем сервисы
        self.icon_generator = IconGenerator()
        self.history_manager = HistoryManager(storage_path)
        # FileWatcher инициализируется с текущими путями.
        # Он не запускается автоматически, а ждет явного вызова start()
        self.watcher = FileWatcher(list(self._current_watched_paths))

        self.startup_manager = StartupManager(app_name, app_executable_path)

        # 2. Устанавливаем начальную иконку для трея (временная)
        self.setIcon(self.icon_generator.get_icon('normal'))
        self.setToolTip(self.tr("Backdraft: Инициализация..."))

        # 3. Создаем контекстное меню
        self.menu = QMenu()
        self._create_actions()
        self.setContextMenu(self.menu)

        # 4. Соединяем компоненты
        self.watcher.file_modified.connect(self.history_manager.add_file_version)
        # Сигнал от watcher о его запуске/остановке/ошибке также обновляет UI
        # _on_watcher_notification будет вызывать _update_monitoring_ui_state()
        self.watcher.file_watcher_notification.connect(self._on_watcher_notification)

        # Соединяем сигналы сканирования HistoryManager со слотами TrayIcon
        self.history_manager.scan_started.connect(self._on_scan_started)
        self.history_manager.scan_finished.connect(self._on_scan_finished)
        # Соединяем сигналы очистки HistoryManager со слотами TrayIcon
        self.history_manager.cleanup_started.connect(self._on_cleanup_started)
        self.history_manager.cleanup_finished.connect(self._on_cleanup_finished)
        # Соединяем сигнал уведомлений HistoryManager со слотом TrayIcon
        self.history_manager.history_notification.connect(lambda msg, icon: self.show_notification(
            self.tr("Backdraft - История"), msg, icon
        ))

        self.config_manager.settings_changed.connect(self._on_settings_changed)
        self.startup_manager.startup_action_completed.connect(self._on_startup_action_completed)

        # 5. Подключаем очистку ресурсов при выходе
        app = QApplication.instance()
        app.aboutToQuit.connect(self._on_quit)

        # 6. Применяем текущие настройки автозапуска при старте
        self._apply_initial_startup_setting()

        # 7. Инициируем первичное обновление UI и запуск сканирования/мониторинга.
        # Используем QTimer.singleShot(0) для отложенного вызова, чтобы все компоненты
        # TrayIcon успели полностью инициализироваться.
        QTimer.singleShot(0, self._initial_startup_operations)


    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_watcher_notification(self, msg: str, icon: QSystemTrayIcon.MessageIcon):
        """
        Слот для обработки уведомлений от FileWatcher.
        Показывает уведомление и затем обновляет UI.
        """
        self.show_notification(self.tr("Backdraft - Отслеживание"), msg, icon)
        self._update_monitoring_ui_state() # Важно обновить UI после уведомления от watcher


    def _initial_startup_operations(self):
        """Выполняет операции, необходимые при первом запуске TrayIcon."""
        # Устанавливаем корректное начальное состояние UI
        self._update_monitoring_ui_state()

        # Если есть папки для отслеживания
        if self._current_watched_paths:
            # Запускаем первичное сканирование.
            # Попытка запуска мониторинга произойдет после завершения сканирования.
            self.history_manager.start_scan(list(self._current_watched_paths))
        else:
            # Если папок нет, просто уведомляем и пытаемся запустить мониторинг (что не удастся,
            # но _attempt_start_monitoring() и _update_monitoring_ui_state() корректно это отобразят).
            self.show_notification(
                self.tr("Backdraft - Отслеживание"),
                self.tr("Нет настроенных папок для отслеживания. Добавьте их в настройках."),
                QSystemTrayIcon.Information
            )
            # Попытка запустить мониторинг даже при отсутствии папок,
            # чтобы UI корректно отобразил состояние "неактивен".
            self._attempt_start_monitoring()


    @Slot(str, str, QSystemTrayIcon.MessageIcon)
    def show_notification(self, title: str, message: str, icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information):
        """
        Показывает всплывающее уведомление в системном трее.
        Это общий слот для всех уведомлений.
        """
        self.showMessage(title, message, icon_type, 5000)

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
            # Переподключаем refresh_version_list_if_selected, он был нужен.
            # Напрямую от history_manager.version_added (только для единичных изменений файла, не сканирования)
            self.history_manager.version_added.connect(self.history_window.refresh_version_list_if_selected)
            # А file_list_updated вызывается после сканирования/очистки, поэтому обновляем весь список
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
        """
        Пытается запустить FileWatcher, если все условия для этого соблюдены.
        Этот метод активно ИНИЦИИРУЕТ запуск.
        """
        # Условия для запуска:
        # 1. Есть папки для отслеживания
        # 2. Не идет сканирование
        # 3. Не идет очистка
        # 4. Не приостановлено пользователем
        # 5. FileWatcher еще не запущен
        if self._current_watched_paths and \
           not self.history_manager._is_scan_running and \
           not self.history_manager._is_cleanup_running and \
           not self.watcher.is_paused() and \
           not self.watcher.is_running():

            self.watcher.start() # Это вызовет _on_watcher_notification -> _update_monitoring_ui_state
        else:
            # Если не удалось запустить, просто обновляем UI, чтобы он отразил текущее состояние
            self._update_monitoring_ui_state()


    def _update_monitoring_ui_state(self):
        """
        Централизованно обновляет иконку трея, подсказку и состояние кнопки
        "Приостановить/Возобновить отслеживание" на основе текущего состояния всех компонентов.
        Этот метод только ОТРАЖАЕТ состояние, он не ИНИЦИИРУЕТ запуск/остановку сервисов.
        """
        # Приоритет отдаем активным фоновым операциям
        if self.history_manager._is_scan_running:
            self.setIcon(self.icon_generator.get_icon('saving'))
            self.setToolTip(self.tr("Backdraft: Идет сканирование файлов..."))
            self.toggle_watch_action.setText(self.tr("Сканирование..."))
            self.toggle_watch_action.setChecked(False) # Кнопка не должна быть отмечена
            self.toggle_watch_action.setEnabled(False) # Отключаем переключатель во время сканирования
            return

        if self.history_manager._is_cleanup_running:
            self.setIcon(self.icon_generator.get_icon('error')) # Индикация очистки
            self.setToolTip(self.tr("Backdraft: Идет очистка истории..."))
            self.toggle_watch_action.setText(self.tr("Очистка истории..."))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            return

        # Если нет активных папок для отслеживания
        if not self._current_watched_paths:
            self.setIcon(self.icon_generator.get_icon('inactive')) # Нейтральная иконка
            self.setToolTip(self.tr("Backdraft: Нет папок для отслеживания."))
            self.toggle_watch_action.setText(self.tr("Нет папок для отслеживания"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(False)
            # В этом состоянии watcher должен быть остановлен.
            if self.watcher.is_running():
                self.watcher.stop() # Остановка не инициирована пользователем
            return

        # Нормальное состояние мониторинга (есть папки)
        if self.watcher.is_paused():
            self.setIcon(self.icon_generator.get_icon('paused'))
            self.setToolTip(self.tr("Backdraft: Мониторинг приостановлен."))
            self.toggle_watch_action.setText(self.tr("Возобновить отслеживание"))
            self.toggle_watch_action.setChecked(True) # Отмечено, если приостановлено
            self.toggle_watch_action.setEnabled(True)
            # Если watcher почему-то работает, но отмечен как пауза - останавливаем его
            if self.watcher.is_running():
                self.watcher.stop() # Остановка не инициирована пользователем
        elif self.watcher.is_running():
            self.setIcon(self.icon_generator.get_icon('normal'))
            self.setToolTip(self.tr("Backdraft: Мониторинг активен."))
            self.toggle_watch_action.setText(self.tr("Приостановить отслеживание"))
            self.toggle_watch_action.setChecked(False) # Не отмечено, если активно
            self.toggle_watch_action.setEnabled(True)
        else: # watcher.is_running() == False и watcher.is_paused() == False (активно не запущен, но и не приостановлен пользователем)
            self.setIcon(self.icon_generator.get_icon('inactive'))
            self.setToolTip(self.tr("Backdraft: Мониторинг неактивен."))
            self.toggle_watch_action.setText(self.tr("Мониторинг неактивен"))
            self.toggle_watch_action.setChecked(False)
            self.toggle_watch_action.setEnabled(True) # Можно попытаться запустить (через _attempt_start_monitoring)


    @Slot()
    def _on_scan_started(self):
        """Слот, вызываемый при начале сканирования."""
        self._update_monitoring_ui_state()

    @Slot()
    def _on_scan_finished(self):
        """Слот, вызываемый по завершении сканирования."""
        self._update_monitoring_ui_state()
        # После завершения сканирования, пытаемся запустить мониторинг
        self._attempt_start_monitoring()


    @Slot()
    def _on_cleanup_started(self):
        """Слот, вызываемый при начале очистки."""
        self._update_monitoring_ui_state()

    @Slot()
    def _on_cleanup_finished(self):
        """Слот, вызываемый по завершении очистки."""
        self._update_monitoring_ui_state()
        # После завершения очистки, пытаемся запустить мониторинг
        self._attempt_start_monitoring()


    def _on_toggle_watch(self, checked: bool):
        """Слот для приостановки/возобновления отслеживания файлов."""
        if checked: # Кнопка отмечена -> значит, сейчас "Возобновить", а было "Приостановить"
            # Значит, нужно приостановить отслеживание
            self.watcher.stop(user_initiated=True)
            # Уведомление генерируется _on_watcher_notification
        else: # Кнопка не отмечена -> значит, сейчас "Приостановить", а было "Возобновить"
            # Значит, нужно возобновить отслеживание
            if self._current_watched_paths:
                self.watcher.start() # Это вызовет _on_watcher_notification
            else:
                # Если папок нет, не можем возобновить, возвращаем кнопку в "приостановлено"
                self.show_notification(
                    self.tr("Backdraft - Мониторинг"),
                    self.tr("Нет папок для отслеживания. Мониторинг не может быть возобновлен."),
                    QSystemTrayIcon.Warning
                )
                self.toggle_watch_action.setChecked(True) # Откатываем состояние кнопки

        self._update_monitoring_ui_state() # Обновляем UI после изменения состояния


    @Slot()
    def _on_settings_changed(self):
        """
        Слот, вызываемый при изменении любых настроек в ConfigManager.
        Проверяет настройку 'launch_on_startup' и соответствующим образом
        обновляет автозапуск через StartupManager, а также обновляет
        список отслеживаемых папок.
        """
        # 1. Обновление автозапуска
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)

        # 2. Обновление списка отслеживаемых папок
        new_watched_paths_list_str = self.config_manager.get_watched_paths()

        valid_new_paths_set = set()
        for path_str in new_watched_paths_list_str:
            path = Path(path_str)
            if path.exists():
                valid_new_paths_set.add(path.resolve()) # Нормализуем для корректного сравнения
            else:
                self.show_notification(
                    self.tr("Backdraft - Отслеживание"),
                    self.tr("Внимание: Указанный путь '{0}' не существует и будет проигнорирован.").format(path_str),
                    QSystemTrayIcon.Warning
                )

        added_paths_obj = valid_new_paths_set - self._current_watched_paths
        removed_paths_obj = self._current_watched_paths - valid_new_paths_set

        added_paths_str = [str(p) for p in added_paths_obj]

        # Если пути изменились, обновляем watcher и запускаем сканирование/очистку
        if added_paths_obj or removed_paths_obj:
            # Обновляем watcher с новым полным списком.
            self.watcher.update_paths(list(valid_new_paths_set))

            # Сохраняем новый актуальный список нормализованных путей
            self._current_watched_paths = valid_new_paths_set

            if removed_paths_obj:
                # Запускаем очистку.
                self.history_manager.start_cleanup(list(self._current_watched_paths))

            if added_paths_obj:
                # Запускаем сканирование только для новых добавленных папок
                self.history_manager.start_scan(added_paths_str)

        # После всех операций пытаемся запустить мониторинг.
        # Это также обновит UI.
        self._attempt_start_monitoring()


    @Slot(str, QSystemTrayIcon.MessageIcon)
    def _on_startup_action_completed(self, message: str, icon_type: QSystemTrayIcon.MessageIcon):
        """
        Слот, вызываемый по завершении операции StartupManager (добавление/удаление в автозапуск).
        Показывает всплывающее уведомление.
        """
        self.show_notification(
            self.tr("Backdraft - Автозапуск"),
            message,
            icon_type,
        )

    def _apply_initial_startup_setting(self):
        """Применяет настройку автозапуска при первом старте TrayIcon."""
        enable_startup = self.config_manager.get("launch_on_startup", False)
        self.startup_manager.update_startup_setting(enable_startup)

    def _on_quit(self):
        """Слот, который вызывается перед закрытием приложения для очистки."""
        self.show_notification(
            self.app_name,
            self.tr("Приложение закрывается. Останавливаю сервисы..."),
            QSystemTrayIcon.Information
        )
        self.watcher.stop() # Остановка без user_initiated
        self.history_manager.close()
        self.show_notification(
            self.app_name,
            self.tr("Сервисы остановлены."),
            QSystemTrayIcon.Information
        )
