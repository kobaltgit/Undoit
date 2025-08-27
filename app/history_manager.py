# -*- coding: utf-8 -*-
# Управление версиями файлов (хранилищем)
import hashlib
import os
import shutil
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QSystemTrayIcon


class ScanWorker(QObject):
    """
    Рабочий, выполняющий сканирование файлов в отдельном потоке.
    Может быть использован как для первичного, так и для инкрементального сканирования.
    """
    finished = Signal()
    progress = Signal(str)  # Сигнал для отображения текущего сканируемого файла
    scan_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, history_manager, paths_to_scan: List[str]):
        super().__init__()
        self.history_manager = history_manager
        self.paths_to_scan = [Path(p) for p in paths_to_scan]
        self._should_stop = False

    def stop(self):
        """Устанавливает флаг для остановки выполнения."""
        self._should_stop = True

    def run(self):
         self._should_stop = False
         try:
             self.scan_notification.emit(
                 self.tr("Началось фоновое сканирование файлов..."),
                 QSystemTrayIcon.Information
             )
             for path in self.paths_to_scan:
                 if self._should_stop:
                     break
                 if not Path(path).exists():
                     self.scan_notification.emit(
                         self.tr("Путь для сканирования не существует и будет проигнорирован: {0}").format(path),
                         QSystemTrayIcon.Warning
                     )
                     continue
                 for root, _, files in os.walk(Path(path)):
                     if self._should_stop:
                         self.scan_notification.emit(self.tr("Сканирование прервано пользователем."), QSystemTrayIcon.Warning)
                         break
                     for name in files:
                         if self._should_stop:
                             break
                         file_path = Path(root) / name
                         self.progress.emit(file_path.name) # <-- Исправлено: отправляем только имя
                         # 🔒 Перехватываем сбои на отдельном файле, чтобы не уронить весь поток
                         try:
                             self.history_manager.add_initial_version(file_path)
                         except Exception as e:
                             self.scan_notification.emit(
                                 self.tr("Ошибка при обработке {0}: {1}").format(file_path, e),
                                 QSystemTrayIcon.Warning
                             )
             if not self._should_stop:
                 self.scan_notification.emit(self.tr("Сканирование завершено."), QSystemTrayIcon.Information)
         except Exception as e:
             # Глобальный аварийный перехват, чтобы не застревало состояние
             self.scan_notification.emit(self.tr("Критическая ошибка сканирования: {0}").format(e), QSystemTrayIcon.Critical)
         finally:
             self.finished.emit()


class CleanupWorker(QObject):
    """
    Рабочий, выполняющий очистку файлов в отдельном потоке.
    Удаляет из БД записи о файлах, которые больше не находятся в отслеживаемых папках.
    """
    finished = Signal()
    progress = Signal(str)
    cleanup_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, history_manager, watched_paths: List[str]):
        super().__init__()
        self.history_manager = history_manager
        self.watched_paths = [Path(p) for p in watched_paths]
        self._should_stop = False

    def stop(self):
        """Устанавливает флаг для остановки выполнения."""
        self._should_stop = True

    def run(self):
        """Основной метод, выполняющий очистку."""
        self.cleanup_notification.emit(
            self.tr("Началась фоновая очистка истории файлов..."),
            QSystemTrayIcon.Information
        )

        # Вызываем clean_unwatched_files_in_db, который теперь возвращает сообщения
        messages, files_deleted = self.history_manager.clean_unwatched_files_in_db(
            self.watched_paths,
            lambda: self._should_stop # Передаем функцию проверки остановки
        )

        # После возврата из clean_unwatched_files_in_db (и освобождения блокировки БД),
        # безопасно испускаем собранные сообщения.
        for msg, icon_type in messages:
            self.cleanup_notification.emit(msg, icon_type)

        if not self._should_stop:
            if files_deleted > 0:
                self.cleanup_notification.emit(
                    self.tr("Фоновая очистка истории завершена. Удалено {0} записей.").format(files_deleted),
                    QSystemTrayIcon.Information
                )
            else:
                self.cleanup_notification.emit(
                    self.tr("Фоновая очистка истории завершена. Нет файлов для удаления."),
                    QSystemTrayIcon.Information
                )
        else:
            self.cleanup_notification.emit(
                self.tr("Фоновая очистка истории прервана пользователем."),
                QSystemTrayIcon.Warning
            )

        self.finished.emit()


class HistoryManager(QObject):
    """
    Управляет хранилищем версий файлов.
    """
    scan_started = Signal()
    scan_finished = Signal()
    cleanup_started = Signal()
    cleanup_finished = Signal()
    file_list_updated = Signal()
    version_added = Signal(int)
    history_notification = Signal(str, QSystemTrayIcon.MessageIcon)
    scan_progress = Signal(str) # Сигнал о прогрессе сканирования (отправляет имя файла)

    DB_NAME = "metadata.db"
    OBJECTS_DIR = "objects"

    def _calculate_hash(self, file_path: Path) -> str | None:
        """
        Возвращает SHA-256 хеш файла или None при ошибке.
        """
        import hashlib
        try:
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (OSError, IOError):
            return None


    def __init__(self, storage_path: Path, parent=None):
        super().__init__(parent)
        self.storage_path = storage_path
        self.db_path = self.storage_path / self.DB_NAME
        self.objects_path = self.storage_path / self.OBJECTS_DIR

        self._scan_thread = None
        self._scan_worker = None
        self._is_scan_running = False

        self._cleanup_thread = None
        self._cleanup_worker = None
        self._is_cleanup_running = False

        self._db_connection_lock = threading.RLock()

        self._setup_storage()
        self._db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db_connection.execute("PRAGMA foreign_keys = ON")
        self._setup_database()

    def _stop_current_scan_worker(self):
        """Останавливает текущий рабочий поток сканирования, если он активен."""
        if self._is_scan_running and self._scan_worker:
            self._scan_worker.stop()
            if self._scan_thread and self._scan_thread.isRunning():
                self._scan_thread.quit()
                self._scan_thread.wait(2000)

        self._is_scan_running = False
        self._scan_thread = None
        self._scan_worker = None

    def _stop_current_cleanup_worker(self):
        """Останавливает текущий рабочий поток очистки, если он активен."""
        if self._is_cleanup_running and self._cleanup_worker:
            self._cleanup_worker.stop()
            if self._cleanup_thread and self._cleanup_thread.isRunning():
                self._cleanup_thread.quit()
                self._cleanup_thread.wait(2000)

        self._is_cleanup_running = False
        self._cleanup_thread = None
        self._cleanup_worker = None

    def start_scan(self, paths_to_scan: List[str]):
        """
        Запускает сканирование папок в фоновом потоке.
        Если сканирование уже идет, оно будет остановлено и перезапущено с новыми путями.
        """
        if not paths_to_scan:
            self.history_notification.emit(
                self.tr("Сканирование не начато: нет папок для сканирования."),
                QSystemTrayIcon.Information
            )
            return

        self._stop_current_scan_worker()
        self._stop_current_cleanup_worker() # Останавливаем очистку, если она была активна

        self._is_scan_running = True
        self.scan_started.emit()

        self._scan_thread = QThread(self)
        self._scan_worker = ScanWorker(self, paths_to_scan)
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.finished.connect(self._scan_worker.deleteLater)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_worker.finished.connect(self._on_scan_finished_internal)
        self._scan_worker.scan_notification.connect(self.history_notification)
        self._scan_worker.progress.connect(self.scan_progress) # <-- Пробрасываем сигнал наружу

        self._scan_thread.start()

    @Slot()
    def _on_scan_finished_internal(self):
        """Внутренний слот, вызываемый после завершения сканирования."""
        self._is_scan_running = False
        self.file_list_updated.emit() # Обновление UI ТОЛЬКО после завершения сканирования
        self.scan_finished.emit()

    def start_cleanup(self, watched_paths: List[str]):
        """
        Запускает очистку истории файлов в фоновом потоке.
        Если очистка уже идет, она будет остановлена и перезапущена.
        """
        self._stop_current_cleanup_worker()
        self._stop_current_scan_worker() # Останавливаем сканирование, если оно было активно

        self._is_cleanup_running = True
        self.cleanup_started.emit()

        self._cleanup_thread = QThread(self)
        self._cleanup_worker = CleanupWorker(self, watched_paths)
        self._cleanup_worker.moveToThread(self._cleanup_thread)

        self._cleanup_thread.started.connect(self._cleanup_worker.run)
        self._cleanup_worker.finished.connect(self._cleanup_thread.quit)
        self._cleanup_worker.finished.connect(self._cleanup_worker.deleteLater)
        self._cleanup_thread.finished.connect(self._cleanup_thread.deleteLater)
        self._cleanup_worker.finished.connect(self._on_cleanup_finished_internal)
        self._cleanup_worker.cleanup_notification.connect(self.history_notification)

        self._cleanup_thread.start()

    @Slot()
    def _on_cleanup_finished_internal(self):
        """Внутренний слот, вызываемый после завершения очистки."""
        self._is_cleanup_running = False
        self.file_list_updated.emit() # Обновление UI ТОЛЬКО после завершения очистки
        self.cleanup_finished.emit()


    def add_initial_version(self, file_path: Path):
        """
        Добавляет 'нулевую' версию файла во время сканирования.
        Не испускает сигналы UI/уведомления, так как вызывается из рабочего потока.
        """
        with self._db_connection_lock:
            cursor = self._db_connection.cursor()
            cursor.execute("SELECT id FROM tracked_files WHERE original_path = ?", (str(file_path),))
            if cursor.fetchone():
                return

            # _add_version_from_path теперь не испускает сигналы UI/уведомления
            self._add_version_from_path(file_path)

    @Slot(str)
    def add_file_version(self, file_path_str: str):
        """
        Основной метод. Вызывается при изменении файла (из FileWatcher, в его рабочем потоке).
        Испускает сигналы UI и уведомления после сохранения и освобождения блокировки.
        """
        file_path = Path(file_path_str)
        if not file_path.is_file():
            return

        file_hash = self._calculate_hash(file_path)
        if not file_hash:
            # Уведомление об ошибке здесь, если не удалось рассчитать хеш
            self.history_notification.emit(
                self.tr("Ошибка: не удалось рассчитать хеш для файла {0}").format(file_path.name),
                QSystemTrayIcon.Warning
            )
            return

        was_new_file = False
        file_id = -1
        error_message = None # Для сбора сообщений об ошибках

        with self._db_connection_lock:
            cursor = self._db_connection.cursor()
            cursor.execute("""
                SELECT v.sha256_hash FROM versions v
                JOIN tracked_files tf ON v.file_id = tf.id
                WHERE tf.original_path = ?
                ORDER BY v.timestamp DESC LIMIT 1
            """, (str(file_path),))
            last_version = cursor.fetchone()

            if last_version and last_version[0] == file_hash:
                return # Файл не изменился, новую версию не добавляем

            # _add_version_from_path теперь возвращает статус и ID
            result_tuple = self._add_version_from_path(file_path, file_hash)
            if result_tuple:
                was_new_file, file_id = result_tuple
            else:
                error_message = self.tr("Не удалось сохранить версию файла {0}.").format(file_path.name)

        # После выхода из блока `with self._db_connection_lock:`, блокировка свободна.
        # Теперь можно безопасно испускать сигналы GUI.
        if error_message:
            self.history_notification.emit(error_message, QSystemTrayIcon.Critical)
            return

        self.version_added.emit(file_id)
        if was_new_file:
            self.file_list_updated.emit()
            self.history_notification.emit(
                self.tr("Добавлен новый файл для отслеживания: {0}").format(file_path.name),
                QSystemTrayIcon.Information
            )
        else:
            self.history_notification.emit(
                self.tr("Сохранена новая версия файла: {0}").format(file_path.name),
                QSystemTrayIcon.Information
            )

    def get_all_tracked_files(self) -> List[tuple]:
        """
        Возвращает список всех отслеживаемых файлов из БД.
        Сортирует по алфавиту для удобного отображения.
        Возвращает: список кортежей [(id, original_path), ...]
        """
        with self._db_connection_lock:
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
        with self._db_connection_lock:
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

    def _add_version_from_path(self, file_path: Path, precalculated_hash: str = None) -> Optional[Tuple[bool, int]]:
        """
        Внутренний метод для добавления версии файла в хранилище и БД.
        НЕ ИСПУСКАЕТ СИГНАЛЫ UI. Возвращает (was_new_file, file_id) или None в случае ошибки.
        """
        was_new_file = False
        file_id = -1

        file_hash = precalculated_hash or self._calculate_hash(file_path)
        if not file_hash:
            # Вызывающий метод должен обработать ошибку хеширования
            return None

        try:
            file_size = file_path.stat().st_size
        except FileNotFoundError:
            # Вызывающий метод должен обработать ошибку FileNotFoundError
            return None
        except OSError:
            # Вызывающий метод должен обработать ошибку OSError
            return None

        object_subdir = self.objects_path / file_hash[:2]
        object_path = object_subdir / file_hash[2:]
        if not object_path.exists():
            try:
                object_subdir.mkdir(exist_ok=True)
                shutil.copy2(file_path, object_path)
            except IOError:
                # Вызывающий метод должен обработать ошибку IOError при копировании
                return None

        # Блокировка здесь не нужна, так как вызывающий метод уже держит ее
        cursor = self._db_connection.cursor()

        cursor.execute("SELECT id FROM tracked_files WHERE original_path = ?", (str(file_path),))
        file_id_result = cursor.fetchone()

        if not file_id_result:
            was_new_file = True
            cursor.execute("INSERT INTO tracked_files (original_path) VALUES (?)", (str(file_path),))
            file_id = cursor.lastrowid
        else:
            file_id = file_id_result[0]

        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO versions (file_id, timestamp, sha256_hash, file_size) VALUES (?, ?, ?, ?)",
            (file_id, timestamp, file_hash, file_size)
        )
        try:
            self._db_connection.commit()
            return was_new_file, file_id
        except sqlite3.Error:
            self._db_connection.rollback()
            # Вызывающий метод должен обработать ошибку SQLite
            return None

    def clean_unwatched_files_in_db(self,
                                    current_watched_paths_as_paths: List[Path],
                                    should_stop_callback=None) -> Tuple[List[Tuple[str, QSystemTrayIcon.MessageIcon]], int]:
        """
        Удаляет из базы данных записи о файлах, которые больше не находятся
        ни в одной из отслеживаемых папок.
        Не испускает сигналы UI. Возвращает список сообщений и количество удаленных файлов.
        """
        messages = []
        files_deleted_count = 0
        file_ids_to_delete = []

        with self._db_connection_lock:
            cursor = self._db_connection.cursor()
            cursor.execute("SELECT id, original_path FROM tracked_files")
            all_tracked_files = cursor.fetchall()

            for file_id, original_path_str in all_tracked_files:
                if should_stop_callback and should_stop_callback():
                    messages.append((self.tr("Очистка прервана пользователем."), QSystemTrayIcon.Warning))
                    return messages, files_deleted_count # Прерываем выполнение и возвращаем то, что есть

                original_path = Path(original_path_str)
                is_watched = False
                for watched_path in current_watched_paths_as_paths:
                    try:
                        if original_path.resolve().is_relative_to(watched_path.resolve()):
                            is_watched = True
                            break
                    except RuntimeError as e:
                        messages.append((self.tr("Ошибка при проверке пути {0}: {1}").format(original_path_str, e), QSystemTrayIcon.Warning))
                        is_watched = True # Предполагаем, что путь важен, чтобы не удалить его по ошибке
                        break
                    except Exception as e:
                        messages.append((self.tr("Непредвиденная ошибка при проверке пути {0}: {1}").format(original_path_str, e), QSystemTrayIcon.Critical))
                        is_watched = True
                        break

                if not is_watched:
                    file_ids_to_delete.append(file_id)
                    messages.append((self.tr("Найден файл для удаления: {0}").format(original_path.name), QSystemTrayIcon.NoIcon)) # Не показывать как уведомление в трее

            if file_ids_to_delete:
                try:
                    cursor.execute(f"DELETE FROM versions WHERE file_id IN ({','.join(map(str, file_ids_to_delete))})")
                    cursor.execute(f"DELETE FROM tracked_files WHERE id IN ({','.join(map(str, file_ids_to_delete))})")
                    self._db_connection.commit()
                    files_deleted_count = len(file_ids_to_delete)
                    messages.append((self.tr("Удалено {0} записей о файлах, которые больше не отслеживаются.").format(files_deleted_count), QSystemTrayIcon.Information))
                except sqlite3.Error as e:
                    messages.append((self.tr("Ошибка при удалении записей из БД: {0}").format(e), QSystemTrayIcon.Critical))
                    self._db_connection.rollback()
            else:
                messages.append((self.tr("Нет файлов для удаления из истории."), QSystemTrayIcon.Information))

        return messages, files_deleted_count

    def _setup_storage(self):
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.objects_path.mkdir(exist_ok=True)
        except OSError as e:
            self.history_notification.emit(
                self.tr("Ошибка создания папки хранилища: {0}").format(e),
                QSystemTrayIcon.Critical
            )

    def _setup_database(self):
        with self._db_connection_lock:
            try:
                cursor = self._db_connection.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS tracked_files (id INTEGER PRIMARY KEY, original_path TEXT NOT NULL UNIQUE)")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS versions (
                        id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
                        sha256_hash TEXT NOT NULL, file_size INTEGER NOT NULL,
                        FOREIGN KEY (file_id) REFERENCES tracked_files (id) ON DELETE CASCADE
                    )""")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracked_files_path ON tracked_files (original_path)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_file_id ON versions (file_id)")
                self._db_connection.commit()
            except sqlite3.Error as e:
                self.history_notification.emit(
                    self.tr("Ошибка инициализации базы данных: {0}").format(e),
                    QSystemTrayIcon.Critical
                )

    def close(self):
        self._stop_current_scan_worker()
        self._stop_current_cleanup_worker()
        if self._db_connection:
            with self._db_connection_lock:
                self._db_connection.close()
            # Уведомление о закрытии БД, скорее всего, не нужно, так как приложение уже закрывается
            # self.history_notification.emit(
            #     self.tr("Соединение с базой данных закрыто."),
            #     QSystemTrayIcon.Information
            # )
