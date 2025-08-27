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
    tray_icon = TrayIcon(
        config_manager=config, 
        storage_path=storage_path, 
        paths_to_watch=valid_paths if 'valid_paths' in locals() else paths_to_watch, # Передаем сюда начальный список
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

    # Проверяем пути для отслеживания и показываем модальные сообщения при необходимости
    # Этот блок остается после инициализации tray_icon,
    # чтобы уведомления об ошибках в этом блоке могли быть показаны через трей.
    valid_paths = []
    initial_paths_processed = False
    if not paths_to_watch:
        desktop_path = str(Path.home() / "Desktop")
        paths_to_watch.append(desktop_path)
        config.set_watched_paths(paths_to_watch) # Сохраняем измененный список
        initial_paths_processed = True

        QMessageBox.information(
            None,
            APP_NAME, # Заголовок QMessageBox теперь использует APP_NAME
            # Сообщение для перевода
            QApplication.translate(
                "main",
                "Backdraft готов к работе.\n\n"
                "По умолчанию включено отслеживание вашего Рабочего стола. "
                "Вы сможете изменить отслеживаемые папки в настройках."
            )
        )

    for path in paths_to_watch:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            print(f"Внимание: Указанный путь не существует и будет проигнорирован: {path}")
            tray_icon.show_notification(
                QApplication.translate("main", "Backdraft - Отслеживание"),
                QApplication.translate("main", "Внимание: Указанный путь не существует и будет проигнорирован: {0}").format(path),
                QSystemTrayIcon.Warning
            )

    if not valid_paths and not initial_paths_processed: # Показываем критическое сообщение, если нет валидных путей и не было первоначальной настройки
        QMessageBox.critical(
            None,
            APP_NAME, # Заголовок QMessageBox теперь использует APP_NAME
            # Сообщение для перевода
            QApplication.translate(
                "main",
                "Не найдено ни одной существующей папки для отслеживания.\n"
                "Пожалуйста, добавьте папки в настройках."
            )
        )
        return 1

    # Обновляем paths_to_watch в tray_icon после проверки валидности
    # NOTE: Это немного неидеально, так как watcher уже инициализирован
    # с исходным списком. В реальном приложении лучше передавать актуальный
    # список в watcher после его инициализации или переинициализировать watcher.
    # Но для текущей структуры, где watcher создается в TrayIcon,
    # это временное решение.
    # Более надежное решение:
    # 1. Передавать только config_manager в TrayIcon
    # 2. TrayIcon будет слушать config_manager.settings_changed
    # 3. В _on_settings_changed TrayIcon будет останавливать/перезапускать watcher с новыми путями.
    # Но для данной задачи, я просто передам updated_paths_to_watch в watcher
    # через property или метод.
    tray_icon.update_watched_paths(valid_paths) # <-- Новый метод для обновления путей в TrayIcon/Watcher

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
