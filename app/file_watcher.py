# -*- coding: utf-8 -*-
# Сервис отслеживания файлов
import time
from pathlib import Path
from typing import List, Dict, Set

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class ChangeHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы от watchdog.
    Использует сложный набор правил для фильтрации событий.
    """
    def __init__(self, file_modified_signal: Signal, rules: Dict):
        super().__init__()
        self.file_modified = file_modified_signal
        self._rules = rules

    def _is_path_allowed(self, path_str: str) -> bool:
        """Проверяет, соответствует ли путь правилам отслеживания."""
        try:
            path = Path(path_str).resolve()
        except (OSError, RuntimeError):
            # Если не удается разрешить путь (например, временный файл удален), игнорируем
            return False

        # 1. Прямая проверка отслеживаемых файлов
        if path in self._rules.get('files', set()):
            return True

        # 2. Проверка по папкам и исключениям
        for folder_path, exclusion_paths in self._rules.get('folders', {}).items():
            if path.is_relative_to(folder_path):
                # Файл находится в отслеживаемой папке. Теперь проверим, не исключен ли он.
                is_excluded = any(path.is_relative_to(ex_path) for ex_path in exclusion_paths)
                if not is_excluded:
                    return True # Не исключен, значит, отслеживаем
        
        return False # Не попал ни под одно правило

    def on_modified(self, event: FileSystemEvent):
        if Path(event.src_path).is_file() and not event.is_directory and self._is_path_allowed(event.src_path):
            self.file_modified.emit(event.src_path)

    def on_created(self, event: FileSystemEvent):
        # Отслеживаем новые файлы
        # Необходимо добавить небольшую задержку, чтобы файл успел быть полностью записан.
        # Watchdog может генерировать on_created, когда файл еще не полностью доступен.
        # HistoryManager.add_file_version и так обрабатывает это, но явная проверка не помешает.
        if Path(event.src_path).is_file() and not event.is_directory and self._is_path_allowed(event.src_path):
            self.file_modified.emit(event.src_path)


class FileWatcher(QObject):
    """
    Сервис, который отслеживает изменения в указанных элементах
    в отдельном потоке, используя 'watched_items' с правилами.
    """
    file_modified = Signal(str)
    file_watcher_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, watched_items: List[Dict]):
        super().__init__()
        self._observer = None
        self._is_paused_by_user = False
        self._scheduled_watches = []
        
        # --- Новая логика на основе правил ---
        self._watched_items = watched_items
        self._rules = {}
        self._folders_to_watch = set()
        self._handler = None # Будет создан в _reset_observer_and_schedule

        self._reset_observer_and_schedule(watched_items)

    def _build_rules_and_paths(self, items: List[Dict]):
        """Создает правила фильтрации и список уникальных папок для наблюдения."""
        self._rules = {
            'files': set(),      # {Path('C:/file1.txt'), ...}
            'folders': {}        # {Path('C:/folder1'): {Path('C:/folder1/exclude1'), ...}}
        }
        self._folders_to_watch = set()

        for item in items:
            path_str = item.get("path")
            item_type = item.get("type")
            if not path_str or not item_type: continue

            path = Path(path_str)
            if not path.exists():
                # Уведомление об отсутствующем пути будет отправлено в другом месте
                continue

            resolved_path = path.resolve()
            if item_type == 'file':
                self._rules['files'].add(resolved_path)
                # Добавляем родительскую папку для наблюдения
                self._folders_to_watch.add(resolved_path.parent)
            
            elif item_type == 'folder':
                exclusions = {Path(ex).resolve() for ex in item.get("exclusions", [])}
                self._rules['folders'][resolved_path] = exclusions
                # Добавляем саму папку для наблюдения
                self._folders_to_watch.add(resolved_path)

    def _reset_observer_and_schedule(self, items: List[Dict]):
        """Пересоздает наблюдателя и планирует отслеживание на основе новых правил."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()

        self._watched_items = items
        self._build_rules_and_paths(items)
        
        self._observer = Observer()
        self._handler = ChangeHandler(self.file_modified, self._rules)
        self._scheduled_watches.clear()

        for path in self._folders_to_watch:
            if path.exists():
                watch = self._observer.schedule(self._handler, str(path), recursive=True)
                self._scheduled_watches.append(watch)
            else:
                 self.file_watcher_notification.emit(
                    self.tr("Путь для отслеживания не существует и будет проигнорирован: {0}").format(str(path)),
                    QSystemTrayIcon.Warning
                )

    def update_items(self, new_items: List[Dict]):
        """Обновляет список отслеживаемых элементов."""
        # Простое сравнение словарей достаточно, т.к. ConfigManager уже провел сложную проверку
        if self._watched_items == new_items:
            return

        was_running = self.is_running()
        was_paused_by_user = self._is_paused_by_user

        self._reset_observer_and_schedule(new_items)

        if was_running and not was_paused_by_user:
            self.start()

    def start(self):
        self._is_paused_by_user = False

        if not self._folders_to_watch:
            self.file_watcher_notification.emit(
                self.tr("Не могу начать отслеживание: нет папок для мониторинга."),
                QSystemTrayIcon.Warning
            )
            return

        if not self._observer or not self._observer.is_alive():
            self._reset_observer_and_schedule(self._watched_items)

        try:
            self._observer.start()
            watched_paths_str = ", ".join([str(p) for p in self._folders_to_watch])
            self.file_watcher_notification.emit(
                self.tr("Начинаю отслеживание папок: {0}").format(watched_paths_str),
                QSystemTrayIcon.Information
            )
        except RuntimeError as e:
            self.file_watcher_notification.emit(
                self.tr("Ошибка при запуске отслеживания файлов: {0}").format(e),
                QSystemTrayIcon.Critical
            )

    def stop(self, user_initiated: bool = False):
        if user_initiated:
            self._is_paused_by_user = True

        if self._observer and self._observer.is_alive():
            try:
                self._observer.stop()
                self._observer.join()
                if user_initiated:
                    self.file_watcher_notification.emit(self.tr("Отслеживание остановлено."), QSystemTrayIcon.Information)
            except Exception as e:
                self.file_watcher_notification.emit(self.tr("Ошибка при остановке отслеживания файлов: {0}").format(e), QSystemTrayIcon.Critical)

    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def is_paused(self) -> bool:
        return self._is_paused_by_user

    def get_watched_items(self) -> List[Dict]:
        return self._watched_items