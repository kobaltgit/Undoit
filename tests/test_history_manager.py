# -*- coding: utf-8 -*-
# Тесты для HistoryManager
import sqlite3
from pathlib import Path
from typing import Generator
import pytest
from app.history_manager import HistoryManager

# --- Фикстуры Pytest для настройки тестового окружения ---

@pytest.fixture
def history_manager(fs, mocker) -> Generator[HistoryManager, None, None]:
    """
    Фикстура для создания экземпляра HistoryManager с виртуальной файловой системой.
    Ключевой момент: мы "мокаем" sqlite3.connect, чтобы он всегда возвращал
    соединение с базой данных в оперативной памяти.
    """
    # Мокаем QTimer, чтобы он не мешал тестам
    mocker.patch('app.history_manager.QTimer')

    # Создаем соединение с БД в памяти ОДИН РАЗ
    in_memory_connection = sqlite3.connect(':memory:', check_same_thread=False)
    # Заставляем HistoryManager использовать это соединение при каждом вызове connect
    mocker.patch('app.history_manager.sqlite3.connect', return_value=in_memory_connection)

    storage_path = Path("/storage")
    fs.create_dir(storage_path)
    
    # Теперь инициализация пройдет успешно, так как sqlite3.connect "подменен"
    hm = HistoryManager(storage_path=storage_path)
    
    # hm.__init__ уже вызвал _setup_database, так что таблицы должны быть созданы.
    # Просто для уверенности проверим это.
    cursor = in_memory_connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracked_files'")
    assert cursor.fetchone() is not None
    cursor.close()
    
    yield hm
    
    # Очистка после теста
    in_memory_connection.close()


@pytest.fixture
def create_files(fs):
    """Фикстура для создания тестовых файлов в виртуальной ФС."""
    fs.create_file("/test_files/document.txt", contents="version 1")
    fs.create_file("/test_files/image.jpg", contents=b'\x89PNG\r\n\x1a\n\x00') # Fake image content
    fs.create_dir("/test_files/project/src")
    fs.create_file("/test_files/project/main.py", contents="import sys")
    return fs

# --- Тесты ---

def test_add_first_version(history_manager, create_files, mocker):
    """Тест: Добавление самой первой версии файла."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")

    mock_version_added = mocker.Mock()
    mock_file_list_updated = mocker.Mock()
    hm.version_added.connect(mock_version_added)
    hm.file_list_updated.connect(mock_file_list_updated)

    # Добавляем версию
    hm.add_file_version(str(file_path))

    # 1. Проверяем сигналы
    mock_version_added.assert_called_once()
    mock_file_list_updated.assert_called_once()

    # 2. Проверяем базу данных
    files = hm.get_all_tracked_files()
    assert len(files) == 1
    file_id, original_path = files[0]
    assert original_path == str(file_path)

    versions = hm.get_versions_for_file(file_id)
    assert len(versions) == 1
    version_id, _, sha256_hash, file_size = versions[0]
    assert file_size == len("version 1")

    # 3. Проверяем хранилище объектов
    object_path = hm.get_object_path(sha256_hash)
    assert object_path is not None
    assert object_path.exists()
    with open(object_path, 'r') as f:
        assert f.read() == "version 1"


def test_add_second_version(history_manager, create_files, mocker):
    """Тест: Добавление второй, измененной версии файла."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")
    hm.add_file_version(str(file_path)) # Добавляем первую версию

    # Обновляем содержимое файла (удаляем и создаем заново)
    create_files.remove(file_path)
    create_files.create_file(file_path, contents="version 2 - changed")

    mock_version_added = mocker.Mock()
    mock_file_list_updated = mocker.Mock()
    hm.version_added.connect(mock_version_added)
    hm.file_list_updated.connect(mock_file_list_updated)
    
    # Добавляем вторую версию
    hm.add_file_version(str(file_path))

    # 1. Проверяем сигналы (file_list_updated не должен вызываться для существующего файла)
    mock_version_added.assert_called_once()
    mock_file_list_updated.assert_not_called()

    # 2. Проверяем базу данных
    files = hm.get_all_tracked_files()
    assert len(files) == 1 # Файл все еще один
    file_id = files[0][0]

    versions = hm.get_versions_for_file(file_id)
    assert len(versions) == 2 # Теперь две версии


def test_add_same_version_is_ignored(history_manager, create_files, mocker):
    """Тест: Повторное добавление той же самой версии должно быть проигнорировано."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")
    hm.add_file_version(str(file_path)) # Первая версия

    mock_version_added = mocker.Mock()
    hm.version_added.connect(mock_version_added)
    
    # Пытаемся добавить ту же самую версию еще раз
    hm.add_file_version(str(file_path))

    # 1. Сигнал не должен быть вызван
    mock_version_added.assert_not_called()

    # 2. В базе данных должна остаться только одна версия
    files = hm.get_all_tracked_files()
    file_id = files[0][0]
    versions = hm.get_versions_for_file(file_id)
    assert len(versions) == 1


def test_delete_single_version(history_manager, create_files, mocker):
    """Тест: Удаление одной версии, когда у файла их несколько."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")

    # Создаем 2 версии
    hm.add_file_version(str(file_path))
    create_files.remove(file_path)
    create_files.create_file(file_path, contents="version 2")
    hm.add_file_version(str(file_path))

    file_id = hm.get_all_tracked_files()[0][0]
    versions_before = hm.get_versions_for_file(file_id)
    assert len(versions_before) == 2
    
    version_to_delete = versions_before[0] # Самая новая
    version_id, _, sha256_hash, _ = version_to_delete

    mock_version_deleted = mocker.Mock()
    hm.version_deleted.connect(mock_version_deleted)

    # Удаляем версию
    success = hm.delete_file_version(version_id, file_id, sha256_hash)
    assert success is True

    # 1. Проверяем сигнал
    mock_version_deleted.assert_called_once_with(file_id)

    # 2. Проверяем БД
    versions_after = hm.get_versions_for_file(file_id)
    assert len(versions_after) == 1
    assert versions_after[0][0] != version_id # Убеждаемся, что удалили нужную

    # 3. Проверяем хранилище (объект должен быть удален, т.к. на него нет ссылок)
    object_path = hm.get_object_path(sha256_hash)
    assert object_path is None


def test_delete_last_version_removes_file(history_manager, create_files, mocker):
    """Тест: Удаление последней версии файла должно удалить и сам файл из отслеживаемых."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")
    hm.add_file_version(str(file_path))

    file_id = hm.get_all_tracked_files()[0][0]
    version_to_delete = hm.get_versions_for_file(file_id)[0]
    version_id, _, sha256_hash, _ = version_to_delete

    mock_files_deleted = mocker.Mock()
    hm.files_deleted.connect(mock_files_deleted)

    # Удаляем последнюю версию
    success = hm.delete_file_version(version_id, file_id, sha256_hash)
    assert success is True

    # 1. Проверяем сигнал
    mock_files_deleted.assert_called_once_with([(file_id, str(file_path))])

    # 2. Проверяем БД (не должно остаться ни файла, ни версий)
    files_after = hm.get_all_tracked_files()
    assert len(files_after) == 0
    
    # Проверка, что версий тоже нет (на всякий случай)
    cursor = hm._db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM versions WHERE file_id = ?", (file_id,))
    assert cursor.fetchone()[0] == 0


def test_delete_tracked_file_with_multiple_versions(history_manager, create_files, mocker):
    """Тест: Полное удаление отслеживаемого файла со всеми его версиями."""
    hm = history_manager
    file_path = Path("/test_files/document.txt")
    
    # Создаем 2 версии
    hm.add_file_version(str(file_path))
    create_files.remove(file_path)
    create_files.create_file(file_path, contents="version 2")
    hm.add_file_version(str(file_path))

    file_id = hm.get_all_tracked_files()[0][0]
    assert len(hm.get_versions_for_file(file_id)) == 2

    mock_files_deleted = mocker.Mock()
    hm.files_deleted.connect(mock_files_deleted)
    
    # Удаляем весь файл
    deleted_count, _ = hm.delete_tracked_files({file_id})
    
    assert deleted_count == 1
    mock_files_deleted.assert_called_once_with([(file_id, str(file_path))])

    # Проверяем, что в БД ничего не осталось
    assert len(hm.get_all_tracked_files()) == 0


def test_clean_unwatched_files(history_manager, create_files, mocker):
    """Тест: Очистка файлов, которые больше не входят в список отслеживаемых."""
    hm = history_manager
    
    # Добавляем 3 файла в историю
    path1 = "/test_files/document.txt"
    path2 = "/test_files/image.jpg"
    path3 = "/test_files/project/main.py"
    hm.add_file_version(path1)
    hm.add_file_version(path2)
    hm.add_file_version(path3)
    
    assert len(hm.get_all_tracked_files()) == 3

    mock_files_deleted = mocker.Mock()
    hm.files_deleted.connect(mock_files_deleted)

    # Теперь "отслеживаем" только 2 из них
    watched_items = [
        {"path": path1, "type": "file", "exclusions": []},
        {"path": path3, "type": "file", "exclusions": []},
    ]

    # Запускаем очистку
    _, deleted_count = hm.clean_unwatched_files_in_db(watched_items)

    assert deleted_count == 1
    
    # Проверяем, что в БД остались только отслеживаемые файлы
    remaining_files = hm.get_all_tracked_files()
    assert len(remaining_files) == 2
    remaining_paths = {Path(path).as_posix() for _, path in remaining_files}
    assert path1 in remaining_paths
    assert path3 in remaining_paths
    assert path2 not in remaining_paths

    # Проверяем, что был вызван сигнал с информацией об удаленном файле
    mock_files_deleted.assert_called_once()
    deleted_info = mock_files_deleted.call_args[0][0] # Первый аргумент первого вызова
    assert len(deleted_info) == 1
    assert Path(deleted_info[0][1]).as_posix() == path2 # Проверяем путь удаленного файла