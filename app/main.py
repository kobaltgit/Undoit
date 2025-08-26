# -*- coding: utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
import os # <-- Добавлен импорт os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon # <-- Добавлен импорт QIcon

from app.tray_icon import TrayIcon
from app.config_manager import ConfigManager
from app.icon_generator import IconGenerator # <-- Добавлен импорт IconGenerator


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

    if not paths_to_watch:
        desktop_path = str(Path.home() / "Desktop")
        paths_to_watch.append(desktop_path)
        config.set_watched_paths(paths_to_watch)

        QMessageBox.information(
            None, 
            "Добро пожаловать в Backdraft!",
            "Backdraft готов к работе.\n\n"
            "По умолчанию включено отслеживание вашего Рабочего стола. "
            "Вы сможете изменить отслеживаемые папки в настройках."
            # QMessageBox автоматически использует app.windowIcon()
        )

    valid_paths = []
    for path in paths_to_watch:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            print(f"Внимание: Указанный путь не существует и будет проигнорирован: {path}")

    if not valid_paths:
        QMessageBox.critical(
            None,
            "Ошибка Backdraft",
            "Не найдено ни одной существующей папки для отслеживания.\n"
            "Пожалуйста, добавьте папки в настройках."
            # QMessageBox автоматически использует app.windowIcon()
        )
        return 1

    tray_icon = TrayIcon(
        config_manager=config, 
        storage_path=storage_path, 
        paths_to_watch=valid_paths,
        app_name=APP_NAME,
        app_executable_path=APP_EXECUTABLE_PATH,
        app_icon=app_icon # <-- Передача адаптивной иконки приложения
    )
    tray_icon.show()

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
