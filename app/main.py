# -*- coding-utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from app.tray_icon import TrayIcon
from app.config_manager import ConfigManager


def main():
    """Главная функция запуска приложения."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    storage_path = config.get_storage_path()
    paths_to_watch = config.get_watched_paths()

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
        )
        return 1

    tray_icon = TrayIcon(
        config_manager=config, 
        storage_path=storage_path, 
        paths_to_watch=valid_paths
    )
    tray_icon.show()

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())