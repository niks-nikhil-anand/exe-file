import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QPushButton
)
from PyQt5.QtGui import QPainter, QColor, QPen, QTransform, QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve, QRect, QPoint, QTimer

from config.constants import IMAGE_EXTS, VIDEO_EXTS, PDF_EXTS
from components.image_viewer import ZoomableImageScrollArea
from components.video_viewer import VideoViewer
from components.pdf_viewer import PdfViewer

class DraggableTopCard(QFrame):
    dragged_away = pyqtSignal()
    fullscreen_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            DraggableTopCard {
                background-color: #1e1e1e;
                border: 2px solid #333;
                border-radius: 8px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.handle = QFrame()
        self.handle.setFixedHeight(30)
        self.handle.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom: 1px solid #444;
            }
            QFrame:hover {
                background-color: #353535;
            }
        """)
        self.handle.setCursor(Qt.CursorShape.OpenHandCursor)
        handle_layout = QHBoxLayout(self.handle)
        handle_layout.setContentsMargins(10, 0, 10, 0)
        
        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(24, 24)
        self.btn_fullscreen.setStyleSheet("""
            QPushButton { background: transparent; color: #aaa; border: none; font-size: 16px; }
            QPushButton:hover { color: #fff; }
        """)
        self.btn_fullscreen.clicked.connect(self.fullscreen_requested.emit)
        
        handle_layout.addWidget(self.btn_fullscreen)
        handle_layout.addStretch()
        
        handle_indicator = QFrame()
        handle_indicator.setFixedSize(40, 4)
        handle_indicator.setStyleSheet("background-color: #666; border-radius: 2px;")
        handle_layout.addWidget(handle_indicator)
        
        handle_layout.addStretch()
        
        self.layout.addWidget(self.handle)
        
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.content_container)
        
        self.active_viewer = None
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.original_pos = QPoint()
        
    def set_media(self, filepath):
        if self.active_viewer:
            if hasattr(self.active_viewer, 'stop'):
                self.active_viewer.stop()
            self.content_layout.removeWidget(self.active_viewer)
            self.active_viewer.setParent(None)
            self.active_viewer.deleteLater()
            self.active_viewer = None
            
        lower_path = filepath.lower()
        if lower_path.endswith(IMAGE_EXTS):
            self.active_viewer = ZoomableImageScrollArea()
            self.active_viewer.set_pixmap(QPixmap(filepath))
        elif lower_path.endswith(VIDEO_EXTS):
            self.active_viewer = VideoViewer()
            self.active_viewer.load_media(filepath)
        elif lower_path.endswith(PDF_EXTS):
            self.active_viewer = PdfViewer()
            self.active_viewer.load_document(filepath)
        else:
            self.active_viewer = QLabel(f"Preview not available for:\n{os.path.basename(filepath)}")
            self.active_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.active_viewer.setStyleSheet("color: #888; font-size: 16px;")
            
        self.content_layout.addWidget(self.active_viewer)
        
        # Propagate fullscreen state if it exists
        parent_deck = self.parentWidget()
        if parent_deck and hasattr(parent_deck, 'is_fullscreen'):
            if hasattr(self.active_viewer, 'set_fullscreen_mode'):
                self.active_viewer.set_fullscreen_mode(parent_deck.is_fullscreen)

    def set_fullscreen_mode(self, is_full):
        if hasattr(self, 'active_viewer') and hasattr(self.active_viewer, 'set_fullscreen_mode'):
            self.active_viewer.set_fullscreen_mode(is_full)

    def stop_media(self):
        if hasattr(self.active_viewer, 'stop'):
            self.active_viewer.stop()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.handle.geometry().contains(event.pos()):
            self.is_dragging = True
            self.handle.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.drag_start_pos = event.globalPos()
            self.original_pos = self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.globalPos() - self.drag_start_pos
            self.move(self.original_pos + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.handle.setCursor(Qt.CursorShape.OpenHandCursor)
            # Reverted to snap back instead of dismiss to prevent clearing the stack
            self.animate_return()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
    def animate_dismiss(self, delta):
        # Extend the delta to push it fully off screen
        fly_delta = delta * 3
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        end_pos = self.pos() + fly_delta
        self.anim.setEndValue(end_pos)
        self.anim.finished.connect(self.dragged_away.emit)
        self.anim.start()
        
    def animate_return(self):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setEndValue(self.original_pos)
        self.anim.start()

class StackedDeckViewer(QWidget):
    deck_empty = pyqtSignal()
    deck_count_changed = pyqtSignal(int)
    fullscreen_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_paths = []
        self.is_hovered = False
        self.is_fullscreen = False
        self.setMouseTracking(True)
        
        self.top_card = DraggableTopCard(self)
        self.top_card.dragged_away.connect(self.on_top_card_removed)
        self.top_card.fullscreen_requested.connect(self.fullscreen_requested.emit)
        self.top_card.hide()
        
        self.btn_prev = QPushButton("❮", self)
        self.btn_prev.setFixedSize(50, 100)
        self.btn_prev.setStyleSheet("""
            QPushButton { background: rgba(30,30,30,0.6); color: white; border: none; border-radius: 8px; font-size: 24px; font-weight: bold; }
            QPushButton:hover { background: rgba(80,80,80,0.8); }
        """)
        self.btn_prev.clicked.connect(self.prev_card)
        self.btn_prev.hide()
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_next = QPushButton("❯", self)
        self.btn_next.setFixedSize(50, 100)
        self.btn_next.setStyleSheet(self.btn_prev.styleSheet())
        self.btn_next.clicked.connect(self.next_card)
        self.btn_next.hide()
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.hover_anim_progress = 0.0
        self.hover_anim = QPropertyAnimation(self, b"hover_progress")
        self.hover_anim.setDuration(300)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Max visible background cards
        self.max_bg_cards = 4
        
    def get_hover_progress(self):
        return self.hover_anim_progress
        
    def set_hover_progress(self, val):
        self.hover_anim_progress = val
        self.update()
        
    hover_progress = pyqtProperty(float, get_hover_progress, set_hover_progress)
    
    def load_media(self, paths):
        # paths is a list of file paths. First item is the top of the stack.
        self.media_paths = paths.copy()
        if self.media_paths:
            self.top_card.set_media(self.media_paths[0])
            self.top_card.show()
            self.deck_count_changed.emit(len(self.media_paths))
            self.layout_cards()
            self.animate_deck_entry()
            self.update_nav_buttons()
        else:
            self.top_card.hide()
            self.deck_empty.emit()
            self.update_nav_buttons()
            
    def append_media(self, paths):
        # Insert new paths at the beginning so they become the new top of the stack
        self.media_paths = paths + self.media_paths
        
        self.top_card.set_media(self.media_paths[0])
        # Reset position instantly in case it was animating
        self.top_card.move(self.top_card.original_pos)
        self.top_card.show()
        self.layout_cards()
        self.animate_deck_entry()
        
        self.deck_count_changed.emit(len(self.media_paths))
        self.update_nav_buttons()
        self.update()
            
    def on_top_card_removed(self):
        self.top_card.stop_media()
        if self.media_paths:
            self.media_paths.pop(0)
            
        self.deck_count_changed.emit(len(self.media_paths))
        if self.media_paths:
            self.top_card.set_media(self.media_paths[0])
            # Reset position instantly
            self.top_card.move(self.top_card.original_pos)
            self.top_card.show()
            
            # Animate the new top card scaling up slightly
            self.effect = QGraphicsOpacityEffect(self.top_card)
            self.top_card.setGraphicsEffect(self.effect)
            self.fade_in = QPropertyAnimation(self.effect, b"opacity")
            self.fade_in.setDuration(200)
            self.fade_in.setStartValue(0.0)
            self.fade_in.setEndValue(1.0)
            self.fade_in.finished.connect(lambda: self.top_card.setGraphicsEffect(None))
            self.fade_in.start()
            
            self.update_nav_buttons()
            self.update()
        else:
            self.top_card.hide()
            self.deck_empty.emit()
            self.update_nav_buttons()
            
    def animate_deck_entry(self):
        self.effect = QGraphicsOpacityEffect(self.top_card)
        self.top_card.setGraphicsEffect(self.effect)
        self.entry_anim = QPropertyAnimation(self.effect, b"opacity")
        self.entry_anim.setDuration(300)
        self.entry_anim.setStartValue(0.0)
        self.entry_anim.setEndValue(1.0)
        self.entry_anim.finished.connect(lambda: self.top_card.setGraphicsEffect(None))
        self.entry_anim.start()
            
    def set_fullscreen_mode(self, is_full):
        self.is_fullscreen = is_full
        if hasattr(self, 'top_card') and hasattr(self.top_card, 'set_fullscreen_mode'):
            self.top_card.set_fullscreen_mode(is_full)
        self.update_nav_buttons()
        self.layout_cards()
        self.update()
        
    def update_nav_buttons(self):
        if self.is_fullscreen and len(self.media_paths) > 1:
            self.btn_prev.show()
            self.btn_next.show()
            self.btn_prev.raise_()
            self.btn_next.raise_()
        else:
            self.btn_prev.hide()
            self.btn_next.hide()

    def prev_card(self):
        if len(self.media_paths) > 1:
            self.top_card.stop_media()
            self.media_paths.insert(0, self.media_paths.pop())
            self.top_card.set_media(self.media_paths[0])
            self.update()

    def next_card(self):
        if len(self.media_paths) > 1:
            self.top_card.stop_media()
            self.media_paths.append(self.media_paths.pop(0))
            self.top_card.set_media(self.media_paths[0])
            self.update()

    def layout_cards(self):
        if not self.media_paths:
            return
            
        rect = self.rect()
        margin = 0 if self.is_fullscreen else 50
        card_w = rect.width() - margin * 2
        card_h = rect.height() - margin * 2
        
        # Center position
        x = (rect.width() - card_w) // 2
        y = (rect.height() - card_h) // 2
        
        self.top_card.setGeometry(x, y, card_w, card_h)
        self.top_card.original_pos = QPoint(x, y)
        
        self.btn_prev.move(20, (rect.height() - self.btn_prev.height()) // 2)
        self.btn_next.move(rect.width() - self.btn_next.width() - 20, (rect.height() - self.btn_next.height()) // 2)
        
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_cards()
        
    def enterEvent(self, event):
        self.is_hovered = True
        self.hover_anim.setDirection(QPropertyAnimation.Direction.Forward)
        if self.hover_anim.state() != QPropertyAnimation.State.Running:
            self.hover_anim.setStartValue(self.hover_anim_progress)
            self.hover_anim.setEndValue(1.0)
            self.hover_anim.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.is_hovered = False
        self.hover_anim.setDirection(QPropertyAnimation.Direction.Backward)
        if self.hover_anim.state() != QPropertyAnimation.State.Running:
            self.hover_anim.setStartValue(self.hover_anim_progress)
            self.hover_anim.setEndValue(0.0)
            self.hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if len(self.media_paths) <= 1 or self.is_fullscreen:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        margin = 50
        card_w = rect.width() - margin * 2
        card_h = rect.height() - margin * 2
        cx = rect.width() / 2
        cy = rect.height() / 2
        
        num_bg_cards = min(len(self.media_paths) - 1, self.max_bg_cards)
        
        # Draw from bottom-most to top-most (excluding actual top card)
        for i in range(num_bg_cards, 0, -1):
            painter.save()
            
            painter.translate(cx, cy)
            
            # Fan out based on hover progress and index
            base_rot = i * 2.0 * (-1 if i % 2 == 0 else 1)
            hover_rot = i * 4.0 * (-1 if i % 2 == 0 else 1)
            rot = base_rot + (hover_rot - base_rot) * self.hover_anim_progress
            
            base_y = i * 5.0
            hover_y = i * -15.0 # Lift up
            hover_x = i * 25.0 * (-1 if i % 2 == 0 else 1)
            y_offset = base_y + (hover_y - base_y) * self.hover_anim_progress
            x_offset = hover_x * self.hover_anim_progress
            
            painter.rotate(rot)
            painter.translate(x_offset, y_offset)
            
            card_rect = QRect(-card_w // 2, -card_h // 2, card_w, card_h)
            
            # Shadow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 60))
            painter.drawRoundedRect(card_rect.translated(0, 8), 8, 8)
            
            # Card background
            darkness = 40 - (i * 4)
            painter.setBrush(QColor(darkness, darkness, darkness))
            painter.setPen(QPen(QColor(70, 70, 70), 2))
            painter.drawRoundedRect(card_rect, 8, 8)
            
            # Icon placeholder
            filepath = self.media_paths[i]
            lower_path = filepath.lower()
            painter.setPen(QColor(120, 120, 120))
            font = painter.font()
            font.setPointSize(36)
            painter.setFont(font)
            
            icon_char = "📄"
            if lower_path.endswith(IMAGE_EXTS): icon_char = "🖼️"
            elif lower_path.endswith(VIDEO_EXTS): icon_char = "🎬"
            elif lower_path.endswith(PDF_EXTS): icon_char = "📑"
            
            painter.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, icon_char)
            
            painter.restore()

    def clear(self):
        self.top_card.stop_media()
        self.top_card.hide()
        self.media_paths.clear()
        self.deck_count_changed.emit(0)
        self.update()
        
    def stop(self):
        self.top_card.stop_media()
