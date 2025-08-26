# -*- coding: utf-8 -*-
# Управление версиями файлов (хранилищем)
import hashlib
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal, Slot, QThread


class ScannerWorker(QObject):
    """
    Рабочий, выполняющий сканирование файлов в отдельном потоке.
    """
    finished = Signal()
    progress = Signal(str)  # Сигнал для отображения текущего сканируемого файла

    def __init__(self, history_manager, paths_to_scan: List[str]):
        super().__init__()
        self.history_manager = history_manager
        self.paths_to_scan = paths_to_scan

    def run(self):
        """Основной метод, выполняющий сканирование."""
        print("ScannerWorker: Началось фоновое сканирование...")
        for path_str in self.paths_to_scan:
            path = Path(path_str)
            for root, _, files in os.walk(path):
                for name in files:
                    file_path = Path(root) / name
                    self.progress.emit(str(file_path))
                    self.history_manager.add_initial_version(file_path)
        
        print("ScannerWorker: Сканирование завершено.")
        self.finished.emit()


class HistoryManager(QObject):
    """
    Управляет хранилищем версий файлов.
    """
    initial_scan_started = Signal()
    initial_scan_finished = Signal()

    DB_NAME = "metadata.db"
    OBJECTS_DIR = "objects"

    def __init__(self, storage_path: Path, parent=None):
        super().__init__(parent)
        self.storage_path = storage_path
        self.db_path = self.storage_path / self.DB_NAME
        self.objects_path = self.storage_path / self.OBJECTS_DIR

        self._thread = None
        self._worker = None

        self._setup_storage()
        self._db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._setup_database()

    def start_initial_scan(self, paths: List[str]):
        """Запускает первичное сканирование папок в фоновом потоке."""
        self.initial_scan_started.emit()

        self._thread = QThread()
        self._worker = ScannerWorker(self, paths)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self.initial_scan_finished)

        self._thread.start()

    def add_initial_version(self, file_path: Path):
        """Добавляет 'нулевую' версию файла во время сканирования."""
        cursor = self._db_connection.cursor()
        cursor.execute("SELECT id FROM tracked_files WHERE original_path = ?", (str(file_path),))
        if cursor.fetchone():
            return # Файл уже отслеживается, ничего не делаем

        self._add_version_from_path(file_path)
        
    @Slot(str)
    def add_file_version(self, file_path_str: str):
        """Основной метод. Вызывается при изменении файла."""
        file_path = Path(file_path_str)
        if not file_path.is_file():
            return
            
        file_hash = self._calculate_hash(file_path)
        if not file_hash:
            return

        cursor = self._db_connection.cursor()
        cursor.execute("""
            SELECT v.sha256_hash FROM versions v
            JOIN tracked_files tf ON v.file_id = tf.id
            WHERE tf.original_path = ?
            ORDER BY v.timestamp DESC LIMIT 1
        """, (str(file_path),))
        last_version = cursor.fetchone()

        if last_version and last_version[0] == file_hash:
            return

        self._add_version_from_path(file_path, file_hash)

    def get_all_tracked_files(self) -> List[tuple]:
        """
        Возвращает список всех отслеживаемых файлов из БД.
        Сортирует по алфавиту для удобного отображения.
        Возвращает: список кортежей [(id, original_path), ...]
        """
        cursor = self._db_connection.cursor()
        cursor.execute(
            "SELECT id, original_path FROM tracked_files ORDER BY original_path ASC"
        )
        return cursor.fetchall()
    
    def get_versions_for_file(self, file_id: int) -> List[tuple]:
        """
        Возвращает все сохраненные версии для указанного file_id.
        Сортирует от новых к старым.
        Возвращает: список кортежей [(timestamp, sha256_hash, file_size), ...]
        """
        cursor = self._db_connection.cursor()
        cursor.execute("""
            SELECT timestamp, sha256_hash, file_size
            FROM versions
            WHERE file_id = ?
            ORDER BY timestamp DESC
        """, (file_id,))
        return cursor.fetchall()
    
    def get_object_path(self, sha256_hash: str) -> Path | None:
        """
        Возвращает путь к файлу-объекту в хранилище по его хешу.
        """
        object_path = self.objects_path / sha256_hash[:2] / sha256_hash[2:]
        if object_path.exists():
            return object_path
        return None

    def _add_version_from_path(self, file_path: Path, precalculated_hash: str = None):
        """Внутренний метод для добавления версии файла в хранилище и БД."""
        file_hash = precalculated_hash or self._calculate_hash(file_path)
        if not file_hash:
            print(f"Ошибка: Не удалось прочитать файл {file_path}")
            return
            
        file_size = file_path.stat().st_size
        
        object_subdir = self.objects_path / file_hash[:2]
        object_path = object_subdir / file_hash[2:]
        if not object_path.exists():
            object_subdir.mkdir(exist_ok=True)
            shutil.copy2(file_path, object_path)

        cursor = self._db_connection.cursor()
        cursor.execute("INSERT OR IGNORE INTO tracked_files (original_path) VALUES (?)", (str(file_path),))
        cursor.execute("SELECT id FROM tracked_files WHERE original_path = ?", (str(file_path),))
        file_id = cursor.fetchone()[0]

        timestamp = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        cursor.execute(
            "INSERT INTO versions (file_id, timestamp, sha256_hash, file_size) VALUES (?, ?, ?, ?)",
            (file_id, timestamp, file_hash, file_size)
        )
        self._db_connection.commit()
        print(f"Сохранена версия для: {file_path.name} | Хеш: {file_hash[:8]}...")

    def _calculate_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, FileNotFoundError):
            return None

    def _setup_storage(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.objects_path.mkdir(exist_ok=True)

    def _setup_database(self):
        cursor = self._db_connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS tracked_files (id INTEGER PRIMARY KEY, original_path TEXT NOT NULL UNIQUE)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
                sha256_hash TEXT NOT NULL, file_size INTEGER NOT NULL,
                FOREIGN KEY (file_id) REFERENCES tracked_files (id)
            )""")
        self._db_connection.commit()    

    def close(self):
        if self._db_connection:
            self._db_connection.close()