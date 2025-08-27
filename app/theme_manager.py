# -*- coding: utf-8 -*-
# Управление системными темами (светлая/темная)
import os
import sys
import winreg
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import QObject, Slot, Signal # <-- Добавлен импорт Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon # <-- Добавлен импорт QSystemTrayIcon

from app.config_manager import ConfigManager


# Вспомогательная функция для определения пути к ресурсам,
# чтобы работало как при запуске скриптом, так и после компиляции PyInstaller.
def _resource_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу, адаптированный для PyInstaller.
    """
    try:
        # PyInstaller создает временную папку и устанавливает sys._MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Обычный запуск Python-скрипта
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ThemeManager(QObject):
    """
    Управляет загрузкой и применением QSS стилей (темной/светлой темы)
    ко всему приложению, адаптируясь к системной теме Windows или
    выбору пользователя.
    """
    # Сигнал для отправки уведомлений в трей.
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
    theme_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    DARK_THEME_PATH = "resources/styles/dark.qss"
    LIGHT_THEME_PATH = "resources/styles/light.qss"

    def __init__(self, config_manager: ConfigManager, app: QApplication, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.app = app

        # Подключаемся к сигналу изменения настроек
        self.config_manager.settings_changed.connect(self._on_settings_changed)

        # Применяем тему при инициализации
        self._apply_current_theme()

    def _get_system_theme_preference(self) -> str:
        """
        Определяет, какая тема (light/dark) используется в системе Windows.
        Возвращает 'dark' или 'light'. Для других ОС по умолчанию 'light'.
        """
        if sys.platform != 'win32':
            return 'light' # По умолчанию светлая тема для не-Windows

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            # AppsUseLightTheme == 0 означает темную тему
            if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] == 0:
                winreg.CloseKey(key)
                return 'dark'
            else:
                winreg.CloseKey(key)
                return 'light'
        except Exception:
            # В случае ошибки возвращаем светлую тему по умолчанию
            # print("ThemeManager: Ошибка при определении системной темы. Используется светлая тема по умолчанию.")
            self.theme_notification.emit(
                self.tr("Ошибка при определении системной темы. Используется светлая тема по умолчанию."),
                QSystemTrayIcon.Warning
            )
            return 'light'

    def _load_qss(self, qss_file_path: str):
        """
        Загружает QSS файл и применяет его ко всему приложению.
        """
        full_path = _resource_path(qss_file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            self.app.setStyleSheet(qss_content)
            # print(f"ThemeManager: Применена тема из {qss_file_path}")
            self.theme_notification.emit(
                self.tr("Применена тема из {0}").format(Path(qss_file_path).name),
                QSystemTrayIcon.Information
            )
        except FileNotFoundError:
            # print(f"ThemeManager: Ошибка - файл стилей не найден: {qss_file_path}")
            self.theme_notification.emit(
                self.tr("Ошибка - файл стилей не найден: {0}").format(qss_file_path),
                QSystemTrayIcon.Critical
            )
        except Exception as e:
            # print(f"ThemeManager: Ошибка при загрузке или применении стилей {qss_file_path}: {e}")
            self.theme_notification.emit(
                self.tr("Ошибка при загрузке или применении стилей {0}: {1}").format(qss_file_path, e),
                QSystemTrayIcon.Critical
            )

    def _apply_current_theme(self):
        """
        Определяет и применяет текущую тему на основе настроек пользователя
        или системных предпочтений.
        """
        user_theme_setting = self.config_manager.get("theme", "auto")

        if user_theme_setting == "auto":
            system_theme = self._get_system_theme_preference()
            if system_theme == 'dark':
                self._load_qss(self.DARK_THEME_PATH)
            else:
                self._load_qss(self.LIGHT_THEME_PATH)
        elif user_theme_setting == "dark":
            self._load_qss(self.DARK_THEME_PATH)
        elif user_theme_setting == "light":
            self._load_qss(self.LIGHT_THEME_PATH)
        else:
            # print(f"ThemeManager: Неизвестная настройка темы: {user_theme_setting}. Используется светлая тема по умолчанию.")
            self.theme_notification.emit(
                self.tr("Неизвестная настройка темы: {0}. Используется светлая тема по умолчанию.").format(user_theme_setting),
                QSystemTrayIcon.Warning
            )
            self._load_qss(self.LIGHT_THEME_PATH)

    @Slot()
    def _on_settings_changed(self):
        """
        Слот, вызываемый при изменении настроек. Переприменяет тему,
        если настройка темы изменилась.
        """
        # Сначала получаем текущую настройку темы, чтобы избежать лишних перезагрузок QSS
        current_theme_setting_before_apply = self.config_manager.get("theme", "auto")
        self._apply_current_theme()
        current_theme_setting_after_apply = self.config_manager.get("theme", "auto")

        # Отправляем уведомление, только если тема реально изменилась
        if current_theme_setting_before_apply != current_theme_setting_after_apply:
            self.theme_notification.emit(
                self.tr("Настройка темы изменена. Текущая тема: {0}").format(current_theme_setting_after_apply),
                QSystemTrayIcon.Information
            )
        # print(f"ThemeManager: Настройка темы изменена или другие настройки сохранены. Текущая тема: {current_theme_setting}.")
