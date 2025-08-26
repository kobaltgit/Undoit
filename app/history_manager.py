# -*- coding: utf-8 -*-
# Управление версиями файлов (хранилищем)
import hashlib
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Slot


class HistoryManager(QObject):
    """
    Управляет хранилищем версий файлов.
    Использует хеширование для дедупликации и базу данных SQLite
    для отслеживания метаданных.
    """
    DB_NAME = "metadata.db"
    OBJECTS_DIR = "objects"

    def __init__(self, storage_path: Path, parent=None):
        super().__init__(parent)
        self.storage_path = storage_path
        self.db_path = self.storage_path / self.DB_NAME
        self.objects_path = self.storage_path / self.OBJECTS_DIR

        self._setup_storage()
        self._db_connection = sqlite3.connect(self.db_path)
        self._setup_database()

    def _setup_storage(self):
        """Создает необходимые директории для хранилища."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.objects_path.mkdir(exist_ok=True)
        print(f"HistoryManager: Хранилище инициализировано в {self.storage_path}")

    def _setup_database(self):
        """Создает таблицы в базе данных, если они не существуют."""
        cursor = self._db_connection.cursor()
        # Таблица для отслеживаемых файлов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_files (
                id INTEGER PRIMARY KEY,
                original_path TEXT NOT NULL UNIQUE
            )
        """)
        # Таблица для версий файлов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                FOREIGN KEY (file_id) REFERENCES tracked_files (id)
            )
        """)
        self._db_connection.commit()
        print("HistoryManager: База данных готова.")

    def _calculate_hash(self, file_path: Path) -> str:
        """Вычисляет SHA256 хеш для файла."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                # Читаем файл по частям, чтобы не загружать в память большие файлы
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, FileNotFoundError):
            return None

    @Slot(str)
    def add_file_version(self, file_path_str: str):
        """
        Основной метод. Вызывается при изменении файла.
        Хеширует файл и сохраняет его, если необходимо.
        """
        file_path = Path(file_path_str)
        if not file_path.is_file():
            return

        file_hash = self._calculate_hash(file_path)
        if not file_hash:
            print(f"Ошибка: Не удалось прочитать файл {file_path}")
            return
            
        file_size = file_path.stat().st_size

        # 1. Проверяем, изменился ли файл по сравнению с последней версией
        cursor = self._db_connection.cursor()
        cursor.execute("""
            SELECT v.sha256_hash FROM versions v
            JOIN tracked_files tf ON v.file_id = tf.id
            WHERE tf.original_path = ?
            ORDER BY v.timestamp DESC LIMIT 1
        """, (str(file_path),))
        last_version = cursor.fetchone()

        if last_version and last_version[0] == file_hash:
            # Содержимое файла не изменилось, ничего не делаем
            return

        # 2. Сохраняем "объект" (содержимое файла), если его еще нет
        object_subdir = self.objects_path / file_hash[:2]
        object_path = object_subdir / file_hash[2:]
        if not object_path.exists():
            object_subdir.mkdir(exist_ok=True)
            shutil.copy2(file_path, object_path)

        # 3. Добавляем запись в базу данных
        # Получаем ID файла или создаем новую запись
        cursor.execute("INSERT OR IGNORE INTO tracked_files (original_path) VALUES (?)", (str(file_path),))
        cursor.execute("SELECT id FROM tracked_files WHERE original_path = ?", (str(file_path),))
        file_id = cursor.fetchone()[0]

        # Добавляем новую версию
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO versions (file_id, timestamp, sha256_hash, file_size) VALUES (?, ?, ?, ?)",
            (file_id, timestamp, file_hash, file_size)
        )
        self._db_connection.commit()
        print(f"Сохранена новая версия для: {file_path.name} | Хеш: {file_hash[:8]}...")

    def close(self):
        """Корректно закрывает соединение с базой данных."""
        if self._db_connection:
            self._db_connection.close()