# -*- coding: utf-8 -*-
# GUI: Окно помощи

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, 
                               QPushButton, QMessageBox)
from PySide6.QtGui import QIcon

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


class HelpWindow(QDialog):
    """
    Окно для отображения справочной информации из Markdown-файла.
    """
    HELP_FILE_PATH = "resources/docs/help_ru.md"

    def __init__(self, app_icon: QIcon, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Справка"))
        self.setWindowIcon(app_icon)
        self.resize(800, 600)

        self._init_ui()
        self._load_help_content()

    def _init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True) # Открывать ссылки в браузере

        close_button = QPushButton(self.tr("Закрыть"))
        close_button.clicked.connect(self.accept)

        main_layout.addWidget(self.text_browser)
        main_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def _load_help_content(self):
        """Загружает и отображает содержимое Markdown-файла."""
        help_file_full_path = _resource_path(self.HELP_FILE_PATH)
        
        try:
            with open(help_file_full_path, 'r', encoding='utf-8') as f:
                content_md = f.read()
            
            # QTextBrowser напрямую поддерживает подмножество Markdown
            self.text_browser.setMarkdown(content_md)

        except FileNotFoundError:
            error_message = self.tr("Файл справки не найден по пути:\n{0}").format(help_file_full_path)
            self.text_browser.setText(error_message)
            QMessageBox.critical(self, self.tr("Ошибка"), error_message)
        except Exception as e:
            error_message = self.tr("Произошла ошибка при чтении файла справки:\n{0}").format(e)
            self.text_browser.setText(error_message)
            QMessageBox.critical(self, self.tr("Ошибка"), error_message)