# config.py
import os
from PySide6.QtCore import QSettings

APP_NAME = "ChronoDash Builder"
APP_VERSION = "v1.2.0"
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

# --- ТЕМЫ (VS Code Style) ---
THEMES = {
    "Dark": """
        QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI', sans-serif; }
        QDockWidget { titlebar-close-icon: url(close.png); border: 1px solid #2d2d2d; }
        QDockWidget::title { background: #252526; padding-left: 5px; padding-top: 4px; }
        QListWidget, QTreeWidget { background-color: #252526; border: 1px solid #3e3e3e; outline: none; color: #cccccc; }
        QHeaderView::section { background-color: #333333; color: #cccccc; border: none; padding: 4px; }
        QTreeWidget::item:selected, QListWidget::item:selected { background-color: #37373d; color: #ffffff; }
        QTreeWidget::item:hover, QListWidget::item:hover { background-color: #2a2d2e; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox { 
            background-color: #3c3c3c; border: 1px solid #3c3c3c; border-radius: 4px; color: #f0f0f0; padding: 4px; selection-background-color: #264f78;
        }
        QLineEdit:focus, QSpinBox:focus { border: 1px solid #007fd4; }
        QPushButton { background-color: #0e639c; color: white; border: none; border-radius: 3px; padding: 6px 12px; }
        QPushButton:hover { background-color: #1177bb; }
        QPushButton:pressed { background-color: #0d5280; }
        QMenuBar { background-color: #333333; border-bottom: 1px solid #252526; }
        QMenuBar::item:selected { background-color: #505050; }
        QMenu { background-color: #252526; border: 1px solid #454545; }
        QMenu::item:selected { background-color: #094771; }
        QToolBar { background: #333333; border-bottom: 1px solid #252526; spacing: 5px; padding: 5px;}
        QGroupBox { border: 1px solid #3e3e3e; border-radius: 5px; margin-top: 20px; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; color: #888; }
        QScrollBar:vertical { border: none; background: #1e1e1e; width: 10px; margin: 0; }
        QScrollBar::handle:vertical { background: #424242; min-height: 20px; border-radius: 5px; }
        QScrollBar:horizontal { border: none; background: #1e1e1e; height: 10px; margin: 0; }
        QScrollBar::handle:horizontal { background: #424242; min-width: 20px; border-radius: 5px; }
    """,
    "Light": """
        QMainWindow, QWidget { background-color: #f3f3f3; color: #333333; font-family: 'Segoe UI', sans-serif; }
        QDockWidget { border: 1px solid #d4d4d4; }
        QDockWidget::title { background: #e5e5e5; padding: 5px; }
        QListWidget, QTreeWidget { background-color: #ffffff; border: 1px solid #d4d4d4; color: #333; }
        QHeaderView::section { background-color: #e5e5e5; border: none; padding: 4px; }
        QTreeWidget::item:selected { background-color: #e8e8e8; color: #000; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QFontComboBox { background-color: #ffffff; border: 1px solid #cccccc; border-radius: 4px; color: #333; padding: 4px; }
        QLineEdit:focus { border: 1px solid #007fd4; }
        QPushButton { background-color: #007fd4; color: white; border: none; border-radius: 3px; padding: 6px 12px; }
        QPushButton:hover { background-color: #0060a0; }
        QMenuBar { background-color: #dddddd; }
        QMenu { background-color: #ffffff; border: 1px solid #cccccc; }
        QToolBar { background: #e5e5e5; border-bottom: 1px solid #cccccc; }
        QGroupBox { border: 1px solid #cccccc; border-radius: 5px; margin-top: 20px; font-weight: bold; }
        QGroupBox::title { color: #555; }
    """
}

WIDGET_TEMPLATES = {
    "group": { 
        "type": "group", "name": "Группа", "width": 200, "height": 200,
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
        "type": "circle", "name": "Круг", "width": 150, "height": 150,
        "is_container": True, "z_index": 0,
        "style": {
            "bg_color": "#3498db", "bg_image": "", "bg_x": 0, "bg_y": 0, "bg_w": 0, "bg_h": 0,
            "use_gradient": False, "grad_start": "#3498db", "grad_end": "#2980b9", "grad_angle": 45,
            "opacity": 1.0, "radius": 0,
            "border_width": 0, "border_color": "#000000"
        }, "content": {}
    },
    "image": {
        "type": "image", "name": "Картинка", "width": 200, "height": 200,
        "is_container": False, "z_index": 0,
        "style": {
            "bg_color": "transparent", "bg_image": "", "bg_x": 0, "bg_y": 0, "bg_w": 0, "bg_h": 0,
            "opacity": 1.0, "radius": 0, "border_width": 0, "border_color": "#000000"
        }, "content": {}
    },
    "progress": {
        "type": "progress", "name": "Прогресс", "width": 300, "height": 20,
        "is_container": False, "z_index": 0,
        "style": {
            "bg_color": "#333333", "opacity": 1.0, "radius": 10, 
            "border_width": 0, "border_color": "#000000"
        },
        "content": {
            "value": 65, "max_value": 100, "bar_color": "#00ff88",
            "use_gradient": False, "grad_start": "#00ff88", "grad_end": "#00aa55", "grad_angle": 0
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
            "format": "%A, %d %b", "font_family": "Arial", "font_size": 18, "color": "#000000",
            "use_text_gradient": False, "text_grad_start": "#000000", "text_grad_end": "#555555", "text_grad_angle": 90
        }
    }
}