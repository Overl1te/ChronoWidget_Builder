# config.py
import os
from PySide6.QtCore import QSettings

APP_NAME = "ChronoDash Builder"
APP_VERSION = "v1.0.0"
GITHUB_REPO_URL = "https://api.github.com/repos/Overl1te/ChronoWidget_Builder/releases/latest"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

def get_setting(key, default, type=None):
    s = QSettings("Overl1te", "ChronoBuilder")
    if type: return s.value(key, default, type=type)
    return s.value(key, default)

def set_setting(key, value):
    s = QSettings("Overl1te", "ChronoBuilder")
    s.setValue(key, value)

WIDGET_TEMPLATES = {
    "group": { 
        "type": "group", "name": "Группа", "width": 100, "height": 100,
        "is_container": True, "z_index": 0,
        "style": {"bg_color": "transparent", "opacity": 1.0, "border_width": 0, "radius": 0},
        "content": {}
    },
    "rect": {
        "type": "rect", "name": "Блок", "width": 200, "height": 200,
        "is_container": True, "z_index": 0,
        "style": {
            "bg_color": "#ffffff", "bg_image": "", "bg_x": 0, "bg_y": 0, "bg_w": 0, "bg_h": 0,
            "use_gradient": False, "grad_start": "#ffffff", "grad_end": "#cccccc", "grad_angle": 90,
            "opacity": 1.0, "radius": 0, "border_width": 1, "border_color": "#000000"
        }, "content": {}
    },
    "circle": {
        "type": "rect", "name": "Круг", "width": 150, "height": 150,
        "is_container": True, "z_index": 0,
        "style": {
            "bg_color": "#3498db", "bg_image": "", "bg_x": 0, "bg_y": 0, "bg_w": 0, "bg_h": 0,
            "use_gradient": False, "grad_start": "#3498db", "grad_end": "#2980b9", "grad_angle": 45,
            "opacity": 1.0, "radius": 9999, # Большой радиус делает круг
            "border_width": 0, "border_color": "#000000"
        }, "content": {}
    },
    "image": {
        "type": "rect", "name": "Картинка", "width": 200, "height": 200,
        "is_container": False, "z_index": 0,
        "style": {
            "bg_color": "transparent", "bg_image": "", # Сюда пользователь выберет файл
            "bg_x": 0, "bg_y": 0, "bg_w": 0, "bg_h": 0,
            "opacity": 1.0, "radius": 0, "border_width": 0, "border_color": "#000000"
        }, "content": {}
    },
    "progress": {
        "type": "progress", "name": "Прогресс-бар", "width": 300, "height": 30,
        "is_container": False, "z_index": 0,
        "style": {
            "bg_color": "#333333", # Фон трека
            "opacity": 1.0, "radius": 15, 
            "border_width": 0, "border_color": "#000000"
        },
        "content": {
            "value": 50, # Текущее значение
            "max_value": 100,
            "bar_color": "#00ff88", # Цвет заполнения
            "use_gradient": False, "grad_start": "#00ff88", "grad_end": "#00aa55", "grad_angle": 90
        }
    },
    "text": {
        "type": "text", "name": "Текст", "width": 150, "height": 50,
        "is_container": False, "z_index": 0,
        "style": {"bg_color": "#ffffff", "opacity": 0.0, "radius": 0, "border_width": 0, "border_color": "#000000"},
        "content": {
            "text": "Label", "font_family": "Arial", "font_size": 14, "color": "#000000",
            "use_text_gradient": False, "text_grad_start": "#000000", "text_grad_end": "#555555", "text_grad_angle": 90
        }
    },
    "clock": {
        "type": "clock", "name": "Часы", "width": 200, "height": 80,
        "is_container": False, "z_index": 0,
        "style": {"bg_color": "#000000", "opacity": 0.8, "radius": 10, "border_width": 0, "border_color": "#ffffff"},
        "content": {
            "format": "HH:mm", "font_family": "Arial", "font_size": 32, "color": "#ffffff",
            "use_text_gradient": False, "text_grad_start": "#ffffff", "text_grad_end": "#aaaaaa", "text_grad_angle": 90
        }
    },
    "date": {
        "type": "date", "name": "Дата", "width": 200, "height": 50,
        "is_container": False, "z_index": 0,
        "style": {"bg_color": "#ffffff", "opacity": 0.0, "radius": 0, "border_width": 0, "border_color": "#000000"},
        "content": {
            "format": "%A, %d %B", # Формат даты
            "locale": "en_US", # Можно расширить в будущем
            "font_family": "Arial", "font_size": 18, "color": "#000000",
            "use_text_gradient": False, "text_grad_start": "#000000", "text_grad_end": "#555555", "text_grad_angle": 90
        }
    }
}