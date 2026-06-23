from PyQt5.QtWidgets import QScrollArea, QLabel, QFrame, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QTransform
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QEvent

class ZoomableImageScrollArea(QScrollArea):
    image_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #121212;")

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #121212;")
        self.setWidget(self.image_label)

        self.grabGesture(Qt.PinchGesture)

        self.original_pixmap = None
        self.zoom_factor = 1.0
        self.is_fit = True
        self.gesture_start_zoom = 1.0
        self.is_fullscreen = False

        self.setup_overlay_controls()

    def set_fullscreen_mode(self, is_full):
        self.is_fullscreen = is_full
        if hasattr(self, 'controls_overlay'):
            if is_full:
                self.controls_overlay.show()
                self.controls_overlay.raise_()
                self.controls_overlay.move(self.width() - self.controls_overlay.width() - 20, 20)
            else:
                self.controls_overlay.hide()

    def setup_overlay_controls(self):
        self.controls_overlay = QWidget(self)
        self.controls_overlay.setStyleSheet("background-color: rgba(30, 30, 30, 0.8); border-radius: 6px;")
        
        controls_layout = QHBoxLayout(self.controls_overlay)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(5)

        btn_style = """
            QPushButton { background: transparent; color: white; border: none; font-size: 14px; padding: 4px; border-radius: 4px; }
            QPushButton:hover { background: rgba(80, 80, 80, 0.8); }
        """

        self.btn_fit_screen = QPushButton("Fit")
        self.btn_fit_screen.setStyleSheet(btn_style)
        self.btn_fit_screen.clicked.connect(self.fit_to_screen)

        self.btn_fit_width = QPushButton("Fit W")
        self.btn_fit_width.setStyleSheet(btn_style)
        self.btn_fit_width.clicked.connect(self.fit_width)

        self.btn_reset = QPushButton("100%")
        self.btn_reset.setStyleSheet(btn_style)
        self.btn_reset.clicked.connect(self.reset_zoom)

        self.btn_zoom_out = QPushButton("➖")
        self.btn_zoom_out.setStyleSheet(btn_style)
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_zoom_in = QPushButton("➕")
        self.btn_zoom_in.setStyleSheet(btn_style)
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        self.btn_rot_l = QPushButton("⟲")
        self.btn_rot_l.setStyleSheet(btn_style)
        self.btn_rot_l.clicked.connect(self.rotate_left)

        self.btn_rot_r = QPushButton("⟳")
        self.btn_rot_r.setStyleSheet(btn_style)
        self.btn_rot_r.clicked.connect(self.rotate_right)
        
        self.btn_flip_h = QPushButton("↔")
        self.btn_flip_h.setStyleSheet(btn_style)
        self.btn_flip_h.clicked.connect(self.flip_horizontal)
        
        self.btn_flip_v = QPushButton("↕")
        self.btn_flip_v.setStyleSheet(btn_style)
        self.btn_flip_v.clicked.connect(self.flip_vertical)

        for btn in [self.btn_fit_screen, self.btn_fit_width, self.btn_reset, self.btn_zoom_out, self.btn_zoom_in, self.btn_rot_l, self.btn_rot_r, self.btn_flip_h, self.btn_flip_v]:
            controls_layout.addWidget(btn)

        self.controls_overlay.adjustSize()
        self.controls_overlay.hide()

    def fit_to_screen(self):
        self.is_fit = True
        self.update_view()

    def fit_width(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        viewport_width = self.viewport().width()
        self.zoom_factor = viewport_width / self.original_pixmap.width()
        self.is_fit = False
        self.update_view()

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.is_fit = False
        self.update_view()

    def rotate(self, angle):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        transform = QTransform().rotate(angle)
        self.original_pixmap = self.original_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.update_view()

    def rotate_left(self):
        self.rotate(-90)

    def rotate_right(self):
        self.rotate(90)

    def flip_horizontal(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        self.original_pixmap = self.original_pixmap.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
        self.update_view()

    def flip_vertical(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        self.original_pixmap = self.original_pixmap.transformed(QTransform().scale(1, -1), Qt.TransformationMode.SmoothTransformation)
        self.update_view()

    def set_pixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.zoom_factor = 1.0
        self.is_fit = True
        self.setWidgetResizable(True)
        self.update_view()

    def update_view(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return

        if self.is_fit:
            self.setWidgetResizable(True)
            viewport_size = self.viewport().size()
            scaled = self.original_pixmap.scaled(
                viewport_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            self.setWidgetResizable(False)
            w = int(self.original_pixmap.width() * self.zoom_factor)
            h = int(self.original_pixmap.height() * self.zoom_factor)
            scaled = self.original_pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.resize(w, h)
            self.image_label.setPixmap(scaled)
        self.update_cursor()

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            self.pinchTriggered(pinch)
            event.accept(Qt.PinchGesture)
            return True
        return False

    def pinchTriggered(self, gesture):
        if gesture.state() == Qt.GestureStarted:
            if self.is_fit:
                if self.image_label.pixmap() and hasattr(self, 'original_pixmap') and self.original_pixmap and self.original_pixmap.width() > 0:
                    self.zoom_factor = self.image_label.pixmap().width() / self.original_pixmap.width()
                else:
                    self.zoom_factor = 1.0
                self.is_fit = False
            self.gesture_start_zoom = self.zoom_factor

        factor = gesture.scaleFactor()
        self.zoom_factor = max(0.1, min(self.gesture_start_zoom * factor, 10.0))
        self.update_view()

    def update_cursor(self):
        if self.is_fit:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            if hasattr(self, 'is_dragging') and self.is_dragging:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)

    def zoom_by(self, factor):
        """Zoom around the center when invoked by buttons or shortcuts."""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return

        if self.is_fit:
            displayed = self.image_label.pixmap()
            if displayed and self.original_pixmap.width() > 0:
                self.zoom_factor = displayed.width() / self.original_pixmap.width()
            else:
                self.zoom_factor = 1.0
            self.is_fit = False

        self.zoom_factor = max(0.1, min(self.zoom_factor * factor, 10.0))
        self.update_view()

    def zoom_in(self):
        self.zoom_by(1.25)

    def zoom_out(self):
        self.zoom_by(0.8)

    def enterEvent(self, event):
        self.update_cursor()
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def wheelEvent(self, event):
        if not self.original_pixmap or self.original_pixmap.isNull():
            super().wheelEvent(event)
            return

        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if getattr(self, 'restrict_zoom_to_fullscreen', False) and not getattr(self, 'is_fullscreen', False):
                super().wheelEvent(event)
                return
                
            viewport_pos = event.pos()
            widget_pos = self.widget().mapFrom(self.viewport(), viewport_pos)

            old_zoom = self.zoom_factor
            if self.is_fit:
                if self.image_label.pixmap() and hasattr(self, 'original_pixmap') and self.original_pixmap and self.original_pixmap.width() > 0:
                    old_zoom = self.image_label.pixmap().width() / self.original_pixmap.width()
                else:
                    old_zoom = 1.0
                self.is_fit = False

            angle = event.angleDelta().y()
            factor = 1.15 if angle > 0 else 0.85
            self.zoom_factor = max(0.1, min(old_zoom * factor, 10.0))

            if self.widget().rect().contains(widget_pos):
                zoom_center_viewport = viewport_pos
                zoom_center_widget = widget_pos
            else:
                zoom_center_viewport = QPoint(self.viewport().width() // 2, self.viewport().height() // 2)
                zoom_center_widget = self.widget().mapFrom(self.viewport(), zoom_center_viewport)

            self.update_view()

            if old_zoom > 0:
                zoom_ratio = self.zoom_factor / old_zoom
                new_x = zoom_center_widget.x() * zoom_ratio
                new_y = zoom_center_widget.y() * zoom_ratio
                self.horizontalScrollBar().setValue(int(new_x - zoom_center_viewport.x()))
                self.verticalScrollBar().setValue(int(new_y - zoom_center_viewport.y()))
        else:
            super().wheelEvent(event)

        event.accept()

    def mouseDoubleClickEvent(self, event):
        if getattr(self, 'restrict_zoom_to_fullscreen', False) and not getattr(self, 'is_fullscreen', False):
            super().mouseDoubleClickEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_fit:
                self.zoom_factor = 2.0
                self.is_fit = False
            else:
                self.is_fit = True
                self.zoom_factor = 1.0
            self.update_view()
        event.accept()

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.Gesture:
            if getattr(self, 'restrict_zoom_to_fullscreen', False) and not getattr(self, 'is_fullscreen', False):
                return super().viewportEvent(event)
            return self.gestureEvent(event)
        return super().viewportEvent(event)

    def resizeEvent(self, event):
        if self.is_fit:
            self.update_view()
        if hasattr(self, 'controls_overlay') and self.controls_overlay.isVisible():
            self.controls_overlay.move(self.width() - self.controls_overlay.width() - 20, 20)
            self.controls_overlay.raise_()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.scroll_start_h = self.horizontalScrollBar().value()
            self.scroll_start_v = self.verticalScrollBar().value()
            self.is_dragging = True
            self.update_cursor()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'is_dragging') and self.is_dragging:
            delta = event.pos() - self.drag_start_pos
            self.horizontalScrollBar().setValue(self.scroll_start_h - delta.x())
            self.verticalScrollBar().setValue(self.scroll_start_v - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.update_cursor()
            if hasattr(self, 'drag_start_pos'):
                diff = (event.pos() - self.drag_start_pos).manhattanLength()
                if diff < 8:
                    self.image_clicked.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
