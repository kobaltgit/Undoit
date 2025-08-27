# -*- coding: utf-8 -*-
# Сервис отслеживания файлов
import time
from pathlib import Path
from typing import List
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QSystemTrayIcon
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class ChangeHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы от watchdog.
    Перенаправляет события в основной поток через сигналы Qt.
    """
    def __init__(self, file_modified_signal: Signal):
        super().__init__()
        self.file_modified = file_modified_signal

    def on_modified(self, event: FileSystemEvent):
        """
        Вызывается, когда файл или директория были изменены.
        """
        # Нам не нужны события изменения директорий
        if not event.is_directory:
            # Отправляем сигнал с путем к измененному файлу
            self.file_modified.emit(event.src_path)


class FileWatcher(QObject):
    """
    Сервис, который отслеживает изменения в указанных папках
    в отдельном потоке.
    """
    file_modified = Signal(str)
    file_watcher_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, paths_to_watch: list[str]):
        super().__init__()
        self._paths = paths_to_watch
        self._observer = None # Инициализируем None, будет создан в _reset_observer_and_schedule_paths
        self._handler = ChangeHandler(self.file_modified)
        self._is_paused_by_user = False # Флаг для отслеживания паузы, установленной пользователем
        self._scheduled_watches = []

        # Создаем Observer и планируем пути при инициализации
        self._reset_observer_and_schedule_paths(paths_to_watch)

    def _reset_observer_and_schedule_paths(self, paths: list[str] | list[Path]):
        """
        Создает новый экземпляр Observer, останавливает и присоединяет старый, если он есть,
        и планирует отслеживание для нового Observer.
        Это гарантирует, что мы всегда работаем со свежим потоком.
        """
        # Сначала останавливаем и присоединяем старый Observer, если он был
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join() # Дожидаемся полной остановки потока

        # Очищаем все старые хэндлеры, если Observer не был пересоздан
        # (это не должно быть проблемой, если Observer пересоздается, но для надежности)
        if self._observer and self._scheduled_watches:
             for watch in self._scheduled_watches:
                 try:
                     self._observer.unschedule(watch)
                 except Exception:
                     pass
             self._scheduled_watches.clear()

        # Создаем новый Observer
        self._observer = Observer()
        self._paths = [str(Path(p)) for p in paths]

        # Планируем пути для нового Observer
        for path_str in self._paths:
            path = Path(path_str)
            if path.exists():
                watch = self._observer.schedule(self._handler, path, recursive=True)
                self._scheduled_watches.append(watch)
            else:
                self.file_watcher_notification.emit(
                    self.tr("Путь для отслеживания не существует и будет проигнорирован: {0}").format(path_str),
                    QSystemTrayIcon.Warning
                )

    def update_paths(self, new_paths: list[str]):
        """
        Обновляет список отслеживаемых папок.
        Пересоздает Observer и перезапускает его, если пути изменились
        и он не был приостановлен пользователем.
        """
        current_paths_normalized = {Path(p).resolve().as_posix() for p in self._paths}
        new_paths_normalized = {Path(p).resolve().as_posix() for p in new_paths}

        if current_paths_normalized == new_paths_normalized:
            return # Пути по сути не изменились, ничего не делаем

        was_running = self.is_running()
        was_paused_by_user = self._is_paused_by_user

        # Пересоздаем Observer и планируем новые пути.
        # Это включает остановку старого Observer.
        self._reset_observer_and_schedule_paths(new_paths)

        # Перезапускаем только если он был активен ДО обновления ПУТЕЙ,
        # И НЕ БЫЛ ПРИОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ.
        if was_running and not was_paused_by_user:
            self.start() # start() сбросит _is_paused_by_user

        # Если был приостановлен пользователем, то состояние _is_paused_by_user сохраняется.

    def start(self):
        """Запускает отслеживание в отдельном потоке."""
        self._is_paused_by_user = False

        if not self._paths:
            self.file_watcher_notification.emit(
                self.tr("Не могу начать отслеживание: нет папок для мониторинга."),
                QSystemTrayIcon.Warning
            )
            return

        # Если observer уже создавался, но его поток завершён — пересоздаём
        if not self._observer or not self._observer.is_alive():
            self._reset_observer_and_schedule_paths(self._paths)

        try:
            self._observer.start()
            self.file_watcher_notification.emit(
                self.tr("Начинаю отслеживание папок: {0}").format(", ".join(self._paths)),
                QSystemTrayIcon.Information
            )
        except RuntimeError as e:
            self.file_watcher_notification.emit(
                self.tr("Ошибка при запуске отслеживания файлов: {0}").format(e),
                QSystemTrayIcon.Critical
            )

    def stop(self, user_initiated: bool = False):
        """Останавливает отслеживание."""
        if user_initiated:
            self._is_paused_by_user = True # Устанавливаем флаг, если пауза инициирована пользователем

        if self._observer and self._observer.is_alive():
            try:
                self._observer.stop()
                self._observer.join() # Дожидаемся полной остановки потока
                self.file_watcher_notification.emit(
                    self.tr("Отслеживание остановлено."),
                    QSystemTrayIcon.Information
                )
            except Exception as e:
                self.file_watcher_notification.emit(
                    self.tr("Ошибка при остановке отслеживания файлов: {0}").format(e),
                    QSystemTrayIcon.Critical
                )
        # Если observer не существует или не активен, ничего не делаем

    def is_running(self) -> bool:
        """Возвращает True, если FileWatcher активно отслеживает файлы."""
        return self._observer is not None and self._observer.is_alive()

    def is_paused(self) -> bool:
        """Возвращает True, если FileWatcher был приостановлен пользователем."""
        return self._is_paused_by_user

    def get_watched_paths(self) -> List[str]:
        """Возвращает текущий список отслеживаемых путей."""
        return self._paths
