# ui.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLineEdit, QSpinBox, 
                               QPushButton, QColorDialog, QGroupBox, QGraphicsView, 
                               QMenu, QMessageBox, QTreeWidget, QTreeWidgetItem, QLabel,
                               QAbstractItemView, QFileDialog, QCheckBox, QDoubleSpinBox,
                               QHBoxLayout, QDialog, QFormLayout, QFrame, QComboBox, QFontComboBox,
                               QScrollArea)
from PySide6.QtCore import Qt, Signal, QEvent, QStandardPaths, QSettings
from PySide6.QtGui import QAction, QPainter, QMouseEvent

from items import RootFrameItem, WidgetItem, BaseResizableItem, BgImageGizmo
from config import APP_VERSION, APP_NAME, THEMES

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setFixedSize(450, 450)
        self.settings = QSettings("Overl1te", "ChronoBuilder")
        layout = QVBoxLayout(self)
        
        group_path = QGroupBox("Пути")
        form_path = QFormLayout(group_path)
        self.path_edit = QLineEdit(self.settings.value("default_dir", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)))
        btn_path = QPushButton("...")
        btn_path.clicked.connect(self.browse_path)
        h = QHBoxLayout()
        h.addWidget(self.path_edit)
        h.addWidget(btn_path)
        form_path.addRow("Папка проектов:", h)
        layout.addWidget(group_path)
        
        group_gen = QGroupBox("Общие")
        form = QFormLayout(group_gen)
        self.cb_autosave = QCheckBox("Включить автосохранение")
        self.cb_autosave.setChecked(self.settings.value("autosave", True, type=bool))
        form.addRow(self.cb_autosave)
        self.cb_grid = QCheckBox("Показывать сетку")
        self.cb_grid.setChecked(self.settings.value("show_grid", True, type=bool))
        form.addRow(self.cb_grid)
        self.cb_kbd = QCheckBox("Клавиатурное управление")
        self.cb_kbd.setChecked(self.settings.value("kbd_control", False, type=bool))
        form.addRow(self.cb_kbd)
        layout.addWidget(group_gen)

        group_theme = QGroupBox("Внешний вид")
        form_t = QFormLayout(group_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Light", "Dark"])
        curr = self.settings.value("theme", "Light")
        self.combo_theme.setCurrentText(curr)
        form_t.addRow("Тема редактора:", self.combo_theme)
        layout.addWidget(group_theme)
        
        layout.addStretch()
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        lbl_ver = QLabel(f"{APP_NAME} {APP_VERSION}")
        lbl_ver.setAlignment(Qt.AlignCenter)
        lbl_ver.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl_ver)

        btns = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_settings)
        btn_close = QPushButton("Отмена")
        btn_close.clicked.connect(self.reject)
        btns.addWidget(btn_save)
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "Выбрать папку", self.path_edit.text())
        if d: self.path_edit.setText(d)
    def save_settings(self):
        self.settings.setValue("default_dir", self.path_edit.text())
        self.settings.setValue("autosave", self.cb_autosave.isChecked())
        self.settings.setValue("show_grid", self.cb_grid.isChecked())
        self.settings.setValue("kbd_control", self.cb_kbd.isChecked())
        self.settings.setValue("theme", self.combo_theme.currentText())
        self.accept()

class HierarchyTree(QTreeWidget):
    item_clicked_in_tree = Signal(object)
    hierarchy_reordered = Signal()
    
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Имя", "🔒", "👁"])
        self.setColumnWidth(0, 140)
        self.setColumnWidth(1, 30)
        self.setColumnWidth(2, 30)
        self.itemClicked.connect(self.on_click)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
    
    def dropEvent(self, event):
        super().dropEvent(event)
        self.sync_scene_from_tree()
        self.hierarchy_reordered.emit()
        
    def sync_scene_from_tree(self):
        self.recursive_sync(self.invisibleRootItem(), None)
        
    def recursive_sync(self, tree_item, parent_gfx_item):
        count = tree_item.childCount()
        for i in range(count):
            child = tree_item.child(i)
            gfx = child.data(0, Qt.UserRole)
            if gfx:
                if not isinstance(gfx, RootFrameItem) and gfx.parentItem() != parent_gfx_item:
                    gfx.setParentItem(parent_gfx_item)
                gfx.setZValue(count - i)
                self.recursive_sync(child, gfx)
                
    def refresh(self, root_frame):
        if self.state() == QAbstractItemView.DraggingState: return
        self.clear()
        self.blockSignals(True)
        root = QTreeWidgetItem(["Root Frame", "", ""])
        root.setData(0, Qt.UserRole, root_frame)
        self.addTopLevelItem(root)
        root.setExpanded(True)
        self.add_children_recursive(root_frame, root)
        self.blockSignals(False)
        
    def add_children_recursive(self, parent_item, parent_node):
        children = list(parent_item.childItems())
        children.sort(key=lambda x: x.zValue(), reverse=True)
        for child in children:
            if isinstance(child, WidgetItem):
                lock = "🔒" if child.is_locked else "🔓"
                vis = "👁" if child.isVisible() else "🚫"
                node = QTreeWidgetItem([child.data_model.get('name', 'Widget'), lock, vis])
                node.setData(0, Qt.UserRole, child)
                node.setTextAlignment(1, Qt.AlignCenter)
                node.setTextAlignment(2, Qt.AlignCenter)
                parent_node.addChild(node)
                node.setExpanded(True)
                if getattr(child, 'is_container', False):
                    self.add_children_recursive(child, node)
                    
    def on_click(self, item, col):
        gfx = item.data(0, Qt.UserRole)
        if not gfx: return
        if col == 1: # Lock
            if isinstance(gfx, RootFrameItem): return
            gfx.is_locked = not getattr(gfx, 'is_locked', False)
            item.setText(1, "🔒" if gfx.is_locked else "🔓")
            gfx.update_flags()
        elif col == 2: # Hide
            vis = not gfx.isVisible()
            gfx.setVisible(vis)
            item.setText(2, "👁" if vis else "🚫")
        else:
            self.item_clicked_in_tree.emit(gfx)

class PropertiesPanel(QWidget):
    data_changed = Signal(object)
    property_committed = Signal(str, object, object)
    undo_refresh_requested = Signal(object)
    request_bg_edit = Signal(object)

    def __init__(self):
        super().__init__()
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        scroll.setWidget(self.content_widget)
        self.outer_layout.addWidget(scroll)
        
        self.current_item = None
        self.gradient_widgets = {} 

    def set_item(self, item):
        self.current_item = item
        self.gradient_widgets.clear()
        
        # Исправленная очистка (развернутый цикл)
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not item: 
            lbl = QLabel("Нет выделения")
            lbl.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(lbl)
            return

        title = QLabel(item.data_model.get('name', 'Element'))
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)
        
        common_g = QGroupBox("Параметры")
        common_l = QGridLayout(common_g)
        common_l.addWidget(QLabel("Z-Index"), 0, 0)
        sb_z = QSpinBox()
        sb_z.setRange(-999, 999)
        sb_z.setValue(int(item.zValue()))
        sb_z.valueChanged.connect(lambda v: self.commit_prop("z_index", self.current_item.zValue(), v))
        common_l.addWidget(sb_z, 0, 1)
        self.layout.addWidget(common_g)

        self.build_ui(item.data_model)
        self.add_action_buttons(item)
        self.layout.addStretch()

    def build_ui(self, data):
        grid = QGridLayout()
        grid.addWidget(QLabel("X"), 0, 0)
        grid.addWidget(self.make_spin(data['x'], "x"), 0, 1)
        grid.addWidget(QLabel("Y"), 0, 2)
        grid.addWidget(self.make_spin(data['y'], "y"), 0, 3)
        grid.addWidget(QLabel("W"), 1, 0)
        grid.addWidget(self.make_spin(data['width'], "width"), 1, 1)
        grid.addWidget(QLabel("H"), 1, 2)
        grid.addWidget(self.make_spin(data['height'], "height"), 1, 3)
        
        container = QWidget()
        container.setLayout(grid)
        self.layout.addWidget(container)

        if 'style' in data: self.create_group("Стиль", data['style'], "style")
        if 'content' in data: self.create_group("Контент", data['content'], "content")

    def create_group(self, title, data_dict, prefix):
        group = QGroupBox(title)
        form = QGridLayout()
        row = 0
        
        grad_keys = ["grad_start", "grad_end", "grad_angle"]
        text_grad_keys = ["text_grad_start", "text_grad_end", "text_grad_angle"]
        widgets_to_hide = {}

        for k, v in data_dict.items():
            path = f"{prefix}.{k}"
            if k in ['bg_x', 'bg_y', 'bg_w', 'bg_h']: continue

            widget = None
            if k == "font_family":
                widget = QFontComboBox()
                widget.setCurrentText(str(v))
                widget.currentFontChanged.connect(lambda f, p=path, old=v: self.commit_prop(p, old, f.family()))
            elif k in ["use_gradient", "use_text_gradient"]:
                widget = QCheckBox()
                widget.setChecked(v)
                widget.stateChanged.connect(lambda val, p=path, old=v: self.commit_prop(p, old, bool(val)))
            elif k == "bg_image":
                widget = QWidget()
                hl = QHBoxLayout(widget)
                hl.setContentsMargins(0,0,0,0)
                le = QLineEdit(str(v))
                le.editingFinished.connect(lambda l=le, p=path, old=v: self.commit_prop(p, old, l.text()))
                btn_file = QPushButton("...")
                btn_file.setMaximumWidth(30)
                btn_file.clicked.connect(lambda _, l=le: self.pick_file(l))
                btn_edit = QPushButton("⛶")
                btn_edit.setToolTip("Позиция")
                btn_edit.setMaximumWidth(30)
                btn_edit.clicked.connect(lambda: self.request_bg_edit.emit(self.current_item))
                btn_reset = QPushButton("↺")
                btn_reset.setToolTip("Сброс")
                btn_reset.setMaximumWidth(30)
                btn_reset.clicked.connect(self.reset_bg_geo)
                hl.addWidget(le); hl.addWidget(btn_file); hl.addWidget(btn_edit); hl.addWidget(btn_reset)
            elif "angle" in k or k in ["value", "max_value"]:
                widget = QSpinBox()
                widget.setRange(0, 9999)
                if "angle" in k: 
                    widget.setSuffix("°")
                    widget.setRange(0, 360)
                widget.setValue(int(v))
                widget.valueChanged.connect(lambda val, p=path, old=v: self.commit_prop(p, old, val))
            elif "color" in k or "start" in k or "end" in k:
                if isinstance(v, str) and v.startswith("#"):
                    widget = QPushButton(str(v))
                    widget.setStyleSheet(f"background: {v}; color: #555; border: 1px solid #999;")
                    widget.clicked.connect(lambda _, b=widget, p=path, old=v: self.pick_color(b, p, old))
            elif isinstance(v, bool):
                widget = QCheckBox()
                widget.setChecked(v)
                widget.stateChanged.connect(lambda val, p=path, old=v: self.commit_prop(p, old, bool(val)))
            elif isinstance(v, float):
                widget = QDoubleSpinBox()
                widget.setRange(0.0, 1.0)
                widget.setSingleStep(0.1)
                widget.setValue(v)
                widget.valueChanged.connect(lambda val, p=path, old=v: self.commit_prop(p, old, val))
            elif isinstance(v, int): 
                widget = self.make_spin(v, path)
            elif isinstance(v, str): 
                widget = QLineEdit(str(v))
                widget.editingFinished.connect(lambda l=widget, p=path, old=v: self.commit_prop(p, old, l.text()))

            if widget:
                lbl = QLabel(k.replace("_", " ").title())
                form.addWidget(lbl, row, 0)
                form.addWidget(widget, row, 1)
                full_key = f"{prefix}.{k}"
                if k in grad_keys or k in text_grad_keys: 
                    widgets_to_hide[full_key] = (lbl, widget)
                row += 1
        
        group.setLayout(form)
        self.layout.addWidget(group)
        
        is_grad = data_dict.get("use_gradient", False)
        for k in grad_keys:
            fk = f"{prefix}.{k}"
            if fk in widgets_to_hide: 
                widgets_to_hide[fk][0].setVisible(is_grad)
                widgets_to_hide[fk][1].setVisible(is_grad)
                
        is_text_grad = data_dict.get("use_text_gradient", False)
        for k in text_grad_keys:
            fk = f"{prefix}.{k}"
            if fk in widgets_to_hide: 
                widgets_to_hide[fk][0].setVisible(is_text_grad)
                widgets_to_hide[fk][1].setVisible(is_text_grad)

    def make_spin(self, val, path):
        sb = QSpinBox()
        sb.setRange(-9999, 9999)
        sb.setValue(int(val))
        sb.valueChanged.connect(lambda v, p=path: self.update_data(p, v))
        return sb

    def commit_prop(self, path, old_val, new_val):
        if old_val == new_val: return
        self.property_committed.emit(path, old_val, new_val)

    def pick_color(self, btn, path, old_val):
        c = QColorDialog.getColor(initial=QColor(old_val))
        if c.isValid(): 
            new_val = c.name()
            btn.setText(new_val)
            btn.setStyleSheet(f"background: {new_val}; color: #555; border: 1px solid #999;")
            self.commit_prop(path, old_val, new_val)
            self.update_data(path, new_val)

    def pick_file(self, line_edit):
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать", docs, "Img (*.png *.jpg *.jpeg *.svg)")
        if path: 
            line_edit.setText(path)
            line_edit.editingFinished.emit()

    def reset_bg_geo(self):
        if not self.current_item: return
        self.update_data("style.bg_x", 0)
        self.update_data("style.bg_y", 0)
        self.update_data("style.bg_w", 0)
        self.update_data("style.bg_h", 0)

    def update_data(self, path, value):
        if not self.current_item: return
        keys = path.split('.')
        ref = self.current_item.data_model
        try:
            for k in keys[:-1]: 
                ref = ref[k]
            ref[keys[-1]] = value
        except KeyError: return
        
        if keys[-1] in ['width', 'height', 'x', 'y']:
            self.current_item.setRect(0, 0, self.current_item.data_model['width'], self.current_item.data_model['height'])
            self.current_item.setPos(self.current_item.data_model['x'], self.current_item.data_model['y'])
            self.current_item.update_handle_pos()
            
        if hasattr(self.current_item, 'refresh_content'): 
            self.current_item.refresh_content()
            
        self.current_item.update()
        self.data_changed.emit(self.current_item)

    def add_action_buttons(self, item):
        self.layout.addSpacing(10)
        if isinstance(item, RootFrameItem):
            btn = QPushButton("Сброс Frame")
            btn.clicked.connect(lambda: item.reset_settings() or self.set_item(item))
            self.layout.addWidget(btn)
        else:
            btn = QPushButton("Удалить")
            btn.setStyleSheet("background-color: #e74c3c; color: white;")
            btn.clicked.connect(self.delete_widget)
            self.layout.addWidget(btn)

    def delete_widget(self):
        if self.current_item and not isinstance(self.current_item, RootFrameItem):
            scene = self.current_item.scene()
            scene.removeItem(self.current_item)
            self.set_item(None)

class EditorView(QGraphicsView):
    item_selected = Signal(object)
    item_deleted = Signal()
    hierarchy_changed = Signal()
    request_properties = Signal()
    
    def __init__(self, scene, root_frame):
        super().__init__(scene)
        self.root_frame = root_frame
        self.setAcceptDrops(True)
        self.scene().selectionChanged.connect(self.on_selection)
        self.bg_gizmo = None
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoom_in = event.angleDelta().y() > 0
            scale_factor = 1.1 if zoom_in else 0.9
            self.scale(scale_factor, scale_factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake = QMouseEvent(QEvent.MouseButtonPress, event.position(), event.globalPosition(), 
                               Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mousePressEvent(fake)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            fake = QMouseEvent(QEvent.MouseButtonRelease, event.position(), event.globalPosition(), 
                               Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mouseReleaseEvent(fake)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif event.key() == Qt.Key_Delete:
            items = self.scene().selectedItems()
            changed = False
            for i in items:
                if isinstance(i, BgImageGizmo): continue
                if isinstance(i, WidgetItem): 
                    if i.is_locked: continue
                    self.scene().removeItem(i)
                    changed = True
            if changed:
                self.item_selected.emit(None)
                self.item_deleted.emit()
                self.hierarchy_changed.emit()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.RubberBandDrag)
        super().keyReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        key = event.mimeData().text()
        scene_pos = self.mapToScene(event.position().toPoint())
        self.scene().clearSelection()
        items = self.scene().items(scene_pos)
        parent = next((i for i in items if isinstance(i, RootFrameItem) or 
                       (isinstance(i, WidgetItem) and getattr(i, 'is_container', False))), self.root_frame)
        
        if isinstance(parent, WidgetItem) and parent.is_locked:
            parent = self.root_frame
            
        local_pos = parent.mapFromScene(scene_pos)
        if parent.contains(local_pos):
            item = WidgetItem(key, local_pos.x(), local_pos.y(), parent)
            item.setPos(item.constrain_position(item.pos()))
            item.setSelected(True)
            self.hierarchy_changed.emit()
            event.accept()
        else:
            event.ignore()

    def on_selection(self):
        if self.bg_gizmo:
            sel = self.scene().selectedItems()
            if not sel or sel[0] != self.bg_gizmo:
                self.remove_gizmo()
        
        sel = self.scene().selectedItems()
        real = [i for i in sel if isinstance(i, BaseResizableItem)]
        self.item_selected.emit(real[0] if real else None)

    def contextMenuEvent(self, event):
        item = self.scene().itemAt(self.mapToScene(event.pos()), self.transform())
        target = item
        while target and not isinstance(target, BaseResizableItem):
            target = target.parentItem()
        
        if not target: return
        
        menu = QMenu(self)
        menu.addAction("Свойства", lambda: self.open_properties(target))
        menu.addSeparator()
        
        if isinstance(target, RootFrameItem):
            menu.addAction("Сброс", target.reset_settings)
        elif isinstance(target, WidgetItem):
            if not target.is_locked:
                menu.addAction("Удалить", lambda: self.delete_item_safe(target))
        
        menu.exec(event.globalPos())

    def open_properties(self, item):
        if not item.isSelected():
            self.scene().clearSelection()
            item.setSelected(True)
        self.request_properties.emit()

    def delete_item_safe(self, item):
        self.scene().removeItem(item)
        self.item_selected.emit(None)
        self.hierarchy_changed.emit()
    
    def start_bg_edit(self, item):
        self.remove_gizmo()
        path = item.data_model['style'].get('bg_image', '')
        if not path: return
        
        self.bg_gizmo = BgImageGizmo(item, path, self.scene())
        self.scene().addItem(self.bg_gizmo)
        self.scene().clearSelection()
        self.bg_gizmo.setSelected(True)

    def remove_gizmo(self):
        if self.bg_gizmo:
            self.bg_gizmo.target.update()
            self.scene().removeItem(self.bg_gizmo)
            self.bg_gizmo = None