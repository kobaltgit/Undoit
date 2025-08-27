# -*- coding: utf-8 -*-
# Управление конфигурацией приложения
import json
from pathlib import Path
from typing import Any, List, Set

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon


class ConfigManager(QObject):
    """
    Управляет настройками приложения, читая и сохраняя их в JSON-файл.
    """
    # --- Новые, более конкретные сигналы ---
    # Сигнал об изменении списка отслеживаемых папок.
    watched_paths_changed = Signal(list)
    # Сигнал об изменении темы.
    theme_changed = Signal(str)
    # Сигнал об изменении языка.
    language_changed = Signal(str)
    # Сигнал об изменении настройки автозапуска.
    startup_changed = Signal(bool)

    # Сигнал для отправки уведомлений в трей (остается без изменений).
    config_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    CONFIG_DIR_NAME = "Backdraft"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_data_path = self._get_app_data_path()
        self.config_path = self.app_data_path / self.CONFIG_FILE_NAME

        self._default_settings = {
            "watched_paths": [],
            "theme": "auto",  # auto, light, dark
            "language": "auto", # auto, ru, en
            "launch_on_startup": False,
        }

        # Загружаем настройки или используем дефолтные
        self._settings = self._default_settings.copy()
        self.load()

    def _get_app_data_path(self) -> Path:
        """Возвращает путь к папке данных приложения и создает ее, если нужно."""
        path = Path.home() / "AppData" / "Local" / self.CONFIG_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self):
        """Загружает настройки из config.json."""
        if not self.config_path.exists():
            # При первом запуске просто сохраняем дефолтные настройки, без уведомлений
            self._save_to_file()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Обновляем дефолтные значения загруженными,
                # это сохранит новые ключи, если они появятся в будущих версиях
                self._settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError) as e:
            self.config_notification.emit(
                self.tr("Ошибка загрузки конфигурации: {0}. Будут использованы настройки по умолчанию.").format(e),
                QSystemTrayIcon.Warning
            )
            self._settings = self._default_settings.copy()

    def _save_to_file(self):
        """Внутренний метод для сохранения в файл без отправки сигналов."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            self.config_notification.emit(
                self.tr("Ошибка сохранения конфигурации: {0}").format(e),
                QSystemTrayIcon.Critical
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """
        Устанавливает значение настройки, сохраняет его в файл и испускает
        соответствующий сигнал, если значение действительно изменилось.
        """
        current_value = self._settings.get(key)
        
        # Переменная, чтобы определить, нужно ли сохранять и отправлять сигнал
        has_changed = False

        if key == "watched_paths":
            current_paths_set = self._normalize_paths_to_set(current_value)
            new_paths_set = self._normalize_paths_to_set(value)
            if current_paths_set != new_paths_set:
                # Сохраняем в POSIX-формате для консистентности
                self._settings[key] = [Path(p).as_posix() for p in value]
                has_changed = True
        else:
            if current_value != value:
                self._settings[key] = value
                has_changed = True

        if has_changed:
            self._save_to_file()
            
            # Определяем, какой сигнал нужно отправить, и передаем новое значение
            if key == "watched_paths":
                self.watched_paths_changed.emit(self._settings[key])
            elif key == "theme":
                self.theme_changed.emit(value)
            elif key == "language":
                self.language_changed.emit(value)
            elif key == "launch_on_startup":
                self.startup_changed.emit(value)

    def _normalize_paths_to_set(self, paths: List[str]) -> Set[str]:
        """
        Вспомогательный метод для нормализации списка путей в набор строк
        для сравнения без учета порядка и различий в слэшах.
        """
        if not paths:
            return set()
        normalized_paths = set()
        for p_str in paths:
            try:
                # Resolve() для канонического пути, as_posix() для единообразных слэшей
                normalized_paths.add(Path(p_str).resolve().as_posix())
            except Exception:
                # Если путь невалиден, просто добавляем его как есть (лучше, чем пропустить)
                normalized_paths.add(Path(p_str).as_posix())
        return normalized_paths

    # --- Удобные методы-геттеры и сеттеры ---

    def get_storage_path(self) -> Path:
        """Возвращает путь к папке с хранилищем версий."""
        return self.app_data_path / "storage"

    def get_watched_paths(self) -> List[str]:
        """Возвращает список отслеживаемых папок."""
        return self.get("watched_paths", [])

    def set_watched_paths(self, paths: List[str]):
        """
        Устанавливает список отслеживаемых папок.
        """
        self.set("watched_paths", paths)