# -*- coding: utf-8 -*-
# Тесты для NotificationAggregator
import pytest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from app.notification_aggregator import NotificationAggregator

# Фикстура для создания экземпляра QApplication для тестов.
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def aggregator(qapp, qtbot):
    """
    Фикстура, которая создает экземпляр NotificationAggregator для теста
    и гарантирует его правильное удаление через цикл событий Qt.
    """
    agg = NotificationAggregator()
    yield agg
    # Явное удаление через deleteLater - ключевой момент для избежания падений.
    agg.deleteLater()
    # Даем Qt время на обработку события удаления
    qtbot.wait(50)


# Используем pytest-qt для работы с сигналами и таймерами Qt
def test_immediate_notification_without_topic(qtbot, aggregator):
    """Тест: Уведомление без темы (topic) должно отправляться немедленно."""
    with qtbot.waitSignal(aggregator.aggregated_notification_ready, timeout=100) as blocker:
        aggregator.add_notification(
            topic="",  # Пустая тема
            title="Важное",
            message="Это важное сообщение",
            icon=QSystemTrayIcon.Information
        )
    
    # Проверяем, что сигнал был испущен с правильными аргументами
    assert blocker.args == ["Важное", "Это важное сообщение", QSystemTrayIcon.Information]

def test_single_notification_in_topic_is_sent_after_delay(qtbot, aggregator):
    """Тест: Одно уведомление с темой отправляется после задержки."""
    aggregator.AGGREGATION_DELAY_MS = 50 # Уменьшаем задержку для теста

    with qtbot.waitSignal(aggregator.aggregated_notification_ready, timeout=200) as blocker:
        aggregator.add_notification(
            topic="history_events",
            title="История",
            message="Сохранена версия",
            icon=QSystemTrayIcon.Information
        )
    
    # Сообщение должно быть одно, поэтому оно не агрегируется, а просто отправляется
    assert blocker.args == ["История", "Сохранена версия", QSystemTrayIcon.Information]


def test_multiple_notifications_are_aggregated(qtbot, aggregator):
    """Тест: Несколько уведомлений с одной темой группируются в одно."""
    aggregator.AGGREGATION_DELAY_MS = 100 # Уменьшаем задержку для теста

    with qtbot.waitSignal(aggregator.aggregated_notification_ready, timeout=300) as blocker:
        # Отправляем несколько уведомлений подряд, быстрее чем AGGREGATION_DELAY_MS
        aggregator.add_notification("scan_progress", "Сканирование", "file1.txt", QSystemTrayIcon.Information)
        qtbot.wait(20)
        aggregator.add_notification("scan_progress", "Сканирование", "file2.txt", QSystemTrayIcon.Information)
        qtbot.wait(20)
        aggregator.add_notification("scan_progress", "Сканирование", "file3.txt", QSystemTrayIcon.Information)

    # Проверяем, что было отправлено одно сгруппированное сообщение
    expected_message = aggregator.tr("Просканировано {0} файлов: {1} и еще {2}").format(3, "file1.txt, file2.txt", 1)
    
    assert blocker.args == ["Сканирование", expected_message, QSystemTrayIcon.Information]


def test_notifications_with_different_topics_are_separate(qtbot, aggregator):
    """Тест: Уведомления с разными темами группируются отдельно."""
    aggregator.AGGREGATION_DELAY_MS = 100

    # Создаем "шпиона" вручную
    spy_list = []
    aggregator.aggregated_notification_ready.connect(lambda *args: spy_list.append(list(args)))

    # Отправляем уведомления для двух разных тем
    aggregator.add_notification("history_events", "История", "Сохранена версия 1", QSystemTrayIcon.Information)
    aggregator.add_notification("settings", "Настройки", "Тема изменена", QSystemTrayIcon.Information)
    aggregator.add_notification("history_events", "История", "Сохранена версия 2", QSystemTrayIcon.Information)

    # Ждем достаточно долго, чтобы оба таймера сработали
    qtbot.wait(200)

    # Должно быть ровно два вызова сигнала
    assert len(spy_list) == 2

    # Проверяем содержимое каждого вызова
    history_call = next(call for call in spy_list if call[0] == "История")
    settings_call = next(call for call in spy_list if call[0] == "Настройки")

    expected_history_msg = aggregator.tr("{0} (и еще {1} событий в истории)").format("Сохранена версия 1", 1)
    
    assert history_call == ["История", expected_history_msg, QSystemTrayIcon.Information]
    assert settings_call == ["Настройки", "Тема изменена", QSystemTrayIcon.Information]

def test_timer_restarts_on_new_notification(qtbot, aggregator):
    """Тест: Таймер перезапускается при поступлении нового уведомления в ту же тему."""
    aggregator.AGGREGATION_DELAY_MS = 100

    # Создаем "шпиона" вручную
    spy_list = []
    aggregator.aggregated_notification_ready.connect(lambda *args: spy_list.append(list(args)))

    # Первое уведомление
    aggregator.add_notification("scan_progress", "Сканирование", "file1.txt", QSystemTrayIcon.Information)
    
    # Ждем половину времени и отправляем второе
    qtbot.wait(60)
    aggregator.add_notification("scan_progress", "Сканирование", "file2.txt", QSystemTrayIcon.Information)

    # Проверяем, что за это время сигнал НЕ был отправлен
    assert len(spy_list) == 0
    
    # Ждем еще 110 мс (дольше, чем задержка)
    qtbot.wait(110)

    # Теперь сигнал должен быть отправлен
    assert len(spy_list) == 1
    expected_message = aggregator.tr("Просканировано {0} файлов: {1}").format(2, "file1.txt, file2.txt")
    assert spy_list[0] == ["Сканирование", expected_message, QSystemTrayIcon.Information]