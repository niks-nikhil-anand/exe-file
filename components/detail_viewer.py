from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QSplitter, QGraphicsOpacityEffect, QFrame, QMainWindow, QStackedWidget,
    QPushButton, QSlider, QGridLayout, QLayout
)
from PyQt5.QtGui import (
    QPixmap, QColor, QPainter, QBrush, QPen, QKeyEvent, QImage, QDrag
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QPoint, QUrl,
    QEvent, QSize, QTimer, QMimeData
)

from config.constants import IMAGE_EXTS, VIDEO_EXTS, PDF_EXTS
from components.image_viewer import ZoomableImageScrollArea
from components.grid_image_item import GridImageItem
from components.drag_overlay import DragHighlightOverlay
from components.video_viewer import VideoViewer
from components.pdf_viewer import PdfViewer

class DetailViewer(QWidget):
    media_closed = pyqtSignal()
    image_clicked = pyqtSignal()
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        # 1. Image View Setup
        self.image_scroll = ZoomableImageScrollArea()
        self.image_scroll.image_clicked.connect(self.image_clicked.emit)
        self.stacked_widget.addWidget(self.image_scroll)

        # 2. Video View Setup
        self.video_viewer = VideoViewer()
        self.video_container = self.video_viewer
        self.media_player = self.video_viewer.media_player
        self.stacked_widget.addWidget(self.video_viewer)

        # 3. PDF View Setup
        self.pdf_viewer = PdfViewer()
        self.pdf_container = self.pdf_viewer
        self.stacked_widget.addWidget(self.pdf_viewer)

        # 4. Placeholder View Setup
        self.placeholder_container = QWidget()
        self.placeholder_container.setStyleSheet("background-color: #121212;")
        placeholder_layout = QVBoxLayout(self.placeholder_container)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.placeholder_icon = QLabel("🖼️")
        self.placeholder_icon.setStyleSheet("font-size: 64px; margin-bottom: 20px;")
        self.placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.placeholder_icon)

        self.placeholder_text = QLabel("Select a media file or drop multiple images here")
        self.placeholder_text.setStyleSheet("color: #666666; font-size: 16px; font-weight: 500;")
        self.placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(self.placeholder_text)

        self.stacked_widget.addWidget(self.placeholder_container)

        # 5. Multi Image View Setup (Scrollable Grid)
        self.multi_image_scroll = QScrollArea()
        self.multi_image_scroll.setWidgetResizable(True)
        self.multi_image_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.multi_image_scroll.setStyleSheet("background-color: #121212;")
        self.multi_image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.multi_image_container = QWidget()
        self.multi_image_container.setStyleSheet("background-color: #121212;")
        self.multi_image_grid = QGridLayout(self.multi_image_container)
        self.multi_image_grid.setContentsMargins(15, 15, 15, 15)
        self.multi_image_grid.setSpacing(15)

        self.multi_image_scroll.setWidget(self.multi_image_container)
        self.stacked_widget.addWidget(self.multi_image_scroll)

        self.anim = QPropertyAnimation(self.stacked_widget)
        self.anim.setPropertyName(b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(lambda: self.stacked_widget.setGraphicsEffect(None))

        # Floating Close Button
        self.close_button = QPushButton("✕", self)
        self.close_button.setFixedSize(36, 36)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 30, 0.85);
                color: #e0e0e0;
                border: 1px solid rgba(80, 80, 80, 0.6);
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 0.95);
                color: white;
                border: 1px solid rgba(220, 50, 50, 0.95);
            }
        """)
        self.close_button.clicked.connect(self.clear_media)
        self.close_button.hide()

        # Fit to screen button overlay
        self.fit_button = QPushButton("Fit", self)
        self.fit_button.setFixedSize(60, 36)
        self.fit_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(43, 43, 43, 0.85);
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(58, 58, 58, 0.95);
            }
        """)
        self.fit_button.clicked.connect(self.fit_to_screen)
        self.fit_button.hide()

        self.zoom_out_button = QPushButton("−", self)
        self.zoom_out_button.setFixedSize(36, 36)
        self.zoom_out_button.setToolTip("Zoom out")
        self.zoom_out_button.setStyleSheet(self.fit_button.styleSheet())
        self.zoom_out_button.clicked.connect(self.image_scroll.zoom_out)
        self.zoom_out_button.hide()

        self.zoom_in_button = QPushButton("+", self)
        self.zoom_in_button.setFixedSize(36, 36)
        self.zoom_in_button.setToolTip("Zoom in")
        self.zoom_in_button.setStyleSheet(self.fit_button.styleSheet())
        self.zoom_in_button.clicked.connect(self.image_scroll.zoom_in)
        self.zoom_in_button.hide()

        # Image Count Badge
        self.badge_label = QLabel(self)
        self.badge_label.setStyleSheet("""
            QLabel {
                background-color: rgba(56, 189, 248, 0.95);
                color: #0f172a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.badge_label.hide()

        # Drag Highlight Overlay
        self.drag_overlay = DragHighlightOverlay(self)

        self.current_filepath = None
        self.current_pixmap = None
        self.grid_items = []

        # Start on the placeholder screen
        self.stacked_widget.setCurrentIndex(3)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            has_image = False
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(IMAGE_EXTS):
                    has_image = True
                    break
            if has_image:
                self.set_drag_highlight(True)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drag_highlight(False)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.set_drag_highlight(False)
        if event.mimeData().hasUrls():
            image_paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(IMAGE_EXTS):
                    image_paths.append(path)
            if image_paths:
                print(f"Debug: Number of dropped images: {len(image_paths)}")
                # A drag that starts from an unselected sidebar card briefly opens
                # that card in the focused viewer.  The grid itself is still alive,
                # so use its contents (rather than the visible stacked page) to
                # decide whether this drop continues the current grid session.
                append_to_grid = bool(self.grid_items)
                self.load_multiple_media_grid(image_paths, append=append_to_grid)
                event.acceptProposedAction()

    def set_drag_highlight(self, active):
        if hasattr(self, 'drag_overlay'):
            if active:
                self.drag_overlay.setGeometry(self.rect())
                self.drag_overlay.show()
                self.drag_overlay.raise_()
            else:
                self.drag_overlay.hide()

    def fit_to_screen(self):
        if self.stacked_widget.currentIndex() == 0:
            self.image_scroll.is_fit = True
            self.image_scroll.zoom_factor = 1.0
            self.image_scroll.update_view()

    def set_image_zoom_controls_visible(self, visible):
        self.fit_button.setVisible(visible)
        self.zoom_out_button.setVisible(visible)
        self.zoom_in_button.setVisible(visible)
        if visible:
            self.fit_button.raise_()
            self.zoom_out_button.raise_()
            self.zoom_in_button.raise_()

    def load_media(self, filepath):
        self.anim.stop()
        self.media_player.stop()

        self.pdf_viewer.clear()

        self.current_filepath = filepath
        self.current_pixmap = None

        lower_path = filepath.lower()

        if lower_path.endswith(IMAGE_EXTS):
            self.stacked_widget.setCurrentIndex(0)
            pixmap = QPixmap(filepath)
            self.current_pixmap = pixmap
            self.image_scroll.set_pixmap(pixmap)
            self.set_image_zoom_controls_visible(True)
        elif lower_path.endswith(PDF_EXTS):
            self.stacked_widget.setCurrentIndex(2)
            self.set_image_zoom_controls_visible(False)
            self.pdf_viewer.load_document(filepath)
        elif lower_path.endswith(VIDEO_EXTS):
            self.stacked_widget.setCurrentIndex(1)
            self.set_image_zoom_controls_visible(False)
            self.video_viewer.load_media(filepath)
        else:
            self.stacked_widget.setCurrentIndex(3)
            import os
            self.placeholder_icon.setText("📄")
            self.placeholder_text.setText(f"Preview not available for: {os.path.basename(filepath)}")
            self.set_image_zoom_controls_visible(False)

        self.close_button.show()
        self.close_button.raise_()

        self.start_stacked_animation()

    def load_focused_image(self, filepath):
        self.stacked_widget.setCurrentIndex(0)
        pixmap = QPixmap(filepath)
        self.current_pixmap = pixmap
        self.image_scroll.set_pixmap(pixmap)
        self.close_button.show()
        self.close_button.raise_()
        self.set_image_zoom_controls_visible(True)

    def load_multiple_media_grid(self, image_paths, append=False):
        self.anim.stop()
        self.media_player.stop()
        self.pdf_viewer.clear()

        self.current_filepath = None
        self.current_pixmap = None

        if not append:
            self.clear_grid_items()
            self.current_media_list = []
            self.grid_items = []
        elif not hasattr(self, 'current_media_list'):
            self.current_media_list = []

        for path in image_paths:
            self.current_media_list.append(path)
            item = GridImageItem(path, self)
            item.clicked.connect(self.on_grid_item_clicked)
            item.double_clicked.connect(self.on_grid_item_double_clicked)
            item.remove_requested.connect(self.on_remove_item_requested)
            self.grid_items.append(item)

        self.rebuild_multi_image_grid(force=True)

        self.stacked_widget.setCurrentIndex(4) # Multi-image grid page
        self.close_button.show()
        self.close_button.raise_()
        self.set_image_zoom_controls_visible(False)
        self.update_image_count_badge()

        self.start_stacked_animation()

    def on_grid_item_clicked(self, clicked_item):
        for item in self.grid_items:
            item.set_selected(item == clicked_item)

    def on_grid_item_double_clicked(self, clicked_item):
        self.badge_label.hide()
        self.load_focused_image(clicked_item.filepath)
        # A grid double-click means "open this image" rather than merely select
        # it, so promote the focused viewer to the application's fullscreen mode.
        self.fullscreen_requested.emit()

    def on_remove_item_requested(self, item):
        path = item.filepath
        if hasattr(self, 'current_media_list') and path in self.current_media_list:
            self.current_media_list.remove(path)

        if item in self.grid_items:
            self.grid_items.remove(item)

        self.multi_image_grid.removeWidget(item)
        item.setParent(None)
        item.deleteLater()

        if not self.grid_items:
            self.clear_media()
        else:
            self.rebuild_multi_image_grid(force=True)
            self.update_image_count_badge()

    def update_image_count_badge(self):
        if hasattr(self, 'grid_items') and self.grid_items:
            count = len(self.grid_items)
            self.badge_label.setText(f"📁 {count} Image{'s' if count != 1 else ''}")
            self.badge_label.show()
            self.badge_label.raise_()
        else:
            self.badge_label.hide()

    def clear_grid_items(self):
        if hasattr(self, 'grid_items'):
            for item in self.grid_items:
                self.multi_image_grid.removeWidget(item)
                item.setParent(None)
                item.deleteLater()
            self.grid_items = []

    def rebuild_multi_image_grid(self, force=False):
        if not hasattr(self, 'grid_items') or not self.grid_items:
            return

        image_count = len(self.grid_items)

        # Keep the first few layouts predictable: one image fills the viewer,
        # two images sit side-by-side, and a third starts the second row.
        # Larger collections continue as a balanced grid.
        import math
        if image_count == 1:
            cols = 1
        elif image_count <= 4:
            cols = 2
        else:
            cols = math.ceil(math.sqrt(image_count))
        rows = math.ceil(image_count / cols)
        self.current_grid_cols = cols

        # A single image should use the complete grid viewport.  Multi-image
        # layouts retain a small gutter so their boundaries remain clear.
        if image_count == 1:
            self.multi_image_grid.setContentsMargins(0, 0, 0, 0)
            self.multi_image_grid.setSpacing(0)
        else:
            self.multi_image_grid.setContentsMargins(8, 8, 8, 8)
            self.multi_image_grid.setSpacing(8)

        # Clear previous layout stretches
        for r in range(self.multi_image_grid.rowCount()):
            self.multi_image_grid.setRowStretch(r, 0)
        for c in range(self.multi_image_grid.columnCount()):
            self.multi_image_grid.setColumnStretch(c, 0)

        for item in self.grid_items:
            self.multi_image_grid.removeWidget(item)

        for idx, item in enumerate(self.grid_items):
            row = idx // cols
            col = idx % cols
            self.multi_image_grid.addWidget(item, row, col)

        for r in range(rows):
            self.multi_image_grid.setRowStretch(r, 1)
        for c in range(cols):
            self.multi_image_grid.setColumnStretch(c, 1)

        for item in self.grid_items:
            item.single_mode = image_count == 1
            item.update_image()

    def start_stacked_animation(self):
        self.anim.stop()
        self.opacity_effect = QGraphicsOpacityEffect(self.stacked_widget)
        self.stacked_widget.setGraphicsEffect(self.opacity_effect)
        self.anim.setTargetObject(self.opacity_effect)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def update_image(self):
        self.image_scroll.update_view()

    def clear_media(self):
        # Return to multi-image grid if focused viewer is closed and we have a grid loaded
        if self.stacked_widget.currentIndex() == 0 and hasattr(self, 'grid_items') and self.grid_items:
            self.stacked_widget.setCurrentIndex(4)
            self.set_image_zoom_controls_visible(False)
            self.close_button.show()
            self.close_button.raise_()
            self.update_image_count_badge()
            return

        self.anim.stop()
        self.stacked_widget.setGraphicsEffect(None)
        self.media_player.stop()

        self.pdf_viewer.clear()

        self.current_filepath = None
        self.current_pixmap = None
        self.image_scroll.set_pixmap(QPixmap())
        self.clear_grid_items()

        self.stacked_widget.setCurrentIndex(3)
        self.placeholder_icon.setText("🖼️")
        self.placeholder_text.setText("Select a media file or drop multiple images here")
        self.close_button.hide()
        self.set_image_zoom_controls_visible(False)
        self.badge_label.hide()
        self.media_closed.emit()

    @property
    def current_pdf_doc(self):
        return self.pdf_viewer.document

    def update_pdf_page(self):
        self.pdf_viewer.render_page()

    def pdf_prev_page(self):
        self.pdf_viewer.previous_page()

    def pdf_next_page(self):
        self.pdf_viewer.next_page()

    def pdf_zoom_in(self):
        self.pdf_viewer.zoom_in()

    def pdf_zoom_out(self):
        self.pdf_viewer.zoom_out()

    def shutdown(self):
        self.video_viewer.stop()
        self.pdf_viewer.clear()

    def resizeEvent(self, event):
        if self.stacked_widget.currentIndex() == 0:
            self.update_image()
        elif self.stacked_widget.currentIndex() == 4:
            self.rebuild_multi_image_grid()
        super().resizeEvent(event)

        margin = 15
        self.close_button.move(margin, margin)
        self.close_button.raise_()

        self.fit_button.move(margin + 45, margin)
        self.fit_button.raise_()

        self.zoom_out_button.move(margin + 110, margin)
        self.zoom_out_button.raise_()

        self.zoom_in_button.move(margin + 151, margin)
        self.zoom_in_button.raise_()

        if hasattr(self, 'badge_label'):
            self.badge_label.move(margin + 200, margin + 4)
            self.badge_label.raise_()

        if hasattr(self, 'drag_overlay'):
            self.drag_overlay.setGeometry(self.rect())
