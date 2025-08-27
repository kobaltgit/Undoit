# -*- coding: utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from app.tray_icon import TrayIcon
from app.config_manager import ConfigManager
from app.icon_generator import IconGenerator
from app.theme_manager import ThemeManager
from app.locale_manager import LocaleManager


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


def main():
    """Главная функция запуска приложения."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    storage_path = config.get_storage_path()
    paths_to_watch = config.get_watched_paths()

    # Флаг для определения, является ли это первым запуском (нет настроенных путей)
    initial_config_empty = not paths_to_watch

    # Если список отслеживаемых папок пуст, добавляем Рабочий стол по умолчанию
    if initial_config_empty:
        desktop_path = str(Path.home() / "Desktop")
        # Проверяем, существует ли путь к рабочему столу, прежде чем добавлять
        if Path(desktop_path).exists():
            paths_to_watch.append(desktop_path)
            config.set_watched_paths(paths_to_watch) # Сохраняем измененный список
        # Если рабочий стол не существует, paths_to_watch останется пустым,
        # и TrayIcon покажет соответствующее уведомление.

    # Инициализируем LocaleManager и применяем язык приложения
    locale_manager = LocaleManager(config_manager=config, app=app)

    # Инициализируем ThemeManager и применяем тему приложения
    theme_manager = ThemeManager(config_manager=config, app=app)

    # Инициализируем IconGenerator
    icon_generator = IconGenerator()

    # Определяем пути к иконкам приложения
    DARK_APP_ICON_PATH = "resources/icons/backdraft_black_app.ico"
    LIGHT_APP_ICON_PATH = "resources/icons/backdraft_light_app.ico"

    # Получаем адаптивную иконку приложения
    app_icon = icon_generator.get_app_icon(DARK_APP_ICON_PATH, LIGHT_APP_ICON_PATH)

    # Устанавливаем глобальную иконку приложения
    app.setWindowIcon(app_icon)

    # Определяем имя приложения и путь к его исполняемому файлу
    APP_NAME = "Backdraft"
    APP_EXECUTABLE_PATH = Path(sys.executable)

    # Создаем TrayIcon, передавая все необходимые менеджеры и данные
    # TrayIcon теперь отвечает за внутреннюю валидацию этих путей и запуск сервисов.
    tray_icon = TrayIcon(
        config_manager=config, 
        storage_path=storage_path, 
        paths_to_watch=paths_to_watch, # Передаем потенциально измененный список
        app_name=APP_NAME,
        app_executable_path=APP_EXECUTABLE_PATH,
        app_icon=app_icon
    )
    tray_icon.show()

    # Соединяем сигналы уведомлений от менеджеров с общим слотом TrayIcon
    config.config_notification.connect(lambda msg, icon: tray_icon.show_notification(
        QApplication.translate("main", "Backdraft - Настройки"), msg, icon
    ))
    locale_manager.locale_notification.connect(lambda msg, icon: tray_icon.show_notification(
        QApplication.translate("main", "Backdraft - Локализация"), msg, icon
    ))
    theme_manager.theme_notification.connect(lambda msg, icon: tray_icon.show_notification(
        QApplication.translate("main", "Backdraft - Тема"), msg, icon
    ))

    # Показываем приветственное сообщение, если это был первый запуск
    # и удалось добавить рабочий стол (т.е. paths_to_watch теперь не пуст).
    # Если paths_to_watch остался пустым, TrayIcon сам уведомит.
    if initial_config_empty and paths_to_watch:
        QMessageBox.information(
            None,
            APP_NAME,
            QApplication.translate(
                "main",
                "Backdraft готов к работе.\n\n"
                "По умолчанию включено отслеживание вашего Рабочего стола. "
                "Вы сможете изменить отслеживаемые папки в настройках."
            )
        )

    # Теперь все уведомления об отсутствующих путях или отсутствии папок для отслеживания
    # будут генерироваться TrayIcon и его менеджерами через системные уведомления.
    # Больше нет необходимости в модальных QMessageBox для этих случаев здесь.

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
