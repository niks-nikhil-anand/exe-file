import os
import sys
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton

from components.detail_viewer import DetailViewer
from components.main_window import MainWindow
from components.pdf_viewer import PdfViewer
from components.video_viewer import VideoViewer
from services.media_scanner import ImageWorker
from services.thumbnail_loader import ThumbnailLoader


app = QApplication.instance() or QApplication(sys.argv)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMediaComponents(unittest.TestCase):
    def test_main_window_has_no_gallery_title(self):
        with patch.object(ThumbnailLoader, "start"), patch.object(ImageWorker, "start"):
            window = MainWindow()
            self.assertEqual(window.windowTitle(), "")
            window.close()

    def test_empty_gallery_has_no_title_description_or_internet_card_button(self):
        viewer = DetailViewer()

        self.assertEqual(viewer.placeholder_container.findChildren(QLabel), [])
        button_texts = [button.text().strip().lower() for button in viewer.findChildren(QPushButton)]
        self.assertNotIn("add internet card", button_texts)

        viewer.shutdown()

    def test_pdf_component_loads_and_zooms(self):
        viewer = PdfViewer()
        path = os.path.join(PROJECT_ROOT, "public", "sample.pdf")

        self.assertTrue(viewer.load_document(path))
        self.assertIsNotNone(viewer.document)
        initial_zoom = viewer.zoom
        viewer.zoom_in()
        self.assertGreater(viewer.zoom, initial_zoom)

        viewer.clear()
        self.assertIsNone(viewer.document)

    def test_video_component_owns_playback_controls(self):
        viewer = VideoViewer()
        self.assertEqual(viewer.volume_slider.value(), 70)
        viewer.set_volume(35)
        self.assertEqual(viewer.media_player.volume(), 35)
        self.assertEqual(viewer.time_label.text(), "00:00 / 00:00")
        viewer.stop()


if __name__ == "__main__":
    unittest.main()
