# -*- coding: utf-8 -*-
# Управление автозапуском приложения (только для Windows)
import sys
import os
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal # <-- Добавлен импорт Signal
from PySide6.QtWidgets import QSystemTrayIcon # <-- Добавлен импорт для типа MessageIcon

# pywin32 нужен для создания ярлыков в Windows
try:
    import win32com.client
    import pythoncom
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    print("Внимание: библиотека 'pywin32' не найдена. Функции автозапуска Windows будут недоступны.")
    print("Пожалуйста, установите ее: pip install pywin32")


class StartupManager(QObject):
    """
    Управляет добавлением/удалением приложения в автозапуск Windows.
    Работает только на платформе Windows.
    """
    # Сигнал, испускаемый при завершении операции автозапуска (успех/ошибка)
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
    startup_action_completed = Signal(str, QSystemTrayIcon.MessageIcon) # <-- Объявление нового сигнала

    def __init__(self, app_name: str, app_executable_path: Path, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.app_executable_path = app_executable_path
        self._startup_folder = None

        if sys.platform == 'win32' and PYWIN32_AVAILABLE:
            self._startup_folder = self._get_windows_startup_folder()
            if not self._startup_folder.exists():
                try:
                    self._startup_folder.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    print(f"Ошибка: Не удалось создать папку автозагрузки: {e}")
                    self._startup_folder = None
        elif sys.platform != 'win32':
            # Вместо print, можно сразу испустить сигнал об ошибке, если это необходимо
            # self.startup_action_completed.emit("Функция автозапуска доступна только для Windows.", QSystemTrayIcon.Warning)
            pass # Не выдаем уведомление, т.к. пользователь может быть не на Windows

    def _get_windows_startup_folder(self) -> Path | None:
        """
        Возвращает путь к папке автозагрузки Windows.
        Использует переменную окружения APPDATA.
        """
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return None

    def _get_shortcut_path(self) -> Path | None:
        """Возвращает полный путь к файлу ярлыка."""
        if self._startup_folder:
            return self._startup_folder / f"{self.app_name}.lnk"
        return None

    def is_in_startup(self) -> bool:
        """Проверяет, добавлен ли ярлык приложения в автозагрузку."""
        shortcut_path = self._get_shortcut_path()
        return shortcut_path.exists() if shortcut_path else False

    def add_to_startup(self):
        """Добавляет приложение в автозапуск Windows."""
        if not (sys.platform == 'win32' and PYWIN32_AVAILABLE and self._startup_folder):
            if sys.platform == 'win32' and not PYWIN32_AVAILABLE:
                self.startup_action_completed.emit(
                    "Невозможно добавить в автозагрузку: библиотека 'pywin32' не установлена.",
                    QSystemTrayIcon.Warning
                )
            # Для не-Windows систем не выдаём уведомление, т.к. функция недоступна по определению
            return

        shortcut_path = self._get_shortcut_path()
        if not shortcut_path:
            self.startup_action_completed.emit(
                "Невозможно добавить в автозагрузку: не удалось определить путь для ярлыка.",
                QSystemTrayIcon.Critical
            )
            return

        try:
            pythoncom.CoInitialize() # Инициализация COM-объектов
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(shortcut_path)) # str() для совместимости
            shortcut.TargetPath = str(self.app_executable_path)
            shortcut.WorkingDirectory = str(self.app_executable_path.parent)
            shortcut.Description = f"{self.app_name} - Фоновое отслеживание файлов"
            shortcut.IconLocation = str(self.app_executable_path)
            shortcut.save()

            self.startup_action_completed.emit(
                f"Приложение '{self.app_name}' успешно добавлено в автозагрузку.",
                QSystemTrayIcon.Information
            )
        except Exception as e:
            self.startup_action_completed.emit(
                f"Ошибка при добавлении в автозагрузку: {e}\n"
                "Возможно, потребуются права администратора.",
                QSystemTrayIcon.Critical
            )
        finally:
            pythoncom.CoUninitialize() # Деинициализация COM-объектов

    def remove_from_startup(self):
        """Удаляет приложение из автозапуска Windows."""
        if not (sys.platform == 'win32' and PYWIN32_AVAILABLE and self._startup_folder):
            if sys.platform == 'win32' and not PYWIN32_AVAILABLE:
                self.startup_action_completed.emit(
                    "Невозможно удалить из автозагрузки: библиотека 'pywin32' не установлена.",
                    QSystemTrayIcon.Warning
                )
            return

        shortcut_path = self._get_shortcut_path()
        if shortcut_path and shortcut_path.exists():
            try:
                os.remove(shortcut_path)
                self.startup_action_completed.emit(
                    f"Приложение '{self.app_name}' успешно удалено из автозагрузки.",
                    QSystemTrayIcon.Information
                )
            except OSError as e:
                self.startup_action_completed.emit(
                    f"Ошибка при удалении из автозагрузки: {e}\n"
                    "Возможно, потребуются права администратора.",
                    QSystemTrayIcon.Critical
                )
        else:
            self.startup_action_completed.emit(
                f"Ярлык для '{self.app_name}' не найден в автозагрузке.",
                QSystemTrayIcon.Warning
            )

    @Slot(bool)
    def update_startup_setting(self, enable: bool):
        """
        Слот для обновления состояния автозапуска на основе настройки.
        Вызывается, когда ConfigManager.settings_changed сообщает об изменении
        настройки 'launch_on_startup'.
        """
        if sys.platform != 'win32' or not PYWIN32_AVAILABLE:
            # Не генерируем уведомление здесь, так как пользователь уже мог быть предупрежден,
            # и эта функция просто недоступна на других ОС.
            return

        if enable and not self.is_in_startup():
            self.add_to_startup()
        elif not enable and self.is_in_startup():
            self.remove_from_startup()
        # Если состояние уже соответствует, уведомление не требуется.
        # self.startup_action_completed.emit(f"Состояние автозапуска уже соответствует ({'включено' if enable else 'выключено'}).", QSystemTrayIcon.NoIcon)
