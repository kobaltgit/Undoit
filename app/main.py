# -*- coding: utf-8 -*-
# Главный файл приложения. Создает QApplication и TrayIcon.
import sys
from PySide6.QtWidgets import QApplication
from app.tray_icon import TrayIcon

def main():
    """Главная функция запуска приложения."""
    # 1. Создаем основной объект приложения
    app = QApplication(sys.argv)

    # 2. Устанавливаем важное правило для приложений, работающих в трее.
    #    Оно предотвращает закрытие программы, когда последнее окно (например, настройки)
    #    будет закрыто. Выход будет осуществляться только через меню в трее.
    app.setQuitOnLastWindowClosed(False)

    # 3. Создаем и показываем нашу иконку в трее
    tray_icon = TrayIcon()
    tray_icon.show()

    # 4. Запускаем главный цикл обработки событий приложения
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())