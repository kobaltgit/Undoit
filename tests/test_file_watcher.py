# -*- coding: utf-8 -*-
# Тесты для FileWatcher

from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

from app.file_watcher import ChangeHandler, FileWatcher

# --- Тесты для ChangeHandler (логика правил) ---

@pytest.fixture
def create_watched_structure(fs):
    """Фикстура для создания структуры папок и файлов для тестов."""
    # Отслеживаемая папка
    fs.create_dir("/watched_folder/subfolder")
    fs.create_file("/watched_folder/file1.txt")
    fs.create_file("/watched_folder/subfolder/file2.py")
    
    # Исключенная папка
    fs.create_dir("/watched_folder/excluded_folder")
    fs.create_file("/watched_folder/excluded_folder/ignored.log")

    # Отдельный отслеживаемый файл
    fs.create_file("/another_folder/watched_file.md")

    # Неотслеживаемая папка
    fs.create_dir("/unwatched_folder")
    fs.create_file("/unwatched_folder/some_file.txt")


def test_change_handler_allows_direct_file(create_watched_structure):
    """Тест: обработчик должен разрешать путь к напрямую отслеживаемому файлу."""
    rules = {
        'files': {Path("/another_folder/watched_file.md").resolve()},
        'folders': {}
    }
    handler = ChangeHandler(Mock(), rules)
    assert handler._is_path_allowed("/another_folder/watched_file.md") is True


def test_change_handler_allows_file_in_watched_folder(create_watched_structure):
    """Тест: обработчик должен разрешать путь к файлу внутри отслеживаемой папки."""
    rules = {
        'files': set(),
        'folders': {
            Path("/watched_folder").resolve(): set()
        }
    }
    handler = ChangeHandler(Mock(), rules)
    assert handler._is_path_allowed("/watched_folder/file1.txt") is True
    assert handler._is_path_allowed("/watched_folder/subfolder/file2.py") is True


def test_change_handler_denies_file_in_excluded_folder(create_watched_structure):
    """Тест: обработчик должен запрещать путь к файлу в исключенной подпапке."""
    rules = {
        'files': set(),
        'folders': {
            Path("/watched_folder").resolve(): {Path("/watched_folder/excluded_folder").resolve()}
        }
    }
    handler = ChangeHandler(Mock(), rules)
    assert handler._is_path_allowed("/watched_folder/excluded_folder/ignored.log") is False
    # Но файлы не в исключенной папке должны быть разрешены
    assert handler._is_path_allowed("/watched_folder/file1.txt") is True


def test_change_handler_denies_unwatched_file(create_watched_structure):
    """Тест: обработчик должен запрещать путь к файлу, не подпадающему ни под одно правило."""
    rules = {
        'files': {Path("/another_folder/watched_file.md").resolve()},
        'folders': {
            Path("/watched_folder").resolve(): set()
        }
    }
    handler = ChangeHandler(Mock(), rules)
    assert handler._is_path_allowed("/unwatched_folder/some_file.txt") is False


# --- Тесты для FileWatcher (построение правил и управление) ---

def test_file_watcher_builds_correct_rules(fs):
    """Тест: FileWatcher должен правильно строить правила из watched_items."""
    # Создаем виртуальные пути
    fs.create_dir("/project/src")
    fs.create_dir("/project/node_modules")
    fs.create_file("/project/main.py")
    fs.create_file("/docs/readme.md")

    watched_items = [
        {
            "path": "/project", 
            "type": "folder", 
            "exclusions": ["/project/node_modules"]
        },
        {
            "path": "/docs/readme.md", 
            "type": "file", 
            "exclusions": []
        }
    ]

    watcher = FileWatcher(watched_items)
    
    # Проверяем внутренние правила, которые он построил
    rules = watcher._rules
    
    # 1. Проверяем отслеживаемые файлы
    assert Path("/docs/readme.md").resolve() in rules['files']
    
    # 2. Проверяем отслеживаемые папки и исключения
    project_folder_path = Path("/project").resolve()
    assert project_folder_path in rules['folders']
    assert Path("/project/node_modules").resolve() in rules['folders'][project_folder_path]

    # 3. Проверяем список папок для передачи в watchdog.Observer
    # Должны быть родительские папки файлов и сами отслеживаемые папки
    folders_to_watch = watcher._folders_to_watch
    assert project_folder_path in folders_to_watch
    assert Path("/docs").resolve() in folders_to_watch
    assert len(folders_to_watch) == 2


def test_file_watcher_start_stop_calls_observer(fs, mocker):
    """Тест: методы start() и stop() должны вызывать соответствующие методы Observer."""
    # Мокаем (имитируем) класс Observer, чтобы не создавать реальный поток
    mock_observer_class = mocker.patch('app.file_watcher.Observer')
    # Создаем экземпляр мока для возврата при вызове Observer()
    mock_observer_instance = MagicMock()
    mock_observer_class.return_value = mock_observer_instance

    fs.create_dir("/folder_to_watch")
    items = [{"path": "/folder_to_watch", "type": "folder", "exclusions": []}]

    watcher = FileWatcher(items)
    
    # Запускаем отслеживание
    watcher.start()
    
    # Проверяем, что наблюдатель был запущен
    mock_observer_instance.start.assert_called_once()
    
    # Останавливаем отслеживание
    watcher.stop()
    
    # Проверяем, что наблюдатель был остановлен
    mock_observer_instance.stop.assert_called_once()
    mock_observer_instance.join.assert_called_once()