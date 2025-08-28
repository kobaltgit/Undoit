# -*- coding: utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
import os
from pathlib import Path

# --- Импорты для установки AUMID ---
import ctypes
from ctypes import wintypes

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from app.tray_icon import TrayIcon
from app.config_manager import ConfigManager
from app.icon_generator import IconGenerator
from app.theme_manager import ThemeManager
from app.locale_manager import LocaleManager


# # --- Функция для установки AUMID ---
# def set_app_user_model_id(app_id: str):
#     """
#     Устанавливает AppUserModelID для текущего процесса.
#     Это необходимо для корректного отображения иконки и имени в уведомлениях Windows.
#     """
#     if sys.platform == 'win32':
#         ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

# Вспомогательная функция для определения пути к ресурсам
def _resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main():
    """Главная функция запуска приложения."""
    APP_NAME = "Undoit"
    APP_ID = "Undoit" 
    
    app = QApplication(sys.argv)
    
    # Устанавливаем AUMID ПОСЛЕ создания QApplication.
    # Это вернет правильный заголовок "Undoit" в уведомления.
    # set_app_user_model_id(APP_ID)
    
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    storage_path = config.get_storage_path()
    
    # --- Новая логика для первого запуска ---
    is_first_launch = config.get("is_first_launch", False)
    show_welcome_message = False

    if is_first_launch:
        desktop_path = str(Path.home() / "Desktop")
        if Path(desktop_path).exists():
            desktop_item = {"path": desktop_path, "type": "folder", "exclusions": []}
            # Используем set_watched_items, чтобы сразу записать в конфиг
            config.set_watched_items([desktop_item])
            show_welcome_message = True
        
        # Вне зависимости от того, был ли добавлен Рабочий стол,
        # устанавливаем флаг, что первый запуск прошел.
        config.set("is_first_launch", False)

    # Получаем watched_items уже после потенциального добавления
    watched_items = config.get_watched_items()

    locale_manager = LocaleManager(config_manager=config, app=app)
    theme_manager = ThemeManager(config_manager=config, app=app)
    icon_generator = IconGenerator()

    # --- Используем работающий метод загрузки иконки из файла .ico ---
    DARK_APP_ICON_PATH = "resources/icons/undoit_black_app.ico"
    LIGHT_APP_ICON_PATH = "resources/icons/undoit_light_app.ico"
    app_icon = icon_generator.get_app_icon(DARK_APP_ICON_PATH, LIGHT_APP_ICON_PATH)

    # Устанавливаем эту иконку глобально для приложения
    app.setWindowIcon(app_icon)
    
    APP_EXECUTABLE_PATH = Path(sys.executable)

    tray_icon = TrayIcon(
        config_manager=config,
        storage_path=storage_path,
        watched_items=watched_items,
        app_name=APP_NAME,
        app_executable_path=APP_EXECUTABLE_PATH,
        app_icon=app_icon
    )
    tray_icon.show()

    # Прямые соединения сигналов
    config.config_notification.connect(tray_icon.on_config_notification)
    locale_manager.locale_notification.connect(tray_icon.on_locale_notification)
    theme_manager.theme_notification.connect(tray_icon.on_theme_notification)

    if show_welcome_message:
        QMessageBox.information(
            None,
            APP_NAME,
            QApplication.translate(
                "main",
                "Undoit готов к работе.\n\n"
                "По умолчанию включено отслеживание вашего Рабочего стола. "
                "Вы сможете изменить отслеживаемые папки в настройках."
            )
        )

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())