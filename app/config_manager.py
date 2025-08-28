# -*- coding: utf-8 -*-
# Управление конфигурацией приложения
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon


class ConfigManager(QObject):
    """
    Управляет настройками приложения, читая и сохраняя их в JSON-файл.
    """
    # --- Обновленные сигналы ---
    # Сигнал об изменении списка отслеживаемых элементов.
    watched_items_changed = Signal(list)
    theme_changed = Signal(str)
    language_changed = Signal(str)
    startup_changed = Signal(bool)

    config_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    CONFIG_DIR_NAME = "Undoit"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_data_path = self._get_app_data_path()
        self.config_path = self.app_data_path / self.CONFIG_FILE_NAME

        # --- Новая структура настроек по умолчанию ---
        self._default_settings = {
            "watched_items": [], # Теперь это watched_items
            "theme": "auto",
            "language": "auto",
            "launch_on_startup": False,
            "is_first_launch": True, # Флаг для первого запуска
        }

        self._settings = self._default_settings.copy()
        self.load()

    def _get_app_data_path(self) -> Path:
        """Возвращает путь к папке данных приложения и создает ее, если нужно."""
        path = Path.home() / "AppData" / "Local" / self.CONFIG_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self):
        """Загружает настройки из config.json и выполняет миграцию, если нужно."""
        if not self.config_path.exists():
            self._save_to_file()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                self._settings.update(loaded_settings)
                                
                # Проверяем, есть ли флаг первого запуска. 
                # Если его нет, это старый конфиг, и мы считаем, что первый запуск уже был.
                if "is_first_launch" not in self._settings:
                    self._settings["is_first_launch"] = False
                
                # --- Механизм миграции со старого формата ---
                if "watched_paths" in self._settings:
                    self._migrate_watched_paths_to_items()
                    # После миграции сразу сохраняем, чтобы зафиксировать изменения
                    self._save_to_file()

        except (json.JSONDecodeError, IOError) as e:
            self.config_notification.emit(
                self.tr("Ошибка загрузки конфигурации: {0}. Будут использованы настройки по умолчанию.").format(e),
                QSystemTrayIcon.Warning
            )
            self._settings = self._default_settings.copy()

    def _migrate_watched_paths_to_items(self):
        """Преобразует старый формат 'watched_paths' в новый 'watched_items'."""
        old_paths = self._settings.get("watched_paths", [])
        if not isinstance(old_paths, list):
            # На случай, если данные повреждены
            self._settings["watched_items"] = []
            del self._settings["watched_paths"]
            return
            
        new_items = []
        for path_str in old_paths:
            path = Path(path_str)
            item_type = ""
            if path.is_dir():
                item_type = "folder"
            elif path.is_file():
                item_type = "file"
            else:
                continue # Пропускаем несуществующие пути

            new_items.append({
                "path": path.as_posix(),
                "type": item_type,
                "exclusions": []
            })
        
        self._settings["watched_items"] = new_items
        del self._settings["watched_paths"] # Удаляем старый ключ
        self.config_notification.emit(
            self.tr("Формат конфигурации был обновлен."), QSystemTrayIcon.Information
        )


    def _save_to_file(self):
        """Внутренний метод для сохранения в файл без отправки сигналов."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # Убеждаемся, что старого ключа точно нет перед сохранением
                self._settings.pop("watched_paths", None)
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
        Устанавливает значение настройки, сохраняет и испускает сигнал, если оно изменилось.
        """
        current_value = self._settings.get(key)
        has_changed = False

        if key == "watched_items":
            # Сложное сравнение для списка словарей, игнорируя порядок
            if self._are_items_different(current_value, value):
                # Нормализуем пути перед сохранением
                self._settings[key] = self._normalize_items_for_storage(value)
                has_changed = True
        else:
            if current_value != value:
                self._settings[key] = value
                has_changed = True

        if has_changed:
            self._save_to_file()
            
            if key == "watched_items":
                self.watched_items_changed.emit(self._settings[key])
            elif key == "theme":
                self.theme_changed.emit(value)
            elif key == "language":
                self.language_changed.emit(value)
            elif key == "launch_on_startup":
                self.startup_changed.emit(value)

    def _normalize_items_for_storage(self, items: List[Dict]) -> List[Dict]:
        """Приводит все пути в элементах к POSIX-формату для консистентности."""
        normalized_items = []
        for item in items:
            normalized_item = item.copy()
            normalized_item["path"] = Path(item["path"]).as_posix()
            normalized_item["exclusions"] = sorted([Path(ex).as_posix() for ex in item.get("exclusions", [])])
            normalized_items.append(normalized_item)
        return normalized_items

    def _are_items_different(self, list_a: List[Dict], list_b: List[Dict]) -> bool:
        """
        Сравнивает два списка отслеживаемых элементов без учета порядка.
        """
        if len(list_a) != len(list_b):
            return True

        # Преобразуем каждый словарь в неизменяемый вид для сравнения в множестве
        def make_hashable(d):
            # Сортируем исключения, чтобы порядок не влиял на сравнение
            exclusions = tuple(sorted(d.get("exclusions", [])))
            return (d["path"], d["type"], exclusions)

        set_a = {make_hashable(item) for item in self._normalize_items_for_storage(list_a)}
        set_b = {make_hashable(item) for item in self._normalize_items_for_storage(list_b)}

        return set_a != set_b

    # --- Удобные методы-геттеры и сеттеры ---

    def get_storage_path(self) -> Path:
        """Возврает путь к папке с хранилищем версий."""
        return self.app_data_path / "storage"

    def get_watched_items(self) -> List[Dict]:
        """Возвращает список отслеживаемых элементов."""
        return self.get("watched_items", [])

    def set_watched_items(self, items: List[Dict]):
        """Устанавливает список отслеживаемых элементов."""
        self.set("watched_items", items)