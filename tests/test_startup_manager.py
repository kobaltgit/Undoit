# -*- coding: utf-8 -*-
# Тесты для StartupManager

import sys
from pathlib import Path
import pytest

from app.startup_manager import StartupManager

# Пропускаем все тесты в этом файле, если мы не на Windows
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="requires Windows")

# --- Фикстуры ---

@pytest.fixture
def mock_win32(mocker):
    """Фикстура, которая "мокает" зависимости от pywin32."""
    # Мокаем Dispatch, чтобы не создавать реальные COM-объекты
    mock_dispatch = mocker.patch('app.startup_manager.win32com.client.Dispatch')
    
    # Мокаем os.remove, чтобы не удалять реальные файлы
    mock_remove = mocker.patch('app.startup_manager.os.remove')

    # Мокаем CoInitialize и CoUninitialize, так как они не нужны в тестах
    mocker.patch('app.startup_manager.pythoncom.CoInitialize')
    mocker.patch('app.startup_manager.pythoncom.CoUninitialize')
    
    return mock_dispatch, mock_remove


@pytest.fixture
def startup_manager(fs, monkeypatch):
    """Фикстура для создания StartupManager с виртуальной файловой системой."""
    # Устанавливаем переменную окружения APPDATA, чтобы менеджер нашел папку автозагрузки
    # Используем monkeypatch для изоляции от реальных переменных окружения
    fake_appdata = "C:/Users/TestUser/AppData/Roaming"
    fs.create_dir(fake_appdata)
    monkeypatch.setenv("APPDATA", fake_appdata)
    
    app_name = "UndoitTest"
    app_path = Path("C:/Program Files/UndoitTest/Undoit.exe")
    fs.create_file(app_path)

    sm = StartupManager(app_name=app_name, app_executable_path=app_path)
    return sm

# --- Тесты ---

def test_shortcut_path_is_correct(startup_manager):
    """Тест: StartupManager правильно формирует путь к ярлыку."""
    shortcut_path = startup_manager._get_shortcut_path()
    expected_path = Path("C:/Users/TestUser/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/UndoitTest.lnk")
    assert shortcut_path == expected_path


def test_is_in_startup_returns_true_if_shortcut_exists(fs, startup_manager):
    """Тест: is_in_startup() возвращает True, если ярлык существует."""
    shortcut_path = startup_manager._get_shortcut_path()
    fs.create_file(shortcut_path) # Создаем фейковый ярлык
    
    assert startup_manager.is_in_startup() is True


def test_is_in_startup_returns_false_if_shortcut_does_not_exist(startup_manager):
    """Тест: is_in_startup() возвращает False, если ярлык не существует."""
    assert startup_manager.is_in_startup() is False


def test_add_to_startup_creates_shortcut(startup_manager, mock_win32):
    """Тест: add_to_startup() вызывает методы для создания ярлыка."""
    mock_dispatch, _ = mock_win32
    
    # Получаем мок объекта WScript.Shell
    mock_shell = mock_dispatch.return_value
    # Получаем мок самого объекта ярлыка
    mock_shortcut = mock_shell.CreateShortcut.return_value

    startup_manager.add_to_startup()

    # Проверяем, что был вызван метод создания ярлыка с правильным путем
    mock_shell.CreateShortcut.assert_called_once_with(str(startup_manager._get_shortcut_path()))
    
    # Проверяем, что были установлены свойства ярлыка
    assert mock_shortcut.TargetPath == str(startup_manager.app_executable_path)
    assert mock_shortcut.WorkingDirectory == str(startup_manager.app_executable_path.parent)
    
    # Проверяем, что ярлык был сохранен
    mock_shortcut.save.assert_called_once()


def test_remove_from_startup_deletes_shortcut(fs, startup_manager, mock_win32):
    """Тест: remove_from_startup() вызывает os.remove для удаления ярлыка."""
    _, mock_remove = mock_win32
    
    # Сначала создаем фейковый ярлык, чтобы было что удалять
    shortcut_path = startup_manager._get_shortcut_path()
    fs.create_file(shortcut_path)

    assert startup_manager.is_in_startup() is True
    
    startup_manager.remove_from_startup()
    
    # Проверяем, что был вызван os.remove с правильным путем
    mock_remove.assert_called_once_with(shortcut_path)