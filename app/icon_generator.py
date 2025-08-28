# -*- coding: utf-8 -*-
# Генератор иконок-щитов
import os
import sys
import winreg
from typing import Dict, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QImage, QPainter,
                           QPainterPath, QPen, QPixmap)


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


class IconGenerator:
    """
    Генерирует иконки для системного трея программно,
    используя QPainter.

    Иконка представляет собой щит в форме буквы 'U'.
    Контур иконки адаптируется к светлой/темной теме Windows,
    а заливка меняет цвет в зависимости от состояния приложения.
    """
    def __init__(self):
        self._icons: Dict[str, QIcon] = {}
        # Сразу генерируем все варианты иконок при старте
        self.generate_all_icons()

    def _get_system_theme_colors(self) -> Tuple[str, str]:
        """
        Читает реестр Windows для определения системной темы и акцентного цвета.
        Возвращает (цвет_контура, цвет_акцента) в формате hex.
        Первый элемент также указывает на светлую/темную тему:
        '#000000' для светлой, '#FFFFFF' для темной.
        """
        # Проверяем, что мы на Windows
        if sys.platform != 'win32':
            # Для других ОС по умолчанию светлая тема и стандартный синий акцент
            return '#000000', '#0078D4'

        outline_color = '#000000'  # Черный для светлой темы по умолчанию
        accent_color_hex = '#0078D4'  # Стандартный синий Windows по умолчанию

        try:
            # Определяем, используется ли светлая или темная тема
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            # Если AppsUseLightTheme == 0, значит тема темная
            if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] == 0:
                outline_color = '#FFFFFF'  # Белый для темной темы
            winreg.CloseKey(key)

            # Получаем акцентный цвет системы
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\DWM'
            )
            accent_color_dw = winreg.QueryValueEx(key, 'AccentColor')[0]
            # Конвертируем из DWM-формата (ABGR) в RGB hex
            b = (accent_color_dw >> 16) & 0xff
            g = (accent_color_dw >> 8) & 0xff
            r = (accent_color_dw) & 0xff
            accent_color_hex = f'#{r:02x}{g:02x}{b:02x}'
            winreg.CloseKey(key)
        except Exception:
            # В случае ошибки (например, нестандартная тема) используем значения по умолчанию
            pass

        return outline_color, accent_color_hex

    def _generate_shield_icon(self, fill_color: QColor, fill_percentage: float = 1.0) -> QImage:
        """
        Основная функция, которая рисует одну иконку с заданной заливкой.
        fill_percentage: процент заполнения иконки (0.0 до 1.0).
                         Если < 1.0, заливка будет частичной, иначе полной.
        """
        icon_size = 64  # Стандартный размер для иконок трея
        image = QImage(icon_size, icon_size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outline_color_hex, _ = self._get_system_theme_colors()
        outline_color = QColor(outline_color_hex)

        # Координаты и размеры в условной сетке 100x100 для масштабирования
        scale = icon_size / 100.0
        pen_width = 12 * scale

        # Настройка пера (контура)
        pen = QPen(outline_color)
        pen.setWidthF(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Создание формы щита (буквы 'U') с помощью QPainterPath
        path = QPainterPath()
        path.moveTo(20 * scale, 15 * scale) # Верхний левый угол
        path.lineTo(20 * scale, 65 * scale) # Левая вертикальная линия
        # Нижняя дуга в прямоугольнике (x=20, y=40, w=60, h=50)
        path.arcTo(20 * scale, 40 * scale, 60 * scale, 50 * scale, 180, 180)
        path.lineTo(80 * scale, 15 * scale) # Правая вертикальная линия

        # Рисуем контур щита
        painter.drawPath(path)

        # Если fill_percentage меньше 1.0, делаем частичную заливку
        if 0.0 < fill_percentage < 1.0:
            # Определяем высоту для заливки
            # Высота щита от 15*scale до 90*scale (по Y)
            total_height_px = (90 - 15) * scale
            fill_height_px = total_height_px * fill_percentage

            # Начало заливки по Y (снизу вверх)
            fill_start_y = (90 * scale) - fill_height_px

            # Создаем клипинг-путь, чтобы заливка была только внутри формы щита
            clip_path = QPainterPath()
            clip_path.addPath(path) # Используем ту же форму, что и для контура

            # Ограничиваем область заливки снизу
            fill_rect = path.boundingRect()
            fill_rect.setY(fill_start_y)
            fill_rect.setHeight(fill_height_px)
            # Пересекаем clip_path с прямоугольником заливки, чтобы не рисовать выше нужной точки
            # (path.intersected(QPainterPath(fill_rect))) не работает так, как ожидалось
            # Проще создать прямоугольник клипинга и использовать его
            clip_rect_for_fill = fill_rect.intersected(path.boundingRect()) # Гарантируем, что rect внутри bounds

            painter.setClipRect(clip_rect_for_fill.toRect()) # Устанавливаем клипинг прямоугольником
            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path) # Рисуем заливку внутри клипинга

            painter.setClipPath(QPainterPath()) # Сбрасываем клипинг
        elif fill_percentage >= 1.0: # Полная заливка
            painter.setBrush(QBrush(fill_color))
            painter.drawPath(path)

        painter.end()

        return image

    def generate_all_icons(self):
        """
        Генерирует и кэширует все состояния иконок (кроме динамической нормальной).
        Динамическая иконка с fill_percentage генерируется по запросу.
        """
        _, accent_color_hex = self._get_system_theme_colors()

        # Эти иконки всегда полностью залиты (fill_percentage = 1.0)
        state_colors = {
            'saving': QColor(accent_color_hex),
            'paused': QColor('#808080'),  # Серый
            'error': QColor('#D32F2F'),   # Насыщенный красный
            'inactive': QColor("#FFBB00") # Темно-серый для неактивного состояния (не запущен, не пауза)
        }

        for state, color in state_colors.items():
            image = self._generate_shield_icon(color, fill_percentage=1.0)
            pixmap = QPixmap.fromImage(image)
            self._icons[state] = QIcon(pixmap)

        # Для 'normal' состояния мы не кэшируем иконку здесь, так как она может быть динамической.
        # Вместо этого, будет вызван get_dynamic_icon.
        # Чтобы избежать ошибки, если запросят 'normal' без параметров,
        # можно добавить пустую иконку или иконку с 0% заливкой как базовую.
        image = self._generate_shield_icon(QColor(Qt.GlobalColor.transparent), fill_percentage=0.0)
        pixmap = QPixmap.fromImage(image)
        self._icons['normal'] = QIcon(pixmap)

    def get_icon(self, state: str) -> QIcon:
        """
        Возвращает готовую QIcon для заданного состояния.
        Для статических состояний берет из кэша.
        Для 'normal' состояния нужно использовать get_dynamic_icon.
        Доступные состояния: 'normal', 'saving', 'paused', 'error', 'inactive'.
        Это иконки для системного трея, они генерируются программно.
        """
        return self._icons.get(state, self._icons['normal'])

    def get_dynamic_icon(self, fill_percentage: float = 0.0) -> QIcon:
        """
        Генерирует и возвращает иконку для 'normal' состояния с динамической заливкой,
        цвет которой зависит от процента заполнения.
        fill_percentage: процент заполнения (0.0 до 1.0).
        """
        # Определяем цвет заливки в зависимости от процента
        if fill_percentage <= 0.25:
            fill_color = QColor("#28A745")  # Green (Bootstrap success)
        elif fill_percentage <= 0.50:
            fill_color = QColor("#FFC107")  # Yellow (Bootstrap warning)
        else:
            fill_color = QColor("#DC3545")  # Red (Bootstrap danger)

        image = self._generate_shield_icon(fill_color, fill_percentage)
        pixmap = QPixmap.fromImage(image)
        return QIcon(pixmap)


    def get_app_icon(self, dark_icon_path: str, light_icon_path: str) -> QIcon:
        """
        Возвращает адаптивную иконку приложения (из файла .ico)
        в зависимости от системной темы.
        """
        if sys.platform != 'win32':
            # Для других ОС возвращаем светлую иконку по умолчанию
            return QIcon(_resource_path(light_icon_path))

        outline_color_hex, _ = self._get_system_theme_colors()

        # Если outline_color_hex == '#FFFFFF', значит тема темная
        if outline_color_hex == '#FFFFFF':
            return QIcon(_resource_path(light_icon_path))
        else:
            return QIcon(_resource_path(dark_icon_path))
