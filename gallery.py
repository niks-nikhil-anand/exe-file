import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QLabel, QScrollArea, QGridLayout
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


class ImageGallery(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Gallery")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        grid = QGridLayout(container)

        folder = os.path.dirname(os.path.abspath(sys.argv[0]))

        image_files = [
            f for f in os.listdir(folder)
            if f.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
            )
        ]

        row = 0
        col = 0

        for img in image_files:
            label = QLabel()

            pixmap = QPixmap(os.path.join(folder, img))
            pixmap = pixmap.scaled(
                250, 250,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            grid.addWidget(label, row, col)

            col += 1
            if col == 3:
                col = 0
                row += 1

        scroll.setWidget(container)
        layout.addWidget(scroll)


app = QApplication(sys.argv)

window = ImageGallery()
window.show()

sys.exit(app.exec())