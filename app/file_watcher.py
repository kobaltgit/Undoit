# -*- coding: utf-8 -*-
# Сервис отслеживания файлов
import os
import time
from pathlib import Path
from typing import List, Dict, Set, Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QSystemTrayIcon
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import pathspec


class IgnoreManager:
    """
    Управляет правилами игнорирования из .gitignore файлов.
    """
    def __init__(self, watch_roots: List[Path]):
        self._watch_roots = watch_roots
        self._ignore_patterns: Dict[Path, pathspec.PathSpec] = {}
        self.reload_ignore_rules()

    def _find_and_parse_gitignore(self, directory: Path) -> Optional[pathspec.PathSpec]:
        """Ищет .gitignore в папке и парсит его."""
        gitignore_path = directory / ".gitignore"
        if gitignore_path.is_file():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    return pathspec.PathSpec.from_lines('gitwildmatch', f)
            except Exception:
                return None
        return None

    def reload_ignore_rules(self):
        """
        Перезагружает все правила .gitignore из отслеживаемых папок и их подпапок.
        """
        self._ignore_patterns.clear()
        for root in self._watch_roots:
            if not root.is_dir():
                continue
            
            # Проверяем сам корень
            spec = self._find_and_parse_gitignore(root)
            if spec:
                self._ignore_patterns[root] = spec
            
            # Ищем .gitignore во всех подпапках
            for dirpath, _, _ in os.walk(root):
                current_dir = Path(dirpath)
                spec = self._find_and_parse_gitignore(current_dir)
                if spec:
                    self._ignore_patterns[current_dir] = spec

    def is_ignored(self, path: Path) -> bool:
        """
        Проверяет, должен ли данный путь быть проигнорирован согласно правилам .gitignore.
        """
        # Ищем наиболее специфичное правило, двигаясь от папки файла вверх к корню
        for parent in [path.parent] + list(path.parents):
            if parent in self._ignore_patterns:
                spec = self._ignore_patterns[parent]
                # pathspec работает с относительными путями от .gitignore
                relative_path = path.relative_to(parent)
                if spec.match_file(str(relative_path)):
                    return True
            # Прекращаем поиск, как только выходим за пределы отслеживаемых корней
            if parent in self._watch_roots:
                break
        return False


class ChangeHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы от watchdog.
    Использует сложный набор правил для фильтрации событий.
    """
    def __init__(self, file_modified_signal: Signal, rules: Dict, ignore_manager: IgnoreManager):
        super().__init__()
        self.file_modified = file_modified_signal
        self._rules = rules
        self._ignore_manager = ignore_manager

    def _is_temp_ide_file(self, path: Path) -> bool:
        """
        Внутренний фильтр для отсеивания короткоживущих временных файлов,
        создаваемых IDE, таких как VS Code.
        """
        try:
            name = path.name
            # 1. Проверяем на отсутствие расширения
            if '.' in name:
                return False
            # 2. Проверяем длину (типичные временные файлы-хеши длинные)
            if len(name) < 20:
                return False
            # 3. Проверяем, состоит ли имя только из HEX-символов
            int(name, 16)
            return True
        except (ValueError, IndexError):
            # Если не удалось преобразовать в int(16), значит, есть не-HEX символы
            return False

    def _is_path_allowed(self, path_str: str) -> bool:
        """Проверяет, соответствует ли путь правилам отслеживания."""
        try:
            path = Path(path_str).resolve()
        except (OSError, RuntimeError):
            return False

        # --- НОВЫЙ "УМНЫЙ" ФИЛЬТР ---
        if self._is_temp_ide_file(path):
            return False

        # Проверяем, не игнорируется ли файл правилами .gitignore
        if self._ignore_manager.is_ignored(path):
            return False

        # Прямая проверка отслеживаемых файлов (уже настроенных в UI)
        if path in self._rules.get('files', set()):
            return True

        # Проверка по папкам и исключениям (из UI)
        for folder_path, exclusion_paths in self._rules.get('folders', {}).items():
            if path.is_relative_to(folder_path):
                is_excluded = any(path.is_relative_to(ex_path) for ex_path in exclusion_paths)
                if not is_excluded:
                    return True
        
        return False

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and Path(event.src_path).is_file():
            if self._is_path_allowed(event.src_path):
                self.file_modified.emit(event.src_path)
            elif Path(event.src_path).name == '.gitignore':
                self.file_modified.emit(event.src_path)


    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and Path(event.src_path).is_file():
            if self._is_path_allowed(event.src_path):
                self.file_modified.emit(event.src_path)
            elif Path(event.src_path).name == '.gitignore':
                 self.file_modified.emit(event.src_path)

class FileWatcher(QObject):
    """
    Сервис, который отслеживает изменения в указанных элементах
    в отдельном потоке, используя 'watched_items' с правилами.
    """
    file_modified = Signal(str)
    file_watcher_notification = Signal(str, QSystemTrayIcon.MessageIcon)
    rules_reloaded = Signal() # НОВЫЙ СИГНАЛ

    def __init__(self, watched_items: List[Dict]):
        super().__init__()
        self._observer = None
        self._is_paused_by_user = False
        self._scheduled_watches = []
        
        self._watched_items = watched_items
        self._rules = {}
        self._folders_to_watch = set()
        self._handler = None
        self._ignore_manager: Optional[IgnoreManager] = None

        # --- НОВЫЙ обработчик для изменений в .gitignore ---
        self.file_modified.connect(self._handle_gitignore_changes)

        self._reset_observer_and_schedule(watched_items)

    @Slot(str)
    def _handle_gitignore_changes(self, path_str: str):
        """
        Если измененный файл - .gitignore, перезагружает правила.
        """
        if Path(path_str).name == '.gitignore':
            if self._ignore_manager:
                self._ignore_manager.reload_ignore_rules()
                self.rules_reloaded.emit() # Сообщаем, что правила изменились
                self.file_watcher_notification.emit(
                    self.tr("Правила исключений (.gitignore) были обновлены."),
                    QSystemTrayIcon.Information
                )

    def _build_rules_and_paths(self, items: List[Dict]):
        """Создает правила фильтрации и список уникальных папок для наблюдения."""
        self._rules = {
            'files': set(),
            'folders': {}
        }
        self._folders_to_watch = set()

        for item in items:
            path_str = item.get("path")
            item_type = item.get("type")
            if not path_str or not item_type: continue

            path = Path(path_str)
            if not path.exists():
                continue

            resolved_path = path.resolve()
            if item_type == 'file':
                self._rules['files'].add(resolved_path)
                self._folders_to_watch.add(resolved_path.parent)
            
            elif item_type == 'folder':
                exclusions = {Path(ex).resolve() for ex in item.get("exclusions", [])}
                self._rules['folders'][resolved_path] = exclusions
                self._folders_to_watch.add(resolved_path)

    def _reset_observer_and_schedule(self, items: List[Dict]):
        """Пересоздает наблюдателя и планирует отслеживание на основе новых правил."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()

        self._watched_items = items
        self._build_rules_and_paths(items)

        # --- НОВОЕ: Инициализация IgnoreManager ---
        watch_roots_for_ignore = [p for p in self._rules['folders'].keys()]
        self._ignore_manager = IgnoreManager(watch_roots_for_ignore)
        
        self._observer = Observer()
        self._handler = ChangeHandler(self.file_modified, self._rules, self._ignore_manager)
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