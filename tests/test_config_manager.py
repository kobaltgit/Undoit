# -*- coding: utf-8 -*-
# Тесты для ConfigManager
import json
from pathlib import Path
import pytest
from PySide6.QtCore import QObject, Signal

from app.config_manager import ConfigManager

# Используем pytest фикстуру 'fs' от pyfakefs для создания виртуальной файловой системы
def test_initialization_creates_files(fs):
    """Тест: Инициализация ConfigManager создает папку и файл конфигурации, если их нет."""
    # pyfakefs создает виртуальную папку пользователя
    home_dir = Path.home()
    fs.create_dir(home_dir)

    # Ожидаемые пути
    expected_dir = home_dir / "AppData/Local/Undoit"
    expected_file = expected_dir / "config.json"

    assert not expected_dir.exists()
    assert not expected_file.exists()

    config_manager = ConfigManager()

    assert expected_dir.exists()
    assert expected_file.exists()

    with open(expected_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        assert "watched_items" in config_data
        assert config_data["theme"] == "auto"


def test_load_existing_config(fs):
    """Тест: ConfigManager корректно загружает существующий файл конфигурации."""
    home_dir = Path.home()
    config_dir = home_dir / "AppData/Local/Undoit"
    config_file = config_dir / "config.json"
    
    # Создаем "существующий" конфиг
    custom_settings = {
        "watched_items": [{"path": "/my/folder", "type": "folder", "exclusions": []}],
        "theme": "dark",
        "language": "ru",
        "launch_on_startup": True
    }
    fs.create_file(config_file, contents=json.dumps(custom_settings))

    config_manager = ConfigManager()

    assert config_manager.get("theme") == "dark"
    assert config_manager.get("language") == "ru"
    assert config_manager.get("launch_on_startup") is True
    assert config_manager.get_watched_items() == custom_settings["watched_items"]


def test_set_and_save_value(fs, mocker):
    """Тест: Метод set() изменяет значение, сохраняет в файл и испускает сигнал."""
    home_dir = Path.home()
    fs.create_dir(home_dir)
    config_file = home_dir / "AppData/Local/Undoit/config.json"

    config_manager = ConfigManager()
    
    # "Шпионим" за сигналом theme_changed
    mock_signal_handler = mocker.Mock()
    config_manager.theme_changed.connect(mock_signal_handler)

    # Изменяем настройку
    config_manager.set("theme", "light")

    # Проверяем, что значение в памяти изменилось
    assert config_manager.get("theme") == "light"

    # Проверяем, что файл был сохранен с новым значением
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        assert config_data["theme"] == "light"

    # Проверяем, что сигнал был испущен с правильным аргументом
    mock_signal_handler.assert_called_once_with("light")


def test_set_watched_items_emits_signal(fs, mocker):
    """Тест: Метод set() для watched_items корректно сохраняет и испускает сигнал."""
    home_dir = Path.home()
    fs.create_dir(home_dir)
    config_manager = ConfigManager()

    mock_signal_handler = mocker.Mock()
    config_manager.watched_items_changed.connect(mock_signal_handler)

    new_items = [
        {"path": "C:/Users/Test/Documents", "type": "folder", "exclusions": ["C:/Users/Test/Documents/Temp"]},
        {"path": "D:/file.txt", "type": "file", "exclusions": []}
    ]
    
    # Path объекты для корректной работы pyfakefs
    fs.create_dir("C:/Users/Test/Documents/Temp")
    fs.create_file("D:/file.txt")

    config_manager.set("watched_items", new_items)
    
    # Проверяем, что сигнал был вызван
    mock_signal_handler.assert_called_once()
    
    # Проверяем, что данные в файле и в памяти корректны (с нормализованными путями)
    saved_items = config_manager.get_watched_items()
    assert len(saved_items) == 2
    assert saved_items[0]["path"] == "C:/Users/Test/Documents"
    assert saved_items[0]["exclusions"] == ["C:/Users/Test/Documents/Temp"]


def test_migration_from_old_format(fs):
    """Тест: Миграция со старого формата watched_paths на новый watched_items работает корректно."""
    home_dir = Path.home()
    config_dir = home_dir / "AppData/Local/Undoit"
    config_file = config_dir / "config.json"

    # Создаем пути в виртуальной ФС, чтобы is_dir/is_file работали
    fs.create_dir("C:/my_folder")
    fs.create_file("C:/my_file.txt")
    # Этот путь не существует и должен быть проигнорирован
    # fs.create_file("C:/non_existent.txt")

    # Создаем конфиг в старом формате
    old_settings = {
        "watched_paths": [
            "C:/my_folder",
            "C:/my_file.txt",
            "C:/non_existent.txt"
        ],
        "theme": "auto"
    }
    fs.create_file(config_file, contents=json.dumps(old_settings))

    config_manager = ConfigManager() # Миграция должна произойти при инициализации

    # Проверяем, что данные были преобразованы
    new_items = config_manager.get_watched_items()
    assert len(new_items) == 2 # non_existent.txt должен быть проигнорирован
    
    folder_item = next((item for item in new_items if item["path"] == "C:/my_folder"), None)
    file_item = next((item for item in new_items if item["path"] == "C:/my_file.txt"), None)

    assert folder_item is not None
    assert folder_item["type"] == "folder"
    assert folder_item["exclusions"] == []
    
    assert file_item is not None
    assert file_item["type"] == "file"

    # Проверяем, что старый ключ удален из файла
    with open(config_file, 'r') as f:
        saved_data = json.load(f)
        assert "watched_paths" not in saved_data
        assert "watched_items" in saved_data

def test_get_storage_path(fs):
    """Тест: get_storage_path возвращает корректный путь."""
    home_dir = Path.home()
    fs.create_dir(home_dir)
    
    config_manager = ConfigManager()
    storage_path = config_manager.get_storage_path()
    
    expected_path = Path.home() / "AppData/Local/Undoit/storage"
    assert storage_path == expected_path