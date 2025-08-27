# -*- coding: utf-8 -*-
# Управление локализацией приложения
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTranslator, QLocale, Slot, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon # <-- Добавлен импорт Signal и QSystemTrayIcon

from app.config_manager import ConfigManager


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


class LocaleManager(QObject):
    """
    Управляет загрузкой и применением переводов (.qm файлов)
    ко всему приложению на основе системного языка или выбора пользователя.
    """
    # Сигнал для отправки уведомлений в трей.
    # Аргументы: message (str), icon_type (QSystemTrayIcon.MessageIcon)
    locale_notification = Signal(str, QSystemTrayIcon.MessageIcon)

    TRANSLATIONS_DIR = "resources/translations"
    # Допустимые языки, соответствующие именам .qm файлов (например, ru.qm, en.qm)
    SUPPORTED_LANGUAGES = {"ru", "en"}

    def __init__(self, config_manager: ConfigManager, app: QApplication, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.app = app
        self._current_translator = None # Текущий активный QTranslator

        # Подключаемся к сигналу изменения настроек
        self.config_manager.settings_changed.connect(self._on_settings_changed)

        # Применяем язык при инициализации
        self._apply_current_locale()

    def _get_system_locale_preference(self) -> str:
        """
        Определяет основной язык системы (например, 'ru' из 'ru_RU').
        """
        system_locale_name = QLocale.system().name() # Например, "en_US", "ru_RU"
        base_language = system_locale_name.split('_')[0] # Например, "en", "ru"

        if base_language in self.SUPPORTED_LANGUAGES:
            return base_language
        return "en" # По умолчанию английский, если системный язык не поддерживается

    def _load_translator(self, lang_key: str):
        """
        Загружает файл перевода для указанного языка и устанавливает его.
        """
        # Сначала удаляем предыдущий переводчик, если он был установлен
        if self._current_translator:
            self.app.removeTranslator(self._current_translator)
            self._current_translator = None

        if lang_key not in self.SUPPORTED_LANGUAGES:
            # Для неподдерживаемых языков или "auto" без совпадения, просто не устанавливаем переводчик
            # print(f"LocaleManager: Язык '{lang_key}' не поддерживается или выбран 'auto' без совпадений. Используется язык по умолчанию.")
            self.locale_notification.emit(
                self.tr("Язык '{0}' не поддерживается или выбран 'Авто' без совпадений. Используется язык по умолчанию.").format(lang_key),
                QSystemTrayIcon.Information
            )
            return

        translator = QTranslator(self) # Создаем новый переводчик
        qm_file_path = _resource_path(Path(self.TRANSLATIONS_DIR) / f"{lang_key}.qm")

        if translator.load(str(qm_file_path)):
            self.app.installTranslator(translator)
            self._current_translator = translator
            # print(f"LocaleManager: Применен перевод для языка: {lang_key} из файла {qm_file_path}")
            self.locale_notification.emit(
                self.tr("Применен перевод для языка: {0}").format(lang_key),
                QSystemTrayIcon.Information
            )
        else:
            # print(f"LocaleManager: Ошибка загрузки файла перевода для {lang_key}: {qm_file_path}")
            self.locale_notification.emit(
                self.tr("Ошибка загрузки файла перевода для {0}: {1}").format(lang_key, qm_file_path),
                QSystemTrayIcon.Warning
            )

    def _apply_current_locale(self):
        """
        Определяет и применяет текущий язык на основе настроек пользователя
        или системных предпочтений.
        """
        user_lang_setting = self.config_manager.get("language", "auto")

        if user_lang_setting == "auto":
            system_lang = self._get_system_locale_preference()
            self._load_translator(system_lang)
        elif user_lang_setting in self.SUPPORTED_LANGUAGES:
            self._load_translator(user_lang_setting)
        else:
            # print(f"LocaleManager: Неизвестная настройка языка: {user_lang_setting}. Используется английский по умолчанию.")
            self.locale_notification.emit(
                self.tr("Неизвестная настройка языка: {0}. Используется английский по умолчанию.").format(user_lang_setting),
                QSystemTrayIcon.Warning
            )
            self._load_translator("en") # Fallback на английский

    @Slot()
    def _on_settings_changed(self):
        """
        Слот, вызываемый при изменении настроек. Переприменяет язык,
        если настройка языка изменилась.
        """
        # Просто переприменяем язык. Если изменились другие настройки,
        # это не навредит, если язык не менялся.
        current_lang_setting_before_apply = self.config_manager.get("language", "auto")
        self._apply_current_locale()
        current_lang_setting_after_apply = self.config_manager.get("language", "auto")

        # Отправляем уведомление, только если язык реально изменился
        if current_lang_setting_before_apply != current_lang_setting_after_apply:
            self.locale_notification.emit(
                self.tr("Настройка языка изменена. Текущий язык: {0}").format(current_lang_setting_after_apply),
                QSystemTrayIcon.Information
            )
        # print(f"LocaleManager: Настройка языка изменена или другие настройки сохранены. Текущий язык: {current_lang_setting}.")
