# -*- coding: utf-8 -*-
# Управление автозапуском приложения (только для Windows)
import sys
import os
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QSystemTrayIcon

# pywin32 нужен для создания ярлыков в Windows
try:
    import win32com.client
    import pythoncom
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    # Вместо print, StartupManager теперь будет испускать сигнал
    # Он будет пойман TrayIcon'ом и показан как уведомление
    # self.startup_action_completed.emit(
    #     "Внимание: библиотека 'pywin32' не найдена. Функции автозапуска Windows будут недоступны. Пожалуйста, установите ее: pip install pywin32",
    #     QSystemTrayIcon.Warning
    # )
    # Однако, это должно быть сделано в конструкторе или в TrayIcon, а не здесь
    # так как self здесь еще нет.
    pass # Оставим как есть, так как print используется для фатальной ошибки импорта

class StartupManager(QObject):
    """
    Управляет добавлением/удалением приложения в автозапуск Windows.
    Работает только на платформе Windows.
    """
    # Сигнал, испускаемый при завершении операции автозапуска (успех/ошибка)
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
    startup_action_completed = Signal(str, QSystemTrayIcon.MessageIcon)

    def __init__(self, app_name: str, app_executable_path: Path, parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.app_executable_path = app_executable_path
        self._startup_folder = None

        if sys.platform == 'win32':
            if PYWIN32_AVAILABLE:
                self._startup_folder = self._get_windows_startup_folder()
                if not self._startup_folder.exists():
                    try:
                        self._startup_folder.mkdir(parents=True, exist_ok=True)
                    except OSError as e:
                        # print(f"Ошибка: Не удалось создать папку автозагрузки: {e}")
                        self.startup_action_completed.emit(
                            self.tr("Ошибка: Не удалось создать папку автозагрузки: {0}").format(e),
                            QSystemTrayIcon.Critical
                        )
                        self._startup_folder = None
            else:
                # Если pywin32 недоступен, сообщаем об этом через сигнал
                self.startup_action_completed.emit(
                    self.tr("Библиотека 'pywin32' не найдена. Функции автозапуска Windows будут недоступны. Пожалуйста, установите ее: pip install pywin32"),
                    QSystemTrayIcon.Warning
                )
        else:
            # Для не-Windows систем не выдаём уведомление, т.к. функция недоступна по определению
            pass

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
                    self.tr("Невозможно добавить в автозагрузку: библиотека 'pywin32' не установлена."),
                    QSystemTrayIcon.Warning
                )
            # Для не-Windows систем не выдаём уведомление, т.к. функция недоступна по определению
            return

        shortcut_path = self._get_shortcut_path()
        if not shortcut_path:
            self.startup_action_completed.emit(
                self.tr("Невозможно добавить в автозагрузку: не удалось определить путь для ярлыка."),
                QSystemTrayIcon.Critical
            )
            return

        try:
            pythoncom.CoInitialize() # Инициализация COM-объектов
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(shortcut_path)) # str() для совместимости
            shortcut.TargetPath = str(self.app_executable_path)
            shortcut.WorkingDirectory = str(self.app_executable_path.parent)
            shortcut.Description = self.tr("{0} - Фоновое отслеживание файлов").format(self.app_name)
            shortcut.IconLocation = str(self.app_executable_path)
            shortcut.save()

            self.startup_action_completed.emit(
                self.tr("Приложение '{0}' успешно добавлено в автозагрузку.").format(self.app_name),
                QSystemTrayIcon.Information
            )
        except Exception as e:
            self.startup_action_completed.emit(
                self.tr("Ошибка при добавлении в автозагрузку: {0}\n"
                        "Возможно, потребуются права администратора.").format(e),
                QSystemTrayIcon.Critical
            )
        finally:
            pythoncom.CoUninitialize() # Деинициализация COM-объектов

    def remove_from_startup(self):
        """Удаляет приложение из автозапуска Windows."""
        if not (sys.platform == 'win32' and PYWIN32_AVAILABLE and self._startup_folder):
            if sys.platform == 'win32' and not PYWIN32_AVAILABLE:
                self.startup_action_completed.emit(
                    self.tr("Невозможно удалить из автозагрузки: библиотека 'pywin32' не установлена."),
                    QSystemTrayIcon.Warning
                )
            return

        shortcut_path = self._get_shortcut_path()
        if shortcut_path and shortcut_path.exists():
            try:
                os.remove(shortcut_path)
                self.startup_action_completed.emit(
                    self.tr("Приложение '{0}' успешно удалено из автозагрузки.").format(self.app_name),
                    QSystemTrayIcon.Information
                )
            except OSError as e:
                self.startup_action_completed.emit(
                    self.tr("Ошибка при удалении из автозагрузки: {0}\n"
                            "Возможно, потребуются права администратора.").format(e),
                    QSystemTrayIcon.Critical
                )
        else:
            self.startup_action_completed.emit(
                self.tr("Ярлык для '{0}' не найден в автозагрузке.").format(self.app_name),
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
