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
from components.drag_overlay import DragHighlightOverlay
from components.video_viewer import VideoViewer
from components.pdf_viewer import PdfViewer
from components.stacked_deck import StackedDeckViewer

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

        # 5. Multi Image View Setup (Stacked Deck)
        self.stacked_deck = StackedDeckViewer()
        self.stacked_deck.deck_empty.connect(self.clear_media)
        self.stacked_deck.deck_count_changed.connect(self.on_deck_count_changed)
        self.stacked_deck.fullscreen_requested.connect(self.fullscreen_requested.emit)
        self.stacked_widget.addWidget(self.stacked_deck)

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

        # Drag Highlight Overlay
        self.drag_overlay = DragHighlightOverlay(self)

        self.current_filepath = None
        self.current_pixmap = None

        # Start on the placeholder screen
        self.stacked_widget.setCurrentIndex(3)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            has_media = False
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith(IMAGE_EXTS) or path.endswith(VIDEO_EXTS) or path.endswith(PDF_EXTS):
                    has_media = True
                    break
            if has_media:
                self.set_drag_highlight(True)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drag_highlight(False)
        event.accept()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.set_drag_highlight(False)
        if event.mimeData().hasUrls():
            media_paths = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                lower_path = path.lower()
                if lower_path.endswith(IMAGE_EXTS) or lower_path.endswith(VIDEO_EXTS) or lower_path.endswith(PDF_EXTS):
                    media_paths.append(path)
            if media_paths:
                print(f"Debug: Number of dropped media: {len(media_paths)}")
                # A drag that starts from an unselected sidebar card briefly opens
                # that card in the focused viewer.  The deck itself is still alive,
                # so use its contents (rather than the visible stacked page) to
                # decide whether this drop continues the current deck session.
                append_to_deck = bool(self.stacked_deck.media_paths)
                self.load_multiple_media_deck(media_paths, append=append_to_deck)
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
        elif lower_path.endswith(PDF_EXTS):
            self.stacked_widget.setCurrentIndex(2)
            self.pdf_viewer.load_document(filepath)
        elif lower_path.endswith(VIDEO_EXTS):
            self.stacked_widget.setCurrentIndex(1)
            self.video_viewer.load_media(filepath)
        else:
            self.stacked_widget.setCurrentIndex(3)
            import os
            self.placeholder_icon.setText("📄")
            self.placeholder_text.setText(f"Preview not available for: {os.path.basename(filepath)}")

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

    def load_multiple_media_deck(self, media_paths, append=False):
        self.anim.stop()
        self.media_player.stop()
        self.pdf_viewer.clear()

        self.current_filepath = None
        self.current_pixmap = None

        if append:
            self.stacked_deck.append_media(media_paths)
        else:
            self.stacked_deck.load_media(media_paths)

        self.stacked_widget.setCurrentIndex(4) # Stacked deck page
        self.close_button.show()
        self.close_button.raise_()

        self.start_stacked_animation()

    def on_deck_count_changed(self, count):
        pass

    def set_fullscreen_mode(self, is_full):
        if hasattr(self, 'stacked_deck'):
            self.stacked_deck.set_fullscreen_mode(is_full)
        if hasattr(self, 'image_scroll') and hasattr(self.image_scroll, 'set_fullscreen_mode'):
            self.image_scroll.set_fullscreen_mode(is_full)
        if hasattr(self, 'video_viewer') and hasattr(self.video_viewer, 'set_fullscreen_mode'):
            self.video_viewer.set_fullscreen_mode(is_full)
        if hasattr(self, 'pdf_viewer') and hasattr(self.pdf_viewer, 'set_fullscreen_mode'):
            self.pdf_viewer.set_fullscreen_mode(is_full)
            
        if is_full:
            self.close_button.hide()
        elif self.stacked_widget.currentIndex() != 3:
            self.close_button.show()

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
        # Return to deck if focused viewer is closed and we have a deck loaded
        if self.stacked_widget.currentIndex() in [0, 1, 2] and hasattr(self, 'stacked_deck') and self.stacked_deck.media_paths:
            self.stacked_widget.setCurrentIndex(4)
            self.close_button.show()
            self.close_button.raise_()
            self.on_deck_count_changed(len(self.stacked_deck.media_paths))
            return

        self.anim.stop()
        self.stacked_widget.setGraphicsEffect(None)
        self.media_player.stop()

        self.pdf_viewer.clear()

        self.current_filepath = None
        self.current_pixmap = None
        self.image_scroll.set_pixmap(QPixmap())
        self.stacked_deck.clear()

        self.stacked_widget.setCurrentIndex(3)
        self.placeholder_icon.setText("🖼️")
        self.placeholder_text.setText("Select a media file or drop multiple items here")
        self.close_button.hide()
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
        super().resizeEvent(event)

        margin = 15
        self.close_button.move(margin, margin)
        self.close_button.raise_()

        if hasattr(self, 'drag_overlay'):
            self.drag_overlay.setGeometry(self.rect())
