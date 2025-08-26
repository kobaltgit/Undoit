# -*- coding: utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.tray_icon import TrayIcon

# --- КОНФИГУРАЦИЯ (ВРЕМЕННАЯ) ---
# В будущем эти значения будут считываться из файла настроек.

# 1. Определяем путь для хранения резервных копий.
#    Используем стандартную папку для данных приложений пользователя.
#    Path.home() -> C:\Users\<ИмяПользователя>
STORAGE_PATH = Path.home() / "AppData" / "Local" / "Backdraft" / "storage"

# 2. Список папок для отслеживания.
#    ВАЖНО: Замените путь на реальную папку на вашем компьютере для теста!
#    Например, создайте папку C:\Temp\TestFolder
#    Используйте двойные обратные слеши (\\) или прямые слеши (/) в путях.
PATHS_TO_WATCH = [
    str(Path.home() / "Desktop"),
    # "C:/Users/YourUser/Documents" # Пример другого пути
]
# --- КОНЕЦ КОНФИГУРАЦИИ ---


def main():
    """Главная функция запуска приложения."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Проверяем, что папки для отслеживания существуют
    valid_paths = []
    for path in PATHS_TO_WATCH:
        if Path(path).exists():
            valid_paths.append(path)
        else:
            print(f"Внимание: Указанный путь не существует и будет проигнорирован: {path}")

    if not valid_paths:
        print("Ошибка: Не указано ни одной существующей папки для отслеживания. Выход.")
        # Тут в будущем можно показать диалоговое окно с ошибкой
        return 1 # Возвращаем код ошибки

    # Создаем и показываем нашу иконку в трее, передавая ей конфигурацию
    tray_icon = TrayIcon(storage_path=STORAGE_PATH, paths_to_watch=valid_paths)
    tray_icon.show()

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())