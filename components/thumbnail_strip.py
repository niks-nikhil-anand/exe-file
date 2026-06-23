from PyQt5.QtWidgets import QWidget, QHBoxLayout, QScrollArea, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QPainter, QColor

class ThumbnailCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setFixedSize(80, 80)
        self.setStyleSheet("""
            ThumbnailCard {
                background-color: #222;
                border: 2px solid transparent;
                border-radius: 8px;
            }
            ThumbnailCard[active="true"] {
                border: 2px solid #0078d7;
            }
        """)
        self.setProperty("active", False)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

    def set_pixmap(self, pixmap):
        scaled = pixmap.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def set_active(self, is_active):
        self.setProperty("active", is_active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.filepath)

class ThumbnailStrip(QScrollArea):
    item_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QScrollArea {
                background-color: rgba(20, 20, 20, 0.85);
            }
            QScrollBar:horizontal {
                height: 8px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self.container)

        self.cards = []
        self.active_filepath = None

    def add_thumbnail(self, filepath, pixmap=None):
        card = ThumbnailCard(filepath)
        if pixmap:
            card.set_pixmap(pixmap)
        card.clicked.connect(self.on_item_clicked)
        self.layout.addWidget(card)
        self.cards.append(card)

    def set_thumbnails(self, filepaths):
        self.clear()
        for filepath in filepaths:
            self.add_thumbnail(filepath)

    def update_thumbnail(self, filepath, pixmap):
        for card in self.cards:
            if card.filepath == filepath:
                card.set_pixmap(pixmap)
                break

    def set_active(self, filepath):
        self.active_filepath = filepath
        for card in self.cards:
            is_active = (card.filepath == filepath)
            card.set_active(is_active)
            if is_active:
                self.ensureWidgetVisible(card)

    def on_item_clicked(self, filepath):
        self.item_clicked.emit(filepath)

    def clear(self):
        for card in self.cards:
            self.layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()
        self.active_filepath = None
