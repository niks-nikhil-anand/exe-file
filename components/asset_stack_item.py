import os

import fitz
from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from config.constants import IMAGE_EXTS, PDF_EXTS, VIDEO_EXTS
from components.image_viewer import ZoomableImageScrollArea
from components.pdf_viewer import PdfViewer
from components.video_viewer import VideoViewer


class AssetStackItem(QWidget):
    remove_requested = pyqtSignal(object)
    drag_remove_requested = pyqtSignal(object)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.is_top_item = False
        self.is_hovered = False
        self.drag_start_pos = QPoint()
        self.drag_offset = QPoint()
        self.dragging = False
        self.image_scroll = None
        self.video_viewer = None
        self.pdf_viewer = None

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(0)

        self.remove_button = QPushButton("✕", self)
        self.remove_button.setFixedSize(34, 34)
        self.remove_button.setToolTip("Remove top layer")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(24, 24, 27, 0.88);
                color: #f4f4f5;
                border: 1px solid rgba(244, 244, 245, 0.18);
                border-radius: 17px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.95);
                border-color: rgba(239, 68, 68, 0.95);
            }
        """)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_button.hide()

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #d4d4d8; background: transparent;")
        self.layout.addWidget(self.preview_label)

        self.set_top_item(False)

    def set_top_item(self, is_top):
        if self.is_top_item == is_top and self.layout.count() > 0:
            return

        self.shutdown()
        self.is_top_item = is_top
        self.clear_layout()

        self.layout.setContentsMargins(14, 14, 14, 14)
        if is_top:
            self.remove_button.show()
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.build_active_preview()
        else:
            self.remove_button.hide()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.build_passive_preview()

        self.update()

    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def build_active_preview(self):
        lower_path = self.filepath.lower()
        if lower_path.endswith(IMAGE_EXTS):
            self.image_scroll = ZoomableImageScrollArea()
            self.image_scroll.set_pixmap(QPixmap(self.filepath))
            self.layout.addWidget(self.image_scroll)
        elif lower_path.endswith(VIDEO_EXTS):
            self.video_viewer = VideoViewer()
            self.video_viewer.load_media(self.filepath)
            self.layout.addWidget(self.video_viewer)
        elif lower_path.endswith(PDF_EXTS):
            self.pdf_viewer = PdfViewer()
            self.pdf_viewer.load_document(self.filepath)
            self.layout.addWidget(self.pdf_viewer)
        else:
            self.layout.addWidget(self.create_document_label("Preview not available"))

    def build_passive_preview(self):
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #d4d4d8; background: transparent; font-size: 14px; font-weight: 600;")
        pixmap = self.create_passive_pixmap()
        if pixmap and not pixmap.isNull():
            label.setPixmap(pixmap)
        else:
            label.setText(os.path.basename(self.filepath))
        self.layout.addWidget(label)

    def create_document_label(self, title):
        label = QLabel(f"📄\n{title}\n{os.path.basename(self.filepath)}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #d4d4d8; background: transparent; font-size: 17px; font-weight: 600;")
        return label

    def create_passive_pixmap(self):
        lower_path = self.filepath.lower()
        if lower_path.endswith(IMAGE_EXTS):
            pixmap = QPixmap(self.filepath)
        elif lower_path.endswith(PDF_EXTS):
            pixmap = self.create_pdf_preview()
        elif lower_path.endswith(VIDEO_EXTS):
            pixmap = self.create_icon_preview("▶", "#164e63", "#0f172a")
        else:
            pixmap = self.create_icon_preview("FILE", "#334155", "#1e293b")

        if not pixmap or pixmap.isNull():
            return QPixmap()

        size = min(max(220, self.width() - 80), 440)
        return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def create_pdf_preview(self):
        try:
            doc = fitz.open(self.filepath)
            if len(doc) == 0:
                return QPixmap()
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.55, 0.55))
            image_format = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, image_format)
            result = QPixmap.fromImage(image)
            doc.close()
            return result
        except Exception:
            return QPixmap()

    def create_icon_preview(self, text, top_color, bottom_color):
        pixmap = QPixmap(320, 220)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 320, 220, 18, 18)
        painter.fillPath(path, QColor(bottom_color))
        painter.setPen(QPen(QColor(top_color), 8))
        painter.drawRoundedRect(QRect(18, 18, 284, 184), 14, 14)
        painter.setPen(QColor("#e5e7eb"))
        font = painter.font()
        font.setPointSize(26 if len(text) <= 2 else 20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return pixmap

    def fit_to_screen(self):
        if self.image_scroll:
            self.image_scroll.is_fit = True
            self.image_scroll.zoom_factor = 1.0
            self.image_scroll.update_view()

    def zoom_in(self):
        if self.image_scroll:
            self.image_scroll.zoom_in()

    def zoom_out(self):
        if self.image_scroll:
            self.image_scroll.zoom_out()

    def is_image(self):
        return self.filepath.lower().endswith(IMAGE_EXTS)

    def shutdown(self):
        if self.video_viewer:
            self.video_viewer.stop()
            self.video_viewer = None
        if self.pdf_viewer:
            self.pdf_viewer.clear()
            self.pdf_viewer = None
        self.image_scroll = None

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.remove_button.move(self.width() - self.remove_button.width() - 18, 18)
        self.remove_button.raise_()

    def mousePressEvent(self, event):
        if self.is_top_item and event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.drag_offset = QPoint()
            self.dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_top_item and self.dragging:
            self.drag_offset = event.pos() - self.drag_start_pos
            if self.drag_offset.manhattanLength() > 8:
                self.move(self.x() + self.drag_offset.x(), self.y() + self.drag_offset.y())
                self.raise_()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_top_item and self.dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            distance = QPoint(self.x(), self.y()).manhattanLength()
            if distance > max(160, self.parentWidget().width() // 5):
                self.drag_remove_requested.emit(self)
            else:
                self.parentWidget().layout_stack_items(animated=True)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        color = QColor("#18181b") if self.is_top_item else QColor("#27272a")
        if self.is_hovered:
            color = QColor("#222226") if self.is_top_item else QColor("#303036")
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#38bdf8") if self.is_top_item else QColor("#3f3f46"), 2))
        painter.drawRoundedRect(rect, 18, 18)
