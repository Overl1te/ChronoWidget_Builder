# items.py
import json
import uuid
import os
import math
import copy
from datetime import datetime
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QGraphicsObject
from PySide6.QtCore import Qt, QPointF, QTimer, QRectF, QRect, Signal
from PySide6.QtGui import QBrush, QPen, QColor, QFont, QLinearGradient, QPixmap, QPainter, QPainterPath

from config import WIDGET_TEMPLATES

# --- УЛУЧШЕННАЯ РУЧКА ---
class HandleItem(QGraphicsRectItem):
    def __init__(self, parent):
        super().__init__(-6, -6, 12, 12, parent)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#007fd4"), 2))
        self.setFlags(QGraphicsItem.ItemIsMovable)
        self.setZValue(999)
        
    def paint(self, painter, option, widget):
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(self.rect())

    def mousePressEvent(self, event):
        self.parentItem().notify_interaction_start()
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.parentItem().notify_interaction_end()
    def mouseMoveEvent(self, event):
        self.parentItem().handle_resize(event.scenePos())

class BaseResizableItem(QGraphicsObject):
    interaction_started = Signal(object)
    interaction_finished = Signal(object)

    def __init__(self, x, y, w, h, parent=None):
        super().__init__(parent)
        self.rect_geom = QRectF(0, 0, w, h)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.resize_handle = HandleItem(self)
        self.update_handle_pos()
        self.resize_handle.hide()
        self.uid = str(uuid.uuid4())
        self.data_model = {"id": self.uid}
        self.is_locked = False 

    def rect(self): return self.rect_geom
    def setRect(self, x, y, w, h):
        self.rect_geom = QRectF(x, y, w, h)
        self.prepareGeometryChange()
        self.update()
    def boundingRect(self): 
        return self.rect_geom.adjusted(-8, -8, 8, 8)
    def update_handle_pos(self): 
        self.resize_handle.setPos(self.rect().width(), self.rect().height())
    
    def update_flags(self):
        if self.is_locked:
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False) 
            self.resize_handle.hide()
        else:
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, True)
            if self.isSelected(): self.resize_handle.show()

    def mousePressEvent(self, event):
        if not self.is_locked: self.notify_interaction_start()
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if not self.is_locked: self.notify_interaction_end()
    def notify_interaction_start(self): self.interaction_started.emit(self)
    def notify_interaction_end(self): self.interaction_finished.emit(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value and not self.is_locked: self.resize_handle.show()
            else: self.resize_handle.hide()
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            return self.constrain_position(value)
        return super().itemChange(change, value)

    def constrain_position(self, pos):
        parent_item = self.parentItem()
        if not parent_item: return pos 
        p_rect = parent_item.rect() if hasattr(parent_item, 'rect') else parent_item.boundingRect()
        x, y = pos.x(), pos.y()
        w, h = self.rect().width(), self.rect().height()
        if x < 0: x = 0
        if y < 0: y = 0
        if x + w > p_rect.width(): x = p_rect.width() - w
        if y + h > p_rect.height(): y = p_rect.height() - h
        return QPointF(x, y)

    def handle_resize(self, scene_pos):
        local_pos = self.mapFromScene(scene_pos)
        new_w = max(20, local_pos.x())
        new_h = max(20, local_pos.y())
        if self.parentItem():
            p_rect = self.parentItem().rect() if hasattr(self.parentItem(), 'rect') else self.parentItem().boundingRect()
            if self.x() + new_w > p_rect.width(): new_w = p_rect.width() - self.x()
            if self.y() + new_h > p_rect.height(): new_h = p_rect.height() - self.y()
        self.setRect(0, 0, new_w, new_h)
        self.update_handle_pos()
        self.update_model()
    
    def update_model(self):
        self.data_model['x'] = int(self.x())
        self.data_model['y'] = int(self.y())
        self.data_model['width'] = int(self.rect().width())
        self.data_model['height'] = int(self.rect().height())

    def apply_data(self, data):
        self.data_model = copy.deepcopy(data)
        self.uid = data.get('id', self.uid)
        self.setPos(data.get('x', 0), data.get('y', 0))
        self.setZValue(data.get('z_index', 0))
        self.setRect(0, 0, data.get('width', 100), data.get('height', 100))
        self.update_handle_pos()
        if hasattr(self, 'refresh_content'): self.refresh_content()
        self.update()

    def clone_state(self): return copy.deepcopy(self.data_model)

    def draw_styled_shape(self, painter, rect, style, is_circle=False):
        painter.save()
        path = QPainterPath()
        if is_circle:
            path.addEllipse(rect)
        else:
            radius = int(style.get('radius', 0))
            path.addRoundedRect(rect, radius, radius)
            
        painter.setClipPath(path)
        painter.setOpacity(float(style.get('opacity', 1.0)))
        
        bg_col_str = style.get('bg_color', '#ffffff')
        if bg_col_str == 'transparent': painter.setBrush(Qt.NoBrush)
        else: painter.fillPath(path, QColor(bg_col_str))

        bg_image = style.get('bg_image', '')
        if bg_image and os.path.exists(bg_image):
            pixmap = QPixmap(bg_image)
            if not pixmap.isNull():
                bg_x = int(style.get('bg_x', 0)); bg_y = int(style.get('bg_y', 0))
                bg_w = int(style.get('bg_w', 0)); bg_h = int(style.get('bg_h', 0))
                if bg_w <= 0 or bg_h <= 0:
                    scaled = pixmap.scaled(rect.size().toSize(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled)
                else:
                    scaled = pixmap.scaled(bg_w, bg_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(bg_x, bg_y, scaled)

        if style.get('use_gradient', False):
            start_c = QColor(style.get('grad_start', '#ffffff'))
            end_c = QColor(style.get('grad_end', '#000000'))
            angle = int(style.get('grad_angle', 90))
            w, h = rect.width(), rect.height()
            cx, cy = w / 2, h / 2
            r = math.sqrt(w*w + h*h) / 2
            rad = math.radians(angle)
            x1, y1 = cx - r * math.cos(rad), cy - r * math.sin(rad)
            x2, y2 = cx + r * math.cos(rad), cy + r * math.sin(rad)
            gradient = QLinearGradient(x1, y1, x2, y2)
            gradient.setColorAt(0, start_c); gradient.setColorAt(1, end_c)
            painter.fillPath(path, QBrush(gradient))

        painter.restore() 
        b_width = int(style.get('border_width', 0))
        if b_width > 0:
            b_color = QColor(style.get('border_color', '#000000'))
            pen = QPen(b_color, b_width)
            painter.setPen(pen); painter.setBrush(Qt.NoBrush); painter.drawPath(path)
            
        if self.isSelected():
            pen = QPen(QColor("#007fd4"), 1, Qt.DashLine)
            painter.setPen(pen); painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(1,1,-1,-1))

class RootFrameItem(BaseResizableItem):
    def __init__(self, screen_rect):
        super().__init__(50, 50, 400, 300)
        self.screen_rect = screen_rect
        self.is_container = True
        self.data_model = {
            "id": "root", "type": "root_frame", "name": "Root Frame",
            "x": 50, "y": 50, "width": 400, "height": 300, "z_index": 0,
            "style": {"bg_color": "#ffffff", "opacity": 1.0, "radius": 0, "border_width": 1}
        }
        self.uid = "root"
        self.setZValue(0)
    def paint(self, painter, option, widget):
        self.draw_styled_shape(painter, self.rect(), self.data_model.get('style', {}))
    def constrain_position(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.rect().width(), self.rect().height()
        sx, sy, sw, sh = self.screen_rect.getRect()
        if x < sx: x = sx
        if y < sy: y = sy
        if x + w > sw: x = sw - w
        if y + h > sh: y = sh - h
        return QPointF(x, y)
    def handle_resize(self, scene_pos): 
        local_pos = self.mapFromScene(scene_pos)
        new_w = max(50, local_pos.x()); new_h = max(50, local_pos.y())
        screen_w = self.screen_rect.width(); screen_h = self.screen_rect.height()
        if self.x() + new_w > screen_w: new_w = screen_w - self.x()
        if self.y() + new_h > screen_h: new_h = screen_h - self.y()
        self.setRect(0, 0, new_w, new_h)
        self.update_handle_pos(); self.update_model()
    def reset_settings(self):
        self.setPos(50, 50); self.setRect(0, 0, 400, 300)
        self.data_model['style'] = {"bg_color": "#ffffff", "opacity": 1.0, "radius": 0}
        self.update_handle_pos(); self.update_model(); self.update()

class GradientTextItem(QGraphicsTextItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gradient_data = None
    def set_gradient_data(self, data):
        self.gradient_data = data
        self.update()
    def paint(self, painter, option, widget):
        if self.gradient_data and self.gradient_data.get('use_text_gradient'):
            rect = self.boundingRect()
            start_c = QColor(self.gradient_data.get('text_grad_start', '#000000'))
            end_c = QColor(self.gradient_data.get('text_grad_end', '#000000'))
            angle = int(self.gradient_data.get('text_grad_angle', 90))
            w, h = rect.width(), rect.height()
            cx, cy = w / 2, h / 2
            r = math.sqrt(w*w + h*h) / 2
            rad = math.radians(angle)
            x1, y1 = cx - r * math.cos(rad), cy - r * math.sin(rad)
            x2, y2 = cx + r * math.cos(rad), cy + r * math.sin(rad)
            gradient = QLinearGradient(x1, y1, x2, y2)
            gradient.setColorAt(0, start_c); gradient.setColorAt(1, end_c)
            pen = QPen(QBrush(gradient), 0)
            self.setDefaultTextColor(Qt.transparent)
            painter.setPen(pen)
            super().paint(painter, option, widget)
        else: super().paint(painter, option, widget)

class WidgetItem(BaseResizableItem):
    def __init__(self, template_key, x, y, parent_item):
        tpl = WIDGET_TEMPLATES.get(template_key, {})
        w = tpl.get('width', 100); h = tpl.get('height', 100)
        super().__init__(x, y, w, h, parent=parent_item)
        self.is_container = tpl.get('is_container', False)
        self.data_model = json.loads(json.dumps(tpl))
        self.data_model['x'] = int(x); self.data_model['y'] = int(y)
        self.data_model['id'] = self.uid
        self.data_model['z_index'] = tpl.get('z_index', 0)
        self.content_proxy = GradientTextItem(self)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_content)
        self.timer.start(1000)
        self.refresh_content()
        self.setZValue(self.data_model['z_index'])

    def paint(self, painter, option, widget):
        type_ = self.data_model.get('type', 'rect')
        style = self.data_model.get('style', {})
        
        if type_ == 'circle':
            self.draw_styled_shape(painter, self.rect(), style, is_circle=True)
            
        elif type_ == 'progress':
            self.draw_styled_shape(painter, self.rect(), style)
            content = self.data_model.get('content', {})
            val = float(content.get('value', 0))
            max_val = float(content.get('max_value', 100))
            if max_val == 0: max_val = 1
            ratio = min(max(val / max_val, 0), 1)
            fill_w = self.rect().width() * ratio
            fill_rect = QRectF(0, 0, fill_w, self.rect().height())
            
            painter.save()
            radius = int(style.get('radius', 0))
            path = QPainterPath()
            path.addRoundedRect(fill_rect, radius, radius)
            painter.setClipPath(path)
            
            if content.get('use_gradient', False):
                start_c = QColor(content.get('grad_start', '#00ff00'))
                end_c = QColor(content.get('grad_end', '#007700'))
                gradient = QLinearGradient(0, 0, fill_w, 0)
                gradient.setColorAt(0, start_c); gradient.setColorAt(1, end_c)
                painter.fillPath(path, QBrush(gradient))
            else:
                c = QColor(content.get('bar_color', '#00ff00'))
                painter.fillPath(path, QColor(c))
            painter.restore()
            if self.isSelected():
                painter.setPen(QPen(QColor("#007fd4"), 2, Qt.DashLine)); painter.setBrush(Qt.NoBrush); painter.drawRect(self.rect())
                
        else: # Rect, Image, Text containers
            self.draw_styled_shape(painter, self.rect(), style)
    
    def refresh_content(self):
        content = self.data_model.get('content', {})
        text = ""
        type_ = self.data_model.get('type', 'text')
        
        if type_ == 'clock':
            fmt = content.get('format', 'HH:mm')
            py_fmt = fmt.replace("HH", "%H").replace("mm", "%M").replace("ss", "%S")
            text = datetime.now().strftime(py_fmt)
        elif type_ == 'date':
            fmt = content.get('format', '%d.%m.%Y')
            try: text = datetime.now().strftime(fmt)
            except: text = "Error"
        elif type_ == 'text': 
            text = content.get('text', 'Text')
            text = text.replace("{cpu}", "15%").replace("{ram}", "4GB").replace("{bat}", "80%")
        
        if text:
            font = QFont(content.get('font_family', 'Arial'), int(content.get('font_size', 12)))
            self.content_proxy.setFont(font)
            self.content_proxy.setPlainText(text)
            if not content.get('use_text_gradient'):
                self.content_proxy.setDefaultTextColor(QColor(content.get('color', '#000000')))
            self.content_proxy.set_gradient_data(content)
            br = self.content_proxy.boundingRect()
            self.content_proxy.setPos(self.rect().width()/2 - br.width()/2, self.rect().height()/2 - br.height()/2)
        else: self.content_proxy.setPlainText("")

class BgImageGizmo(QGraphicsRectItem):
    def __init__(self, target_item, image_path, scene):
        super().__init__()
        self.target = target_item
        self.pixmap = QPixmap(image_path)
        self.scene_ref = scene
        st = target_item.data_model['style']
        w = int(st.get('bg_w', 0)); h = int(st.get('bg_h', 0))
        x = int(st.get('bg_x', 0)); y = int(st.get('bg_y', 0))
        if w <= 0 or h <= 0:
            rect = target_item.rect()
            w = int(rect.width()); h = int(rect.height())
            self.pixmap = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        else: self.pixmap = self.pixmap.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.setRect(0, 0, w, h)
        target_pos = target_item.mapToScene(0, 0)
        self.setPos(target_pos.x() + x, target_pos.y() + y)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setZValue(9999) 
        self.resize_handle = HandleItem(self)
        self.resize_handle.setPos(w, h)
    def paint(self, painter, option, widget):
        painter.setOpacity(0.5); painter.drawPixmap(self.rect().toRect(), self.pixmap)
        painter.setPen(QPen(Qt.yellow, 2, Qt.DashLine)); painter.setBrush(Qt.NoBrush); painter.drawRect(self.rect())
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            target_pos = self.target.mapToScene(0, 0); new_pos = value
            rel_x = new_pos.x() - target_pos.x(); rel_y = new_pos.y() - target_pos.y()
            self.target.data_model['style']['bg_x'] = int(rel_x)
            self.target.data_model['style']['bg_y'] = int(rel_y)
            if self.target.data_model['style']['bg_w'] == 0:
                 self.target.data_model['style']['bg_w'] = int(self.rect().width())
                 self.target.data_model['style']['bg_h'] = int(self.rect().height())
            self.target.update()
        return super().itemChange(change, value)
    def handle_resize(self, scene_pos):
        local_pos = self.mapFromScene(scene_pos)
        new_w = max(20, local_pos.x()); new_h = max(20, local_pos.y())
        self.setRect(0, 0, new_w, new_h); self.resize_handle.setPos(new_w, new_h)
        self.target.data_model['style']['bg_w'] = int(new_w)
        self.target.data_model['style']['bg_h'] = int(new_h)
        orig = QPixmap(self.target.data_model['style']['bg_image'])
        self.pixmap = orig.scaled(int(new_w), int(new_h), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.target.update(); self.update()