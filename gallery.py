import sys
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication

from config.constants import *
from services.media_scanner import ImageWorker
from services.thumbnail_loader import ThumbnailLoader
from components.sidebar import ImageCard, SidebarListWidget
from components.image_viewer import ZoomableImageScrollArea
from components.stacked_deck import StackedDeckViewer
from components.drag_overlay import DragHighlightOverlay
from components.detail_viewer import DetailViewer
from components.main_window import MainWindow

__all__ = [
    "ImageWorker", "ThumbnailLoader", "ImageCard", "SidebarListWidget",
    "ZoomableImageScrollArea", "StackedDeckViewer", "DragHighlightOverlay",
    "DetailViewer", "MainWindow",
]


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
