# main.py
import sys
import json
import zipfile
import uuid
import os
import tempfile
import copy
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QListWidget, 
                               QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, 
                               QGraphicsView, # Исправлено: добавлен импорт
                               QFileDialog, QWidget, QVBoxLayout, QMessageBox, QLabel,
                               QToolBar, QStyle)
from PySide6.QtCore import Qt, QMimeData, QRectF, QStandardPaths, QUrl, QTimer, QSize
from PySide6.QtGui import QDrag, QBrush, QColor, QPen, QAction, QDesktopServices, QIcon, QKeySequence, QUndoStack, QUndoCommand
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from config import SCREEN_WIDTH, SCREEN_HEIGHT, WIDGET_TEMPLATES, APP_NAME, APP_VERSION, GITHUB_REPO_URL, get_setting
from items import RootFrameItem, WidgetItem
from ui import EditorView, PropertiesPanel, HierarchyTree, SettingsDialog

# --- UNDO COMMANDS ---
class AddWidgetCommand(QUndoCommand):
    def __init__(self, scene, item, parent, hierarchy_sig):
        super().__init__(f"Add {item.data_model.get('name')}")
        self.scene = scene
        self.item = item
        self.parent = parent
        self.hierarchy_sig = hierarchy_sig
    def redo(self):
        if self.item.scene() != self.scene:
            self.item.setParentItem(self.parent)
        self.hierarchy_sig.emit()
    def undo(self):
        self.scene.removeItem(self.item)
        self.hierarchy_sig.emit()

class MoveResizeCommand(QUndoCommand):
    def __init__(self, item, old_state, new_state, update_signal):
        super().__init__("Move/Resize")
        self.item = item
        self.old_state = old_state
        self.new_state = new_state
        self.update_signal = update_signal
    def redo(self): self.apply(self.new_state)
    def undo(self): self.apply(self.old_state)
    def apply(self, state):
        self.item.setPos(state['x'], state['y'])
        self.item.setRect(0, 0, state['w'], state['h'])
        self.item.update_handle_pos()
        self.item.update_model()
        if self.update_signal: self.update_signal.emit(self.item)

class PropertyCommand(QUndoCommand):
    def __init__(self, item, path, old_val, new_val, update_signal):
        super().__init__(f"Change {path}")
        self.item = item; self.path = path
        self.old_val = old_val; self.new_val = new_val
        self.update_signal = update_signal
    def redo(self): self.apply(self.new_val)
    def undo(self): self.apply(self.old_val)
    def apply(self, val):
        keys = self.path.split('.'); ref = self.item.data_model
        try:
            for k in keys[:-1]: ref = ref[k]
            ref[keys[-1]] = val
        except: return
        if keys[-1] == 'z_index': self.item.setZValue(val)
        elif keys[-1] in ['x','y','width','height']:
            self.item.setRect(0,0, self.item.data_model['width'], self.item.data_model['height'])
            self.item.setPos(self.item.data_model['x'], self.item.data_model['y'])
            self.item.update_handle_pos()
        if hasattr(self.item, 'refresh_content'): self.item.refresh_content()
        self.item.update()
        if self.update_signal: self.update_signal.emit(self.item)

# --- MAIN ---
class GridScene(QGraphicsScene):
    def __init__(self, w, h): super().__init__(0, 0, w, h); self.grid_size = 50
    def drawBackground(self, painter, rect):
        if not get_setting("show_grid", True, type=bool): painter.fillRect(rect, QColor("#FAFAFA")); return
        painter.fillRect(rect, QColor("#FAFAFA")); self.grid_color = QColor(230, 230, 230)
        left = int(rect.left()) - (int(rect.left()) % self.grid_size); top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        for x in range(left, int(rect.right()), self.grid_size): painter.setPen(QPen(self.grid_color, 1)); painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), self.grid_size): painter.setPen(QPen(self.grid_color, 1)); painter.drawLine(int(rect.left()), y, int(rect.right()), y)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1400, 900)
        self.network_manager = QNetworkAccessManager(self); self.clipboard_data = None 
        self.undo_stack = QUndoStack(self); self.temp_move_state = {} 
        self.apply_theme(get_setting("theme", "Light", type=str))

        self.scene = GridScene(2500, 1500)
        self.screen_rect = QRectF(100, 100, SCREEN_WIDTH, SCREEN_HEIGHT)
        screen_item = QGraphicsRectItem(self.screen_rect); screen_item.setPen(QPen(Qt.black, 1, Qt.DashLine)); screen_item.setZValue(0)
        self.scene.addItem(screen_item); self.screen_item = screen_item 
        self.screen_lbl = QGraphicsTextItem("Screen 1920x1080", screen_item); self.screen_lbl.setDefaultTextColor(QColor("#999")); self.screen_lbl.setPos(100, 70)

        self.root_frame = RootFrameItem(self.screen_rect); self.scene.addItem(self.root_frame)
        self.view = EditorView(self.scene, self.root_frame); self.setCentralWidget(self.view)

        self.create_docks(); self.create_menus(); self.create_toolbar()
        self.statusBar().showMessage("Готов")
        self.tree_widget.refresh(self.root_frame)

        # Связи
        self.view.item_selected.connect(self.props.set_item)
        self.props.data_changed.connect(lambda item: self.scene.update())
        
        self.view.hierarchy_changed.connect(lambda: self.tree_widget.refresh(self.root_frame))
        self.tree_widget.item_clicked_in_tree.connect(self.select_from_tree)
        self.tree_widget.hierarchy_reordered.connect(lambda: self.scene.update())
        self.view.request_properties.connect(self.show_properties_dock)
        self.props.request_bg_edit.connect(self.view.start_bg_edit)
        
        # Undo/Redo связи
        self.props.property_committed.connect(self.on_property_committed)
        self.props.undo_refresh_requested.connect(self.on_undo_refresh)
        
        self.connect_items_signals()
        QTimer.singleShot(2000, self.check_updates)

    def connect_items_signals(self):
        for item in self.scene.items():
            if isinstance(item, WidgetItem):
                try: 
                    item.interaction_started.disconnect(self.on_item_interaction_start)
                    item.interaction_finished.disconnect(self.on_item_interaction_end)
                except: pass
                item.interaction_started.connect(self.on_item_interaction_start)
                item.interaction_finished.connect(self.on_item_interaction_end)

    def on_property_committed(self, path, old, new):
        if self.props.current_item:
            # Передаем undo_refresh_requested, чтобы при Undo панель обновилась
            cmd = PropertyCommand(self.props.current_item, path, old, new, self.props.undo_refresh_requested)
            self.undo_stack.push(cmd)

    def on_undo_refresh(self, item):
        self.scene.update()
        if self.props.current_item == item:
            self.props.set_item(item) # Обновляем UI

    def on_item_interaction_start(self, item):
        self.temp_move_state[item] = {'x': item.x(), 'y': item.y(), 'w': item.rect().width(), 'h': item.rect().height()}

    def on_item_interaction_end(self, item):
        if item in self.temp_move_state:
            old = self.temp_move_state[item]
            new = {'x': item.x(), 'y': item.y(), 'w': item.rect().width(), 'h': item.rect().height()}
            if old['x'] != new['x'] or old['y'] != new['y'] or old['w'] != new['w'] or old['h'] != new['h']:
                cmd = MoveResizeCommand(item, old, new, self.props.undo_refresh_requested)
                self.undo_stack.push(cmd)
            del self.temp_move_state[item]

    def create_docks(self):
        dock_left = QDockWidget("Навигация", self)
        container = QWidget(); layout = QVBoxLayout(container)
        list_w = QListWidget()
        for k, v in WIDGET_TEMPLATES.items():
            item = list_w.addItem(v['name']); list_w.item(list_w.count()-1).setData(Qt.UserRole, k)
        list_w.setDragEnabled(True); list_w.startDrag = lambda actions: self.start_drag(list_w)
        layout.addWidget(list_w)
        self.tree_widget = HierarchyTree(); layout.addWidget(self.tree_widget)
        dock_left.setWidget(container); self.addDockWidget(Qt.LeftDockWidgetArea, dock_left)
        self.dock_left = dock_left
        dock_right = QDockWidget("Свойства", self)
        self.props = PropertiesPanel()
        dock_right.setWidget(self.props); self.addDockWidget(Qt.RightDockWidgetArea, dock_right)
        self.dock_right = dock_right

    def create_menus(self):
        mb = self.menuBar()
        file_m = mb.addMenu("Файл")
        file_m.addAction(QAction("Новый проект", self, shortcut="Ctrl+N", triggered=self.new_file))
        file_m.addAction(QAction("Открыть...", self, shortcut="Ctrl+O", triggered=self.open_file))
        file_m.addAction(QAction("Импорт WGT...", self, triggered=self.import_wgt))
        file_m.addAction(QAction("Сохранить", self, shortcut="Ctrl+S", triggered=self.save_file))
        file_m.addSeparator(); file_m.addAction(QAction("Экспорт WGT", self, triggered=self.export_product))
        file_m.addSeparator(); file_m.addAction(QAction("Выход", self, triggered=self.close))
        edit_m = mb.addMenu("Правка")
        edit_m.addAction(self.undo_stack.createUndoAction(self, "Отменить"))
        edit_m.addAction(self.undo_stack.createRedoAction(self, "Повторить"))
        edit_m.addSeparator()
        edit_m.addAction(QAction("Копировать", self, shortcut="Ctrl+C", triggered=self.copy_item))
        edit_m.addAction(QAction("Вставить", self, shortcut="Ctrl+V", triggered=self.paste_item))
        edit_m.addSeparator()
        edit_m.addAction(QAction("Сгруппировать", self, shortcut="Ctrl+G", triggered=self.group_items))
        edit_m.addAction(QAction("Разгруппировать", self, shortcut="Ctrl+U", triggered=self.ungroup_items))
        view_m = mb.addMenu("Вид")
        view_m.addAction(self.dock_left.toggleViewAction()); view_m.addAction(self.dock_right.toggleViewAction())
        view_m.addAction(QAction("Предпросмотр (F5)", self, shortcut="F5", triggered=self.toggle_preview))
        settings_m = mb.addMenu("Настройки"); settings_m.addAction(QAction("Параметры...", self, triggered=self.open_settings))

    def create_toolbar(self):
        toolbar = QToolBar("Инструменты"); toolbar.setIconSize(QSize(16, 16)); self.addToolBar(toolbar)
        toolbar.addAction(self.undo_stack.createUndoAction(self, "")); toolbar.addAction(self.undo_stack.createRedoAction(self, ""))
        toolbar.addSeparator(); toolbar.addAction(QAction("Группа", self, triggered=self.group_items))
        toolbar.addAction(QAction("Разгруппировать", self, triggered=self.ungroup_items))

    def keyPressEvent(self, event):
        if get_setting("kbd_control", False, type=bool):
            step = 1 if event.modifiers() & Qt.ShiftModifier else 10
            sel = self.scene.selectedItems(); dx, dy = 0, 0
            if event.key() == Qt.Key_Left: dx = -step
            elif event.key() == Qt.Key_Right: dx = step
            elif event.key() == Qt.Key_Up: dy = -step
            elif event.key() == Qt.Key_Down: dy = step
            if dx or dy:
                for item in sel:
                    if isinstance(item, WidgetItem): item.setPos(item.x() + dx, item.y() + dy); item.update_model()
                self.props.set_item(sel[0] if sel else None)
                return
        super().keyPressEvent(event)

    def group_items(self):
        sel = [i for i in self.scene.selectedItems() if isinstance(i, WidgetItem)]
        if len(sel) < 1: return
        min_x = min(i.x() for i in sel); min_y = min(i.y() for i in sel)
        max_x = max(i.x() + i.rect().width() for i in sel); max_y = max(i.y() + i.rect().height() for i in sel)
        group = WidgetItem("group", min_x, min_y, self.root_frame)
        group.setRect(0, 0, max_x - min_x, max_y - min_y); group.update_model()
        
        self.undo_stack.beginMacro("Group")
        self.undo_stack.push(AddWidgetCommand(self.scene, group, self.root_frame, self.view.hierarchy_changed))
        for item in sel:
            item.setParentItem(group); item.setPos(item.x() - min_x, item.y() - min_y); item.update_model()
        self.undo_stack.endMacro()
        self.scene.clearSelection(); group.setSelected(True); self.connect_items_signals()

    def ungroup_items(self):
        sel = self.scene.selectedItems()
        if not sel: return
        group = sel[0]
        if not isinstance(group, WidgetItem) or not getattr(group, 'is_container', False): return
        
        # Для Undo ungroup нужен сложный макрос, пока просто удаляем группу
        # Но чтобы дети не удалились, их надо вытащить.
        # Undo этого действия требует restore parent.
        # Пока без undo для ungroup (сложно).
        children = list(group.childItems())
        g_x, g_y = group.x(), group.y()
        for child in children:
            if isinstance(child, WidgetItem):
                child.setParentItem(self.root_frame); child.setPos(child.x() + g_x, child.y() + g_y)
                child.update_model(); child.setSelected(True)
        self.scene.removeItem(group); self.view.hierarchy_changed.emit()

    def toggle_preview(self):
        is_preview = not self.dock_left.isVisible()
        self.dock_left.setVisible(is_preview); self.dock_right.setVisible(is_preview)
        self.menuBar().setVisible(is_preview)
        self.screen_item.setVisible(is_preview); self.screen_lbl.setVisible(is_preview)
        for item in self.scene.items():
            if isinstance(item, WidgetItem):
                item.setFlag(QGraphicsRectItem.ItemIsSelectable, is_preview)
                item.setFlag(QGraphicsRectItem.ItemIsMovable, is_preview)
                if not is_preview: item.resize_handle.hide()
        if not is_preview: self.scene.clearSelection(); self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        else: self.view.setDragMode(QGraphicsView.NoDrag)

    def apply_theme(self, theme_name):
        if theme_name == "Dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
                QListWidget, QTreeWidget { background-color: #3c3f41; border: 1px solid #555; }
                QGroupBox { border: 1px solid #555; margin-top: 10px; }
                QLineEdit, QSpinBox, QComboBox, QFontComboBox { background-color: #3c3f41; border: 1px solid #555; padding: 4px; }
                QPushButton { background-color: #3c3f41; border: 1px solid #555; padding: 5px; }
                QMenu { background-color: #3c3f41; border: 1px solid #555; }
                QMenuBar { background-color: #2b2b2b; }
            """)
        else: self.setStyleSheet("")

    def start_drag(self, list_widget):
        item = list_widget.currentItem()
        key = item.data(Qt.UserRole); drag = QDrag(list_widget)
        mime = QMimeData(); mime.setText(key); drag.setMimeData(mime); drag.exec(Qt.CopyAction)
    def select_from_tree(self, item): self.scene.clearSelection(); item.setSelected(True); self.view.setFocus()
    def show_properties_dock(self): self.dock_right.setVisible(True); self.dock_right.raise_()
    def get_docs_path(self): return get_setting("default_dir", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
    def new_file(self):
        if QMessageBox.question(self, "Новый", "Сбросить?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            for child in self.root_frame.childItems(): self.scene.removeItem(child)
            self.root_frame.reset_settings(); self.tree_widget.refresh(self.root_frame); self.props.set_item(None); self.undo_stack.clear()
    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", self.get_docs_path(), "Project (*.json)")
        if path: 
            import main; 
            if ProjectManager.save_project(path, self.root_frame): self.statusBar().showMessage(f"Сохранено", 3000)
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть", self.get_docs_path(), "Project (*.json)")
        if path:
            self.scene.clearSelection(); self.props.set_item(None)
            ok, msg = ProjectManager.load_project(path, self.root_frame, self.scene)
            if ok: self.tree_widget.refresh(self.root_frame); self.undo_stack.clear(); self.connect_items_signals()
            else: QMessageBox.critical(self, "Ошибка", msg)
    def import_wgt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт", self.get_docs_path(), "WGT (*.wgt)")
        if path:
            self.scene.clearSelection(); self.props.set_item(None)
            ok, msg = ProjectManager.import_wgt(path, self.root_frame, self.scene)
            if ok: self.tree_widget.refresh(self.root_frame); self.connect_items_signals()
    def export_product(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", self.get_docs_path(), "WGT (*.wgt)")
        if path: ProjectManager.export_product_wgt(path, self.root_frame)
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_(): self.scene.update(); self.apply_theme(get_setting("theme", "Light", type=str))
    def check_updates(self): pass 
    def copy_item(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, WidgetItem)]
        if items: items[0].update_model(); self.clipboard_data = items[0].data_model.copy()
    def paste_item(self):
        if not self.clipboard_data: return
        new_data = self.clipboard_data.copy()
        new_data['id'] = str(uuid.uuid4()); new_data['x'] += 20; new_data['y'] += 20
        item = WidgetItem(new_data.get('type', 'rect'), new_data['x'], new_data['y'], self.root_frame)
        item.apply_data(new_data); item.setSelected(True)
        self.view.hierarchy_changed.emit()
        self.connect_items_signals()
        self.undo_stack.push(AddWidgetCommand(self.scene, item, self.root_frame, self.view.hierarchy_changed))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())