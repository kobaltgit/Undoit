# -*- coding: utf-8 -*-
# Агрегатор для группировки "быстрых" уведомлений
from collections import defaultdict
from typing import Dict, List, Tuple

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QSystemTrayIcon


class NotificationAggregator(QObject):
    """
    Группирует быстрые, повторяющиеся уведомления в одно сообщение.
    """
    # Сигнал, который отправляет готовое к показу (сгруппированное) уведомление
    # (title, message, icon_type)
    aggregated_notification_ready = Signal(str, str, QSystemTrayIcon.MessageIcon)

    # Задержка в миллисекундах, в течение которой собираются уведомления
    AGGREGATION_DELAY_MS = 600

    def __init__(self, parent=None):
        super().__init__(parent)
        # Словарь для хранения таймеров по темам
        self._timers: Dict[str, QTimer] = {}
        # Словарь для хранения накопленных сообщений и метаданных
        # Формат: { "topic": ([msg1, msg2, ...], title, icon_type), ... }
        self._pending_notifications: Dict[str, Tuple[List[str], str, QSystemTrayIcon.MessageIcon]] = defaultdict(
            lambda: ([], "", QSystemTrayIcon.Information)
        )

    def add_notification(self, topic: str, title: str, message: str, icon: QSystemTrayIcon.MessageIcon):
        """
        Добавляет уведомление. Если тема не указана, отправляет сразу.
        Иначе, запускает механизм агрегации.
        """
        if not topic:
            # Если темы нет, это важное одиночное уведомление. Показываем сразу.
            self.aggregated_notification_ready.emit(title, message, icon)
            return

        # Если для этой темы уже есть активный таймер, останавливаем и удаляем его.
        if topic in self._timers:
            self._timers.pop(topic).deleteLater()

        # Добавляем сообщение в список для этой темы
        messages, _, __ = self._pending_notifications[topic]
        messages.append(message)
        
        # Если это первое сообщение в текущем "пакете", сохраняем заголовок и иконку
        if len(messages) == 1:
            self._pending_notifications[topic] = (messages, title, icon)

        # Создаем НОВЫЙ таймер. Это самый надежный способ.
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self.AGGREGATION_DELAY_MS)
        # Использование topic=topic заставляет лямбду "захватить"
        # текущее значение переменной topic в момент создания.
        timer.timeout.connect(lambda topic=topic: self._flush_topic(topic))
        self._timers[topic] = timer
        timer.start()

    def _flush_topic(self, topic: str):
        """
        Формирует и отправляет сгруппированное уведомление для указанной темы.
        """
        if topic not in self._pending_notifications:
            return

        messages, title, icon = self._pending_notifications.pop(topic)
        # Удаляем таймер, чтобы он не висел в памяти
        if topic in self._timers:
            self._timers.pop(topic).deleteLater()

        count = len(messages)
        if count == 0:
            return
        elif count == 1:
            # Если сообщение одно, просто показываем его
            final_message = messages[0]
        else:
            # Если сообщений много, форматируем их в зависимости от темы
            if topic == "scan_progress":
                max_items_to_show = 2
                first_items = ", ".join(messages[:max_items_to_show])
                if count > max_items_to_show:
                    final_message = self.tr("Просканировано {0} файлов: {1} и еще {2}").format(
                        count, first_items, count - max_items_to_show
                    )
                else:
                    final_message = self.tr("Просканировано {0} файлов: {1}").format(count, first_items)
            
            # --- НОВАЯ ЛОГИКА ---
            elif topic == "history_events":
                # Для событий истории, где сообщения могут быть разнообразными
                # (сохранено, добавлено, удалено), показываем первое и количество остальных.
                first_event = messages[0]
                final_message = self.tr("{0} (и еще {1} событий в истории)").format(
                    first_event, count - 1
                )

            else: # Общий, улучшенный случай для других тем (например, 'settings')
                first_event = messages[0]
                # Обрезаем первое сообщение, если оно слишком длинное
                if len(first_event) > 60:
                    first_event = first_event[:57] + "..."
                
                final_message = self.tr("{0} (и еще {1} уведомлений)").format(
                    first_event, count - 1
                )

        self.aggregated_notification_ready.emit(title, final_message, icon)