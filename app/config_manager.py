# -*- coding: utf-8 -*-
# Управление конфигурацией приложения
import json
from pathlib import Path
from typing import Any, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon # <-- Добавлен импорт для типа MessageIcon


class ConfigManager(QObject):
    """
    Управляет настройками приложения, читая и сохраняя их в JSON-файл.
    """
    # Сигнал, испускаемый при изменении и сохранении любых настроек
    settings_changed = Signal()
    # Сигнал для отправки уведомлений в трей.
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
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
        # Path.home() -> C:\Users\<ИмяПользователя>
        path = Path.home() / "AppData" / "Local" / self.CONFIG_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self):
        """Загружает настройки из config.json."""
        if not self.config_path.exists():
            # Если файла нет, сохраняем дефолтный конфиг
            self.save()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                # Обновляем дефолтные значения загруженными,
                # это сохранит новые ключи, если они появятся в будущих версиях
                self._settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError) as e:
            # print(f"Ошибка загрузки конфигурации: {e}. Будут использованы настройки по умолчанию.")
            self.config_notification.emit(
                self.tr("Ошибка загрузки конфигурации: {0}. Будут использованы настройки по умолчанию.").format(e),
                QSystemTrayIcon.Warning
            )
            self._settings = self._default_settings.copy()

    def save(self):
        """Сохраняет текущие настройки в config.json."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            self.settings_changed.emit()
            # Уведомление об успешном сохранении можно сделать более детальным,
            # но пока оставим только об изменении настроек.
            # self.config_notification.emit(
            #     self.tr("Настройки успешно сохранены."),
            #     QSystemTrayIcon.Information
            # )
        except IOError as e:
            # print(f"Ошибка сохранения конфигурации: {e}")
            self.config_notification.emit(
                self.tr("Ошибка сохранения конфигурации: {0}").format(e),
                QSystemTrayIcon.Critical
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Устанавливает значение настройки и сразу сохраняет его в файл."""
        # Проверяем, изменилось ли значение, чтобы не сохранять и не испускать сигнал без необходимости
        if self._settings.get(key) != value:
            self._settings[key] = value
            self.save() # save() сам испустит settings_changed.

    # --- Удобные методы-геттеры и сеттеры ---

    def get_storage_path(self) -> Path:
        """Возвращает путь к папке с хранилищем версий."""
        return self.app_data_path / "storage"

    def get_watched_paths(self) -> List[str]:
        """Возвращает список отслеживаемых папок."""
        return self.get("watched_paths", [])

    def set_watched_paths(self, paths: List[str]):
        """Устанавливает список отслеживаемых папок."""
        # Убедимся, что сравниваем списки как множества, если порядок неважен,
        # но для сохранения порядка придерживаемся прямого сравнения.
        # В данном случае, set() достаточно умён, чтобы сравнить без лишних сигналов.
        self.set("watched_paths", paths)
