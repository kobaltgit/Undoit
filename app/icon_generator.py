# -*- coding: utf-8 -*-
# Генератор иконок-щитов
import sys
import winreg
from typing import Dict, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QImage, QPainter,
                           QPainterPath, QPen, QPixmap)


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
        """
        # Проверяем, что мы на Windows
        if sys.platform != 'win32':
            return '#000000', '#0078D4' # Возвращаем значения по умолчанию для других ОС

        outline_color = '#000000'  # Черный для светлой темы
        accent_color_hex = '#0078D4'  # Стандартный синий Windows

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
            r = accent_color_dw & 0xff
            accent_color_hex = f'#{r:02x}{g:02x}{b:02x}'
            winreg.CloseKey(key)
        except Exception:
            # В случае ошибки (например, нестандартная тема) используем значения по умолчанию
            pass

        return outline_color, accent_color_hex

    def _generate_shield_icon(self, fill_color: QColor) -> QImage:
        """
        Основная функция, которая рисует одну иконку с заданной заливкой.
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

        # Настройка кисти (заливки)
        painter.setBrush(QBrush(fill_color))

        # Создание формы щита (буквы 'U') с помощью QPainterPath
        path = QPainterPath()
        path.moveTo(20 * scale, 15 * scale) # Верхний левый угол
        path.lineTo(20 * scale, 65 * scale) # Левая вертикальная линия
        # Нижняя дуга в прямоугольнике (x=20, y=40, w=60, h=50)
        path.arcTo(20 * scale, 40 * scale, 60 * scale, 50 * scale, 180, 180)
        path.lineTo(80 * scale, 15 * scale) # Правая вертикальная линия

        painter.drawPath(path)
        painter.end()

        return image

    def generate_all_icons(self):
        """
        Генерирует и кэширует все состояния иконок.
        """
        _, accent_color_hex = self._get_system_theme_colors()

        state_colors = {
            'normal': Qt.GlobalColor.transparent,
            'saving': QColor(accent_color_hex),
            'paused': QColor('#808080'),  # Серый
            'error': QColor('#D32F2F')   # Насыщенный красный
        }

        for state, color in state_colors.items():
            image = self._generate_shield_icon(color)
            pixmap = QPixmap.fromImage(image)
            self._icons[state] = QIcon(pixmap)

    def get_icon(self, state: str) -> QIcon:
        """
        Возвращает готовую QIcon для заданного состояния.
        Доступные состояния: 'normal', 'saving', 'paused', 'error'.
        """
        return self._icons.get(state, self._icons['normal'])