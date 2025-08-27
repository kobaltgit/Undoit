# -*- coding: utf-8 -*-
# Сервис отслеживания файлов
import time
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QSystemTrayIcon # <-- Добавлен импорт QSystemTrayIcon
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
    # Сигнал, который будет испускаться при изменении файла
    # Argument: str - путь к измененному файлу
    file_modified = Signal(str)
    # Сигнал для отправки уведомлений в трей.
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
    file_watcher_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, paths_to_watch: list[str]):
        super().__init__()
        self._paths = paths_to_watch
        self._observer = Observer()
        self._handler = ChangeHandler(self.file_modified)

        # Создаем "наблюдателей" для каждой указанной папки
        self._schedule_paths(paths_to_watch)

    def _schedule_paths(self, paths: list[str]):
        """
        Внутренний метод для планирования отслеживания папок.
        Очищает предыдущие хэндлеры и добавляет новые.
        """
        # Удаляем все существующие запланированные хэндлеры
        for watch in self._observer.emitters:
            self._observer.unschedule(watch)

        # Добавляем новые пути
        for path in paths:
            if Path(path).exists():
                self._observer.schedule(self._handler, path, recursive=True)
            else:
                self.file_watcher_notification.emit(
                    self.tr("Путь для отслеживания не существует и будет проигнорирован: {0}").format(path),
                    QSystemTrayIcon.Warning
                )

    def update_paths(self, new_paths: list[str]):
        """
        Обновляет список отслеживаемых папок.
        Если watcher активен, он будет остановлен и перезапущен с новыми путями.
        """
        if sorted(self._paths) == sorted(new_paths):
            return # Пути не изменились

        was_running = self._observer.is_alive()
        if was_running:
            self.stop()

        self._paths = new_paths
        self._schedule_paths(new_paths)

        if was_running:
            self.start() # Перезапускаем, если был активен

    def start(self):
        """Запускает отслеживание в отдельном потоке."""
        if not self._paths:
            self.file_watcher_notification.emit(
                self.tr("Не могу начать отслеживание: нет папок для мониторинга."),
                QSystemTrayIcon.Warning
            )
            return

        if not self._observer.is_alive():
            try:
                self._observer.start()
                # print(f"FileWatcher: Начинаю отслеживание папок: {self._paths}")
                self.file_watcher_notification.emit(
                    self.tr("Начинаю отслеживание папок: {0}").format(", ".join(self._paths)),
                    QSystemTrayIcon.Information
                )
            except Exception as e:
                self.file_watcher_notification.emit(
                    self.tr("Ошибка при запуске отслеживания файлов: {0}").format(e),
                    QSystemTrayIcon.Critical
                )

    def stop(self):
        """Останавливает отслеживание."""
        if self._observer.is_alive():
            try:
                self._observer.stop()
                self._observer.join() # Дожидаемся полной остановки потока
                # print("FileWatcher: Отслеживание остановлено.")
                self.file_watcher_notification.emit(
                    self.tr("Отслеживание остановлено."),
                    QSystemTrayIcon.Information
                )
            except Exception as e:
                self.file_watcher_notification.emit(
                    self.tr("Ошибка при остановке отслеживания файлов: {0}").format(e),
                    QSystemTrayIcon.Critical
                )
