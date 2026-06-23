import os
import sys
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
    QEvent, QSize, QTimer, QMimeData, QFileSystemWatcher
)

from config.constants import BG_COLOR, SCROLLBAR_BG, SCROLLBAR_HANDLE
from services.media_scanner import ImageWorker
from services.thumbnail_loader import ThumbnailLoader
from components.sidebar import ImageCard, SidebarListWidget
from components.detail_viewer import DetailViewer
from components.thumbnail_strip import ThumbnailStrip

def get_untranslocated_path(app_path):
    if sys.platform != 'darwin':
        return app_path
    try:
        import subprocess
        cmd = ['/usr/bin/security', 'translocate-original-path', app_path]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in lines:
            if line.startswith('/') or (len(line) > 1 and line[1] == ':'):
                return line
            if not line.startswith('Original Path:'):
                return line
    except Exception:
        pass
    return app_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Image Gallery")
        self.resize(1200, 800)
        self.setStyleSheet(f"background-color: {BG_COLOR.name()};")

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        self.detail_viewer = DetailViewer()
        self.detail_viewer.media_closed.connect(self.clear_selection)
        self.detail_viewer.image_clicked.connect(self.toggle_fullscreen)
        self.detail_viewer.fullscreen_requested.connect(self.toggle_fullscreen)
        self.splitter.addWidget(self.detail_viewer)

        self.sidebar_container = QWidget()
        self.sidebar_container.setFixedWidth(300)
        self.sidebar_container.setStyleSheet("background-color: #1a1a1a; border-left: 1px solid #333;")

        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {SCROLLBAR_BG};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {SCROLLBAR_HANDLE};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #777777;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.list_widget = SidebarListWidget()
        self.list_widget.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.list_widget.selection_box_changed.connect(self.on_selection_box_changed)
        self.list_widget.selection_box_finished.connect(self.on_selection_box_changed)

        self.scroll_area.setWidget(self.list_widget)
        sidebar_layout.addWidget(self.scroll_area)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self.trigger_lazy_load)

        self.splitter.addWidget(self.sidebar_container)
        self.splitter.setSizes([int(1200 * 0.7), int(1200 * 0.3)])

        self.cards = []
        self.current_index = -1

        # Initialize thumbnail loader
        self.thumb_loader = ThumbnailLoader()
        self.thumb_loader.thumbnail_loaded.connect(self.on_thumbnail_loaded)
        self.thumb_loader.start()

        if getattr(sys, 'frozen', False):
            exec_dir = os.path.dirname(os.path.abspath(sys.executable))
            if "Contents/MacOS" in exec_dir:
                app_path = os.path.abspath(os.path.join(exec_dir, "..", ".."))
                resolved_app_path = get_untranslocated_path(app_path)
                base_dir = os.path.abspath(os.path.join(resolved_app_path, ".."))
            else:
                base_dir = exec_dir
            
            parent_dir = os.path.abspath(os.path.join(base_dir, ".."))
            has_media_subfolders = any(
                os.path.isdir(os.path.join(base_dir, sub))
                for sub in ["images", "videos", "pdf", "others"]
            )
            has_parent_media_subfolders = any(
                os.path.isdir(os.path.join(parent_dir, sub))
                for sub in ["images", "videos", "pdf", "others"]
            )
            if not has_media_subfolders and has_parent_media_subfolders:
                folder = parent_dir
            else:
                folder = base_dir
        else:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            public_dir = os.path.join(base_dir, "public")
            folder = public_dir if os.path.exists(public_dir) else base_dir

        self.scan_folder = folder
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.on_directory_changed)
        self.setup_watcher(self.scan_folder)
        
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_directories)
        self.poll_timer.start(2000)
        
        self.start_scan()

        self.setMouseTracking(True)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        self.setup_fullscreen_buttons()

    def setup_fullscreen_buttons(self):
        self.fs_prev_btn = QPushButton("❮", self)
        self.fs_prev_btn.setFixedSize(50, 100)
        self.fs_prev_btn.setStyleSheet("""
            QPushButton { background: rgba(30, 30, 30, 0.6); color: white; border: none; border-radius: 8px; font-size: 24px; }
            QPushButton:hover { background: rgba(80, 80, 80, 0.8); }
        """)
        self.fs_prev_btn.clicked.connect(self.go_prev_asset)
        self.fs_prev_btn.hide()
        
        self.fs_next_btn = QPushButton("❯", self)
        self.fs_next_btn.setFixedSize(50, 100)
        self.fs_next_btn.setStyleSheet(self.fs_prev_btn.styleSheet())
        self.fs_next_btn.clicked.connect(self.go_next_asset)
        self.fs_next_btn.hide()

    def go_prev_asset(self):
        if self.current_index > 0:
            self.select_card(self.current_index - 1)

    def go_next_asset(self):
        if self.current_index < len(self.cards) - 1:
            self.select_card(self.current_index + 1)

    def on_thumbnail_clicked(self, filepath):
        for i, card in enumerate(self.cards):
            if card.filepath == filepath:
                self.select_card(i)
                break

    def trigger_lazy_load(self):
        if not hasattr(self, 'cards') or not self.cards:
            return
        viewport_rect = self.scroll_area.viewport().rect()
        for card in self.cards:
            if not card.thumb_loaded:
                try:
                    top_left = card.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
                    bottom_right = card.mapTo(self.scroll_area.viewport(), QPoint(card.width(), card.height()))
                    card_rect = QRect(top_left, bottom_right)
                    if viewport_rect.intersects(card_rect):
                        card.thumb_loaded = True
                        self.thumb_loader.queue_request(card.filepath)
                except Exception:
                    pass

    def on_thumbnail_loaded(self, filepath, pixmap):
        for card in self.cards:
            if card.filepath == filepath:
                card.set_thumbnail(pixmap)
                break

    def add_image_card(self, filepath, filename, date_str):
        card = ImageCard(filepath, filename, date_str, self)
        card.clicked.connect(self.on_card_clicked)
        self.list_layout.addWidget(card)
        self.cards.append(card)

        if len(self.cards) == 1:
            self.select_card(0)

        QTimer.singleShot(50, self.trigger_lazy_load)

    def on_selection_box_changed(self, rect):
        modifiers = QApplication.keyboardModifiers()
        has_ctrl = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
        has_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        for card in self.cards:
            card_rect = card.geometry()
            if rect.intersects(card_rect):
                card.set_selected(True)
            else:
                if not has_ctrl and not has_shift:
                    card.set_selected(False)
        print("Debug Box Selection: Selected cards:")
        for c in self.cards:
            if c.selected:
                print(f"  - {c.name_label.text()}")

    def clear_sidebar_selection(self):
        for card in self.cards:
            card.set_selected(False)

    def start_drag_operations(self, source_card):
        print("Selected before drag:")
        for c in self.cards:
            if c.selected:
                print(f"  - {c.name_label.text()}")

        selected_cards = [c for c in self.cards if c.selected]
        print(f"Debug Drag Start: Found {len(selected_cards)} selected cards to drag (source: {source_card.name_label.text()})")
        if not selected_cards:
            selected_cards = [source_card]

        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(c.filepath) for c in selected_cards]
        mime_data.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        if selected_cards[0].thumb_label.pixmap():
            drag.setPixmap(selected_cards[0].thumb_label.pixmap())
            drag.setHotSpot(QPoint(40, 40))

        drag.exec_(Qt.DropAction.CopyAction)

        print("Selected after drag start:")
        for c in self.cards:
            if c.selected:
                print(f"  - {c.name_label.text()}")

    def clear_selection(self):
        if getattr(self, 'is_fullscreen', False):
            self.toggle_fullscreen()
        if self.current_index != -1:
            self.cards[self.current_index].set_selected(False)
            self.current_index = -1

    def update_fullscreen_overlay(self):
        if not getattr(self, 'is_fullscreen', False):
            return
        
        self.fs_prev_btn.setVisible(self.current_index > 0)
        self.fs_next_btn.setVisible(self.current_index < len(self.cards) - 1)
        self.position_fs_buttons()

    def position_fs_buttons(self):
        if hasattr(self, 'fs_prev_btn') and hasattr(self, 'fs_next_btn'):
            center_y = self.height() // 2 - 50
            self.fs_prev_btn.move(20, center_y)
            self.fs_next_btn.move(self.width() - 70, center_y)
            self.fs_prev_btn.raise_()
            self.fs_next_btn.raise_()

    def toggle_fullscreen(self):
        if not hasattr(self, 'is_fullscreen'):
            self.is_fullscreen = False
        self.is_fullscreen = not self.is_fullscreen
        
        self.detail_viewer.set_fullscreen_mode(self.is_fullscreen)

        if self.is_fullscreen:
            self.sidebar_container.hide()
            self.showFullScreen()
            self.update_fullscreen_overlay()
        else:
            self.sidebar_container.show()
            self.showNormal()
            self.fs_prev_btn.hide()
            self.fs_next_btn.hide()
            
        if hasattr(self.detail_viewer, 'set_fullscreen_mode'):
            self.detail_viewer.set_fullscreen_mode(self.is_fullscreen)

    def enter_fullscreen(self):
        if not getattr(self, 'is_fullscreen', False):
            self.toggle_fullscreen()

    def eventFilter(self, watched, event):
        return super().eventFilter(watched, event)

    def on_card_clicked(self, filepath, card):
        modifiers = QApplication.keyboardModifiers()
        has_ctrl = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier))
        has_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        index = self.cards.index(card)
        print(f"Debug on_card_clicked: {card.name_label.text()} (ctrl={has_ctrl}, shift={has_shift})")

        if has_ctrl:
            card.set_selected(not card.selected)
            if card.selected:
                self.current_index = index
        elif has_shift:
            if self.current_index != -1:
                start = min(self.current_index, index)
                end = max(self.current_index, index)
                for i, c in enumerate(self.cards):
                    c.set_selected(start <= i <= end)
            else:
                card.set_selected(True)
                self.current_index = index
        else:
            for c in self.cards:
                c.set_selected(c == card)
            self.current_index = index

        print("Debug on_card_clicked: Selected cards:")
        for c in self.cards:
            if c.selected:
                print(f"  - {c.name_label.text()}")

    def select_card(self, index):
        if index < 0 or index >= len(self.cards):
            return

        if self.current_index != -1:
            self.cards[self.current_index].set_selected(False)

        self.current_index = index
        selected_card = self.cards[self.current_index]
        selected_card.set_selected(True)

        self.scroll_area.ensureWidgetVisible(selected_card)
        self.update_fullscreen_overlay()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            if getattr(self, 'is_fullscreen', False):
                self.toggle_fullscreen()
                event.accept()
                return
        if event.key() == Qt.Key.Key_Left:
            if self.detail_viewer.stacked_widget.currentIndex() == 4:
                self.detail_viewer.stacked_deck.prev_card()
                event.accept()
                return
        elif event.key() == Qt.Key.Key_Right:
            if self.detail_viewer.stacked_widget.currentIndex() == 4:
                self.detail_viewer.stacked_deck.next_card()
                event.accept()
                return
        if event.key() == Qt.Key.Key_Up:
            if self.current_index > 0:
                self.select_card(self.current_index - 1)
        elif event.key() == Qt.Key.Key_Down:
            if self.current_index < len(self.cards) - 1:
                self.select_card(self.current_index + 1)
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, 'is_fullscreen', False):
            self.position_fs_buttons()
        self.trigger_lazy_load()

    def setup_watcher(self, folder):
        existing_paths = set(self.watcher.directories())
        paths_to_watch = set()
        
        if os.path.exists(folder):
            paths_to_watch.add(folder)
            
        subfolders = ["images", "videos", "pdf", "others"]
        for sub in subfolders:
            subpath = os.path.join(folder, sub)
            if os.path.isdir(subpath):
                paths_to_watch.add(subpath)
                
        new_paths = list(paths_to_watch - existing_paths)
        removed_paths = list(existing_paths - paths_to_watch)
        
        if new_paths:
            self.watcher.addPaths(new_paths)
        if removed_paths:
            self.watcher.removePaths(removed_paths)

    def on_directory_changed(self, path):
        print(f"Directory changed: {path}")
        self.setup_watcher(self.scan_folder)
        self.start_scan()

    def poll_directories(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
        self.start_scan()

    def start_scan(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.scan_queued = True
            return
            
        self.scan_queued = False
        self.scanned_filepaths = set()
        
        self.worker = ImageWorker(self.scan_folder)
        self.worker.file_found.connect(self.on_file_found_during_scan)
        self.worker.finished_loading.connect(self.on_scan_finished)
        self.worker.start()

    def on_file_found_during_scan(self, filepath, filename, date_str):
        self.scanned_filepaths.add(filepath)
        
        exists = any(card.filepath == filepath for card in self.cards)
        if not exists:
            card = ImageCard(filepath, filename, date_str, self)
            card.clicked.connect(self.on_card_clicked)
            self.list_layout.addWidget(card)
            self.cards.append(card)
            
            self.sort_cards()
            
            if len(self.cards) == 1:
                self.select_card(0)
                
            QTimer.singleShot(50, self.trigger_lazy_load)

    def on_scan_finished(self):
        removed_any = False
        selected_card = self.cards[self.current_index] if 0 <= self.current_index < len(self.cards) else None
        
        for card in list(self.cards):
            if card.filepath not in self.scanned_filepaths:
                self.list_layout.removeWidget(card)
                card.deleteLater()
                self.cards.remove(card)
                removed_any = True
                
        if removed_any:
            self.sort_cards()
            if selected_card and selected_card in self.cards:
                self.current_index = self.cards.index(selected_card)
            else:
                if self.cards:
                    self.select_card(0)
                else:
                    self.current_index = -1
                    self.detail_viewer.clear_media()
        
        QTimer.singleShot(50, self.trigger_lazy_load)
        
        if getattr(self, 'scan_queued', False):
            self.start_scan()

    def sort_cards(self):
        selected_card = self.cards[self.current_index] if 0 <= self.current_index < len(self.cards) else None
        self.cards.sort(key=lambda c: os.path.basename(c.filepath).lower())
        for i, card in enumerate(self.cards):
            self.list_layout.insertWidget(i, card)
        if selected_card and selected_card in self.cards:
            self.current_index = self.cards.index(selected_card)
        else:
            self.current_index = -1

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
        self.thumb_loader.stop()
        self.detail_viewer.shutdown()
        super().closeEvent(event)
