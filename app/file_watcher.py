# -*- coding: utf-8 -*-
# Сервис отслеживания файлов
import time
from PySide6.QtCore import QObject, Signal, QThread
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

    def __init__(self, paths_to_watch: list[str]):
        super().__init__()
        self._paths = paths_to_watch
        self._observer = Observer()
        self._handler = ChangeHandler(self.file_modified)

        # Создаем "наблюдателей" для каждой указанной папки
        for path in self._paths:
            self._observer.schedule(self._handler, path, recursive=True)

    def start(self):
        """Запускает отслеживание в отдельном потоке."""
        if not self._observer.is_alive():
            self._observer.start()
            print(f"FileWatcher: Начинаю отслеживание папок: {self._paths}")

    def stop(self):
        """Останавливает отслеживание."""
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join() # Дожидаемся полной остановки потока
            print("FileWatcher: Отслеживание остановлено.")