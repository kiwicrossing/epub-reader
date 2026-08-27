import math
import shutil
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QListView,
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
)

from models.library import LibraryModel
from models.bookmarks import BookmarkModel
from models.settings import Settings
from readers.epub_reader import EpubReader
from ui.bookmark_dialog import BookmarkDialog
from ui.navigation import Navigation
from ui.pagination import Pagination


class MainWindow(QMainWindow):
    def __init__(self):
        """Initialize the main window and application state."""
        super().__init__()

        self.chapter_page_counts = []
        self.book_total_pages = 0
        self.book_pages_read = 0

        self.page_count_index = 0
        # self.page_count_callback = None
        self.measured_content_height = 0

        self.setWindowTitle("EPUB Reader")
        self.resize(1200, 800)
        self.page_margin = 120

        self.library = LibraryModel()
        self.bookmarks = BookmarkModel()

        self.reader = None
        self.current_book_id = None

        self.settings = Settings()
        settings = self.settings.load()
        self.font_size = settings.get("font_size", 20)

        self.go_to_last_page = False
        self.current_page = 0
        self.total_pages = 1
        self.resize_progress = None
        self.is_calculating_book_pages = False

        # timer for resizing window size
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize_finished)

        self._create_ui()
        self._load_library()
        self.load_last_book()

    def _create_ui(self):
        """Create and configure all UI elements."""

        #
        # Toolbar
        #
        self.home_toolbar = QToolBar()
        self.addToolBar(self.home_toolbar)

        self.reader_toolbar = QToolBar()
        self.addToolBar(self.reader_toolbar)

        home_btn = QPushButton("Home")
        open_btn = QPushButton("Open")

        # Top bar buttons.
        next_chapter_btn = QPushButton("Next Chapter")
        prev_chapter_btn = QPushButton("Previous Chapter")
        next_page_btn = QPushButton("Next Page")
        prev_page_btn = QPushButton("Previous Page")
        view_bookmarks_btn = QPushButton("Bookmarks")
        bookmark_btn = QPushButton("Add Bookmark")

        #
        # Font dropdown
        #
        font_btn = QToolButton()
        font_btn.setText("Font")
        font_btn.setPopupMode(QToolButton.InstantPopup)

        font_menu = QMenu(font_btn)

        font_larger_action = QAction("A+", self)
        font_smaller_action = QAction("A-", self)

        font_larger_action.triggered.connect(
            self.increase_font_size
        )
        font_smaller_action.triggered.connect(
            self.decrease_font_size
        )

        font_menu.addAction(font_larger_action)
        font_menu.addAction(font_smaller_action)
        font_btn.setMenu(font_menu)

        #
        # Toolbar order
        #
        self.home_toolbar.addWidget(home_btn)
        self.home_toolbar.addWidget(open_btn)
        self.reader_toolbar.addWidget(next_chapter_btn)
        self.reader_toolbar.addWidget(prev_chapter_btn)
        self.reader_toolbar.addWidget(next_page_btn)
        self.reader_toolbar.addWidget(prev_page_btn)
        self.reader_toolbar.addWidget(view_bookmarks_btn)
        self.reader_toolbar.addWidget(bookmark_btn)
        self.reader_toolbar.addWidget(font_btn)

        #
        # Toolbar actions
        #
        home_btn.clicked.connect(self.show_home)
        open_btn.clicked.connect(self.open_book)
        next_chapter_btn.clicked.connect(self.next_chapter)
        prev_chapter_btn.clicked.connect(self.previous_chapter)
        next_page_btn.clicked.connect(self.next_page)
        prev_page_btn.clicked.connect(self.previous_page)
        view_bookmarks_btn.clicked.connect(self.show_bookmarks)
        bookmark_btn.clicked.connect(self.add_bookmark)

        #
        # Home page
        #
        self.home_page = QWidget()
        home_layout = QVBoxLayout(self.home_page)
        library_title = QLabel("My Library")
        library_title.setStyleSheet("""
        QLabel {
            font-size: 24px;
            font-weight: bold;
            color: #3f1219;
            padding: 12px;
        }
        """)

        self.library_grid = QListWidget()

        self.library_grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.library_grid.customContextMenuRequested.connect(self.show_library_context_menu)

        # make covers look like tiles
        self.library_grid.setViewMode(QListView.IconMode)
        self.library_grid.setResizeMode(QListWidget.Adjust)
        self.library_grid.setMovement(QListView.Static)
        self.library_grid.setSpacing(25)
        self.library_grid.setGridSize(QSize(180, 310))
        self.library_grid.setWordWrap(True)

        # self.library_grid.setIconSize(QSize(150, 220))
        self.library_grid.setSpacing(20)

        self.library_grid.setStyleSheet("""
        QListWidget {
            background-color: #fef2f1;
            border: none;
        }

        QListWidget::item:selected {
            background-color: #fec0c4;
            border-radius: 6px;
        }
        """)

        self.library_grid.itemDoubleClicked.connect(self.library_book_selected)

        home_layout.addWidget(library_title)
        home_layout.addWidget(self.library_grid)

        self.bookmark_list = QListWidget()

        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.calculate_pages)

        self.web_view.setStyleSheet("""
        QWebEngineView {
            background-color: #fef2f1;
            border-left: 1px solid #fad3d1;
            border-right: 1px solid #fad3d1;
        }
        """)

        self.page_counter_view = QWebEngineView(self)

        # QWebEngineView must be shown for Chromium to maintain
        # the correct internal viewport size. Place it off-screen
        # so the user never sees it.
        self.page_counter_view.move(-10000, -10000)
        self.page_counter_view.resize(self.web_view.size())
        self.page_counter_view.show()

        self.page_counter_view.loadFinished.connect(
            self._measure_loaded_chapter
        )

        #
        # Reader widgets
        #
        self.chapter_list = QListWidget()
        self.chapter_list.itemDoubleClicked.connect(self.chapter_selected)
        self.chapter_dock = QDockWidget("Chapters")
        self.chapter_dock.setWidget(self.chapter_list)
        self.addDockWidget(Qt.LeftDockWidgetArea,self.chapter_dock)

        self.front_matter_list = QListWidget()
        self.front_matter_list.itemDoubleClicked.connect(self.front_matter_selected)
        self.front_matter_dock = QDockWidget("Front Matter")
        self.front_matter_dock.setWidget(self.front_matter_list)
        self.addDockWidget(Qt.LeftDockWidgetArea,self.front_matter_dock)

        self.back_matter_list = QListWidget()
        self.back_matter_list.itemDoubleClicked.connect(self.back_matter_selected)
        self.back_matter_dock = QDockWidget("Back Matter")
        self.back_matter_dock.setWidget(self.back_matter_list)
        self.addDockWidget(Qt.LeftDockWidgetArea,self.back_matter_dock)

        self.splitDockWidget(
            self.front_matter_dock,
            self.back_matter_dock,
            Qt.Vertical
        )
        self.front_matter_dock.setMaximumHeight(120)
        self.back_matter_dock.setMaximumHeight(80)
        self.chapter_list.setMaximumWidth(180)
        self.front_matter_list.setMaximumWidth(180)
        self.back_matter_list.setMaximumWidth(180)

        self.bookmark_dock = QDockWidget("Bookmarks")
        self.bookmark_dock.setMinimumWidth(150)
        self.bookmark_dock.setMaximumWidth(250)
        self.bookmark_dock.setWidget(self.bookmark_list)
        self.addDockWidget(
            Qt.RightDockWidgetArea,
            self.bookmark_dock
        )
        self.bookmark_dock.setMaximumWidth(140)
        self.bookmark_list.setStyleSheet("""
        QListWidget {
            background-color: #fad3d1;
            color: #3f1219;
            border: none;
        }

        QListWidget::item:selected {
            background-color: #fec0c4;
        }
        """)

        self.bookmark_list.itemDoubleClicked.connect(self.bookmark_selected)
        self.bookmark_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmark_list.customContextMenuRequested.connect(self.show_bookmark_context_menu)

        #
        # Keyboard shortcuts for page navigation.
        # 
        next_shortcut = QShortcut(QKeySequence(Qt.Key_Right),self)
        next_shortcut.activated.connect(self.next_page)

        prev_shortcut = QShortcut(QKeySequence(Qt.Key_Left),self)
        prev_shortcut.activated.connect(self.previous_page)

        next_chapter_shortcut = QShortcut(QKeySequence("Ctrl+Right"),self)
        next_chapter_shortcut.activated.connect(self.next_chapter)

        prev_chapter_shortcut = QShortcut(QKeySequence("Ctrl+Left"),self)
        prev_chapter_shortcut.activated.connect(self.previous_chapter)

        space_shortcut = QShortcut(QKeySequence(Qt.Key_Space),self)
        space_shortcut.activated.connect(self.next_page)

        back_space_shortcut = QShortcut(QKeySequence("Shift+Space"),self)
        back_space_shortcut.activated.connect(self.previous_page)

        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete),self.bookmark_list)
        delete_shortcut.activated.connect(self.delete_selected_bookmark)

        #
        # Reader page
        #
        splitter = QSplitter()
        splitter.addWidget(self.web_view)
        self.status_label = QLabel("Ready")
        splitter.setSizes([200, 800, 200])

        self.status_label.setStyleSheet("""
        QLabel {
            color: #3f1219;
            font-weight: 500;
        }
        """)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setMaximumWidth(250)

        footer = QWidget()
        footer.setStyleSheet("""
        QWidget {
            background-color: #fce2e1;
            border-top: 1px solid #fad3d1;
        }
        """)
        footer.setMaximumHeight(35)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(5, 2, 5, 2)
        footer_layout.setSpacing(5)

        self.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid #fad3d1;
            border-radius: 6px;
            background: #fce2e1;
            color: #3f1219;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #fec0c4;
            border-radius: 5px;
        }
        """)

        self.page_count_label = QLabel("0 / 0")
        self.page_count_label.setMinimumWidth(90)

        self.page_count_label.setStyleSheet("""
        QLabel {
            color: #3f1219;
            font-weight: 500;
        }
        """)

        footer_layout.addWidget(self.status_label)
        footer_layout.addWidget(self.page_count_label)
        footer_layout.addWidget(self.progress_bar)

        self.reader_page = QWidget()
        reader_layout = QVBoxLayout(self.reader_page)
        reader_layout.addWidget(splitter)
        reader_layout.addWidget(footer)

        #
        # Stacked pages
        #
        self.stack = QStackedWidget()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.reader_page)

        self.setCentralWidget(self.stack)

        #
        # Style sheet
        #
        self.setStyleSheet("""
        QMainWindow {
            background-color: #fef2f1;
            color: #3f1219;
        }

        QWidget {
            color: #3f1219;
        }

        /* Toolbar */
        QToolBar {
            background-color: #fce2e1;
            border: none;
            spacing: 4px;
            padding: 4px;
        }

        /* Dock Widgets */
        QDockWidget {
            background-color: #fce2e1;
            color: #3f1219;
        }

        QDockWidget::title {
            background-color: #fad3d1;
            color: #3f1219;
            padding: 6px;
            font-weight: bold;
            border-bottom: 1px solid #fec0c4;
        }

        /* Lists */
        QListWidget {
            background-color: #fce2e1;
            border: none;
            color: #3f1219;
        }

        QListWidget::item {
            padding: 3px;
        }

        QListWidget::item:selected {
            background-color: #fec0c4;
            color: #3f1219;
        }

        /* Buttons */
        QPushButton {
            background-color: #fad3d1;
            color: #3f1219;
            border: 1px solid #fec0c4;
            border-radius: 6px;
            padding: 4px 10px;
        }

        QPushButton:hover {
            background-color: #fec0c4;
        }

        QPushButton:pressed {
            background-color: #fce2e1;
        }

        /* Tool Button */
        QToolButton {
            background-color: #fad3d1;
            color: #3f1219;
            border: 1px solid #fec0c4;
            border-radius: 6px;
            padding: 4px 10px;
        }

        /* Menus */
        QMenu {
            background-color: #fef2f1;
            color: #3f1219;
            border: 1px solid #fad3d1;
        }

        QMenu::item:selected {
            background-color: #fec0c4;
        }

        /* Splitters */
        QSplitter::handle {
            background-color: #fad3d1;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background-color: #fce2e1;
            width: 12px;
        }

        QScrollBar::handle:vertical {
            background-color: #fec0c4;
            border-radius: 5px;
            min-height: 25px;
        }

        QScrollBar:horizontal {
            background-color: #fce2e1;
            height: 12px;
        }

        QScrollBar::handle:horizontal {
            background-color: #fec0c4;
            border-radius: 5px;
        }
        """)

        # Hide docks
        self.chapter_dock.hide()
        self.front_matter_dock.hide()
        self.back_matter_dock.hide()
        self.bookmark_dock.hide()
        self.reader_toolbar.hide()

        #
        # Start on the home page
        #
        self.stack.setCurrentWidget(self.home_page)

    def show_home(self):
        """Display the home page."""
        self._load_library()

        self.stack.setCurrentWidget(self.home_page)

        self.home_toolbar.show()
        self.reader_toolbar.hide()

        self.chapter_dock.hide()
        self.front_matter_dock.hide()
        self.back_matter_dock.hide()
        self.bookmark_dock.hide()

    def show_library_context_menu(self, position):
        """Show the context menu for a book tile."""
        item = self.library_grid.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        open_action = menu.addAction("Open Book")
        replace_cover_action = menu.addAction("Replace Cover Image...")

        menu.addSeparator()

        delete_action = menu.addAction("Delete from Library")

        action = menu.exec(self.library_grid.mapToGlobal(position))

        if action == open_action:
            self.library_book_selected(item)

        elif action == replace_cover_action:
            self.replace_book_cover(item)

        elif action == delete_action:
            self.delete_book_from_library(item)
            

    def display_html(self, content):
        """Display raw HTML content."""
        self.web_view.setHtml(self.build_reader_html(content))

    def build_reader_html(self, content):
        """Build the styled HTML used by the reader."""
        return f"""
        <html>
        <head>
        <style>
            html {{
                overflow-x: hidden;
                overflow-y: hidden;
                background-color: #fef2f1;
            }}

            body {{
                width: min(90%, 700px);
                margin: 60px auto;
                padding: 50px 40px;

                background: white;
                box-sizing: border-box;
                border: 1px solid #fad3d1;
                border-radius: 10px;

                box-shadow:
                    0 4px 15px rgba(63, 18, 25, 0.08);

                font-family: Georgia, serif;
                font-size: {self.font_size}px;
                color: #3f1219;
                line-height: 1.7;

                overflow: hidden;
            }}

            img {{
                max-width: 100%;
            }}

            h1, h2, h3 {{
                color: #3f1219;
            }}

            a {{
                color: #8d4a58;
            }}

            blockquote {{
                border-left: 4px solid #fec0c4;
                padding-left: 15px;
                color: #5f3f45;
            }}

            hr {{
                border: none;
                border-top: 1px solid #fad3d1;
            }}
        </style>
        </head>

        <body>
            {content}
        </body>
        </html>
        """

    def create_placeholder_cover(
        self,
        title,
        output_path
    ):
        """Generate a placeholder cover image."""

        width = 300
        height = 450

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#405c7a"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))

        font = QFont("Georgia", 18)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(
            pixmap.rect().adjusted(
                20,
                20,
                -20,
                -20
            ),
            Qt.AlignCenter | Qt.TextWordWrap,
            title
        )
        painter.end()

        pixmap.save(output_path)

    def resizeEvent(self, event):
        """Handle window resizing."""
        super().resizeEvent(event)
        self.resize_timer.start(250)

    def handle_resize_finished(self):
        """Recalculate paging after resizing."""

        if not self.reader:
            return

        self.resize_progress = (
            self.current_page /
            max(1, self.total_pages - 1)
        )

        self.calculate_pages()

        QTimer.singleShot(
            250,
            self.calculate_book_page_counts
        )

    def refresh_front_matter(self):
        """Refresh the front matter list."""

        self.front_matter_list.clear()

        if not self.reader:
            return

        for index, entry in enumerate(self.reader.front_matter):
            item = QListWidgetItem(entry["title"])
            item.setData(Qt.UserRole, index)

            self.front_matter_list.addItem(item)

    def front_matter_selected(self, item):
        """Open the selected front matter item."""
        index = item.data(Qt.UserRole)

        if index is None:
            return

        self.display_html(self.reader.front_matter[index]["content"])

    def refresh_back_matter(self):
        """Refresh the back matter list."""

        self.back_matter_list.clear()

        if not self.reader:
            return

        for index, entry in enumerate(self.reader.back_matter):
            item = QListWidgetItem(entry["title"])
            item.setData(Qt.UserRole, index)

            self.back_matter_list.addItem(item)

    def back_matter_selected(self, item):
        """Open the selected back matter item."""

        index = item.data(Qt.UserRole)

        if index is None:
            return

        self.display_html(self.reader.back_matter[index]["content"])

    def refresh_chapters(self):
        """Refresh the chapter list."""
        self.chapter_list.clear()

        if not self.reader:
            return

        for index in range(self.reader.chapter_count):
            title = self.reader.chapters[index]["title"]

            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, index)

            self.chapter_list.addItem(item)

    def update_book_page_display(self):
        """Update the total pages read display."""

        if self.book_total_pages <= 0:
            self.page_count_label.setText("-- / --")
            return

        self.page_count_label.setText(
            f"{self.book_pages_read:,} / "
            f"{self.book_total_pages:,}"
        )

    def update_progress(self):
        """Update the reading progress bar."""

        if not self.reader:
            return

        if self.book_total_pages > 0:
            progress = (
                self.book_pages_read /
                self.book_total_pages
            ) * 100
        else:
            chapter_count = max(
                1,
                self.reader.chapter_count
            )

            chapter_progress = (
                self.reader.current_chapter +
                (
                    (self.current_page + 1) /
                    max(1, self.total_pages)
                )
            )

            progress = (
                chapter_progress /
                chapter_count
            ) * 100

        self.progress_bar.setValue(
            max(
                0,
                min(100, round(progress))
            )
        )

    def calculate_book_page_counts(self):
        """Calculate virtual page counts for every chapter."""

        if not self.reader:
            return
        if self.is_calculating_book_pages:
            return

        self.is_calculating_book_pages = True

        self.chapter_page_counts = []
        self.book_total_pages = 0
        self.book_pages_read = 0
        self.page_count_index = 0

        # Match the visible QWebEngineView's viewport.
        self.page_counter_view.resize(
            self.web_view.width(),
            self.web_view.height()
        )

        # Keep the measurement view rendered but off-screen.
        self.page_counter_view.move(
            -10000,
            -10000
        )

        self.page_count_label.setText(
            "Calculating..."
        )

        self._load_next_chapter_for_measurement()

    def _load_next_chapter_for_measurement(self):
        """Load the next chapter into the page counter."""

        if not self.reader:
            return

        if self.page_count_index >= self.reader.chapter_count:
            self._finish_book_page_calculation()
            return

        chapter = self.reader.chapters[
            self.page_count_index
        ]

        self.page_counter_view.setHtml(
            self.build_reader_html(
                chapter["content"]
            )
        )


    def _measure_loaded_chapter(self, success):
        """Measure a chapter after its HTML has loaded."""

        if not success or not self.reader:
            self._page_measurement_failed(
                "Chapter HTML did not load."
            )
            return

        # Give Chromium one event-loop cycle to finish layout.
        QTimer.singleShot(
            0,
            self._request_content_height
        )

    def _page_measurement_failed(self, reason):
        """Stop book pagination after a measurement failure."""
        self.page_count_label.setText("-- / --")
        self.is_calculating_book_pages = False


    def _load_library(self):
        """Populate the library grid with book tiles and progress bars."""

        self.library_grid.clear()

        covers_dir = Path("covers")
        covers_dir.mkdir(exist_ok=True)

        for book in self.library.get_books():
            book_id = book["id"]
            title = book["title"]
            cover_path = book["cover_path"]
            pages_read = book["pages_read"]
            pages_read = book["pages_read"]
            total_pages = book["total_pages"]

            if not cover_path or not Path(cover_path).exists():
                cover_path = (covers_dir / f"placeholder_{book_id}.png")

                if not cover_path.exists():
                    self.create_placeholder_cover(title, str(cover_path))

            progress = (
                book["progress_percent"]
                if "progress_percent" in book.keys()
                else 0
            )
            progress = max(0, min(100, progress or 0))

            pages_read = (
                book["pages_read"]
                if "pages_read" in book.keys()
                else 0
            )
            book_total_pages = (
                book["total_pages"]
                if "total_pages" in book.keys()
                else 0
            )

            #
            # QListWidget item
            #
            item = QListWidgetItem()
            item.setData(Qt.UserRole, book_id)
            item.setSizeHint(QSize(180, 300))
            self.library_grid.addItem(item)

            #
            # Custom book tile
            #
            tile = QWidget()
            tile.setObjectName("bookTile")

            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(
                8,
                8,
                8,
                8
            )
            tile_layout.setSpacing(5)

            #
            # Cover
            #
            cover_label = QLabel()
            cover_label.setAlignment(Qt.AlignCenter)
            cover_label.setFixedSize(150, 220)

            cover_pixmap = QPixmap(str(cover_path))

            if not cover_pixmap.isNull():
                cover_label.setPixmap(
                    cover_pixmap.scaled(
                        150,
                        220,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )

            #
            # Title
            #
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setWordWrap(True)
            title_label.setMaximumHeight(38)
            title_label.setToolTip(title)

            #
            # Progress bar
            #
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(progress)
            progress_bar.setFormat(f"{progress}%")
            progress_bar.setTextVisible(True)
            progress_bar.setFixedHeight(14)

            # progress_bar.setToolTip(
            #     f"{pages_read:,} / {total_pages:,} pages read"
            #     f"{progress}% of book completed"
            # )
            if book_total_pages > 0:
                progress_bar.setToolTip(
                    f"{pages_read:,} / "
                    f"{book_total_pages:,} pages read"
                )
            else:
                progress_bar.setToolTip(f"{progress}% complete")

            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #fad3d1;
                    border-radius: 6px;
                    background-color: #fce2e1;
                    color: #3f1219;
                    font-size: 9px;
                    text-align: center;
                }

                QProgressBar::chunk {
                    background-color: #d98791;
                    border-radius: 5px;
                }
            """)

            tile_layout.addWidget(cover_label, alignment=Qt.AlignCenter)
            tile_layout.addWidget(title_label)
            tile_layout.addWidget(progress_bar)

            self.library_grid.setItemWidget(item, tile)

    def open_book(self):
        """Open a file picker and load the selected EPUB."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open EPUB",
            "",
            "EPUB Files (*.epub)"
        )

        if not filename:
            return

        self.load_book(filename)

    def delete_book_from_library(self, item):
        """Remove a book and its associated data from the library."""

        book_id = item.data(Qt.UserRole)
        book = self.library.get_book(book_id)

        if not book:
            QMessageBox.warning(
                self,
                "Book Not Found",
                "The selected book could not be found in the library."
            )
            return

        title = book["title"]

        reply = QMessageBox.question(
            self,
            "Delete Book",
            (
                f'Remove "{title}" from your library?\n\n'
                "This will delete its saved reading progress, "
                "bookmarks, and library cover image.\n\n"
                "The original EPUB file will not be deleted."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            cover_path = (
                book["cover_path"]
                if "cover_path" in book.keys()
                else None
            )

            self.bookmarks.delete_bookmarks_for_book(book_id)

            # Delete the book record.
            self.library.delete_book(book_id)

            # Delete only cover files managed by this application.
            self.delete_managed_cover(cover_path)

            # Clear the current reader state if this was the open book.
            if self.current_book_id == book_id:
                self.reader = None
                self.current_book_id = None

                self.current_page = 0
                self.total_pages = 1

                self.go_to_last_page = False
                self.resize_progress = None

                self.chapter_list.clear()
                self.front_matter_list.clear()
                self.back_matter_list.clear()
                self.bookmark_list.clear()

                self.status_label.setText("Ready")
                self.progress_bar.setValue(0)

                self.web_view.setHtml(
                    """
                    <html>
                    <body style="background-color:#fef2f1;">
                    </body>
                    </html>
                    """
                )

                self.show_home()
                

            # Prevent the deleted book from reopening next session.
            settings = self.settings.load()

            if settings.get("last_book_id") == book_id:
                settings.pop("last_book_id", None)
                self.settings.save(settings)

            self._load_library()

            QMessageBox.information(
                self,
                "Book Removed",
                f'"{title}" was removed from your library.'
            )

        except Exception as ex:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Delete Book Error",
                f'Could not remove "{title}" from the library.\n\n{ex}'
            )

    def delete_managed_cover(self, cover_path):
        """Delete a cover only if it is inside the application covers folder."""

        if not cover_path:
            return

        cover = Path(cover_path)
        covers_dir = Path("covers").resolve()

        try:
            resolved_cover = cover.resolve()
            resolved_cover.relative_to(covers_dir)
        except (ValueError, OSError):
            # The cover is outside the application-managed covers folder.
            return

        if resolved_cover.is_file():
            resolved_cover.unlink()

    def load_book(self, path):
        """Load a book and restore its saved reading position."""
        try:
            self.chapter_dock.show()
            self.front_matter_dock.show()
            self.back_matter_dock.show()
            self.bookmark_dock.show()
            self.home_toolbar.show()
            self.reader_toolbar.show()
            self.stack.setCurrentWidget(self.reader_page)

            self.reader = EpubReader(path)

            title = self.reader.title
            cover_path = self.reader.extract_cover("covers")
            book_id = self.library.add_book(path, title, cover_path)
            self.current_book_id = book_id

            book = self.library.get_book(book_id)

            self.save_last_book()
            self.refresh_bookmarks()

            # Restore the last chapter/page read.
            chapter = book["last_chapter"]
            page = book["last_page"]
            if chapter >= self.reader.chapter_count:
                chapter = 0

            self.reader.current_chapter = chapter
            self.current_page = page
            self.refresh_front_matter()
            self.refresh_back_matter()
            self.refresh_chapters()

            self.display_current_chapter()
            QTimer.singleShot(500, self.calculate_book_page_counts)
            self.status_label.setText(title)

            self._load_library()

        except Exception as ex:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", str(ex))

    def load_last_book(self):
        """Reopen the last book from the previous session."""
        settings = self.settings.load()
        book_id = settings.get("last_book_id")

        if not book_id:
            return

        book = self.library.get_book(book_id)

        if not book:
            return

        self.load_book(book["path"])

    def save_last_book(self):
        """Persist the currently opened book."""
        settings = self.settings.load()
        settings["last_book_id"] = self.current_book_id

        self.settings.save(settings)

    def calculate_pages(self):
        """Calculate the number of virtual pages in the current chapter."""
        if not self.reader:
            return

        self.web_view.page().runJavaScript(
            """
            Math.max(
                document.body ? document.body.scrollHeight : 0,
                document.documentElement
                    ? document.documentElement.scrollHeight
                    : 0
            )
            """,
            self.on_page_height
        )

    def _finish_book_page_calculation(self):
        """Finish calculating global book pagination."""

        if not self.reader:
            return

        if (
            len(self.chapter_page_counts) !=
            self.reader.chapter_count
        ):
            self.page_count_label.setText(
                "-- / --"
            )
            return

        self.book_total_pages = sum(
            self.chapter_page_counts
        )

        self.update_book_pages_read()
        self.update_book_page_display()
        self.update_progress()
        self.save_position()
        self.is_calculating_book_pages = False

    def get_page_height(self):
        """Return the usable page height."""
        return max(100, self.web_view.height())

    def on_page_height(self, height):
        """Compute total pages from the rendered chapter height."""
        if not self.reader or not height:
            return

        page_height = self.get_page_height()

        # Determine how many pages exist.
        self.total_pages = max(
            1,
            math.ceil(height / page_height)
        )

        # Jump to the end of a chapter when navigating backwards.
        if self.go_to_last_page:
            self.current_page = self.total_pages - 1
            self.go_to_last_page = False

        # Resizing window.
        if self.resize_progress is not None:
            self.current_page = int(
                self.resize_progress *
                max(0, self.total_pages - 1)
            )

            self.resize_progress = None

        self.current_page = min(
            self.current_page,
            self.total_pages - 1
        )

        self.show_current_page()

    def _request_content_height(self):
        """Request the rendered height of the current chapter."""

        if not self.reader:
            return

        self.page_counter_view.page().runJavaScript(
            """
            Math.max(
                document.body
                    ? document.body.scrollHeight
                    : 0,
                document.documentElement
                    ? document.documentElement.scrollHeight
                    : 0
            )
            """,
            self._receive_content_height
        )

    def _receive_content_height(self, height):
        """Receive the rendered chapter height."""

        if not self.reader:
            return

        if not isinstance(height, (int, float)) or height <= 0:
            self._page_measurement_failed(
                f"Invalid content height: {height!r}"
            )
            return

        self.measured_content_height = float(
            height
        )

        self.page_counter_view.page().runJavaScript(
            "window.innerHeight",
            self._receive_viewport_height
        )

    def _receive_viewport_height(self, viewport_height):
        """Calculate pages using the Chromium viewport height."""

        if not self.reader:
            return

        if (
            not isinstance(viewport_height, (int, float)) or
            viewport_height <= 0
        ):
            self._page_measurement_failed(
                f"Invalid viewport height: {viewport_height!r}"
            )
            return

        measured_index = self.page_count_index

        chapter_pages = max(
            1,
            math.ceil(
                self.measured_content_height /
                float(viewport_height)
            )
        )

        self.chapter_page_counts.append(
            chapter_pages
        )

        self.page_count_index += 1

        QTimer.singleShot(
            0,
            self._load_next_chapter_for_measurement
        )

    def replace_book_cover(self, item):
        """Replace a book cover with a user-supplied PNG."""

        book_id = item.data(Qt.UserRole)

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Cover Image",
            "",
            "PNG Images (*.png, *jpg, *.jpeg, *.webp)"
        )

        if not filename:
            return

        covers_dir = Path("covers")
        covers_dir.mkdir(exist_ok=True)

        new_cover = covers_dir / f"user_{book_id}.png"

        shutil.copy2(filename, new_cover)

        self.library.update_cover_path(book_id, str(new_cover))

        self._load_library()

    def show_current_page(self):
        """Display the current page within the chapter."""

        if not self.reader:
            return

        page_height = self.get_page_height()

        js = f"""
        window.scrollTo(
            0,
            {self.current_page * page_height + 20}
        );
        """

        self.web_view.page().runJavaScript(
            js
        )

        self.update_book_pages_read()
        self.update_progress()
        self.update_book_page_display()

        self.status_label.setText(
            f"{self.reader.title} | "
            f"{self.reader.current_chapter_title} | "
            f"Chapter page "
            f"{self.current_page + 1}/"
            f"{self.total_pages}"
        )

        self.save_position()

        

    def display_current_chapter(self):
        """Render the current chapter in the reading view."""
        if not self.reader:
            return

        self.display_html(self.reader.get_current_chapter())

        self.save_position()

        if self.reader.current_chapter < self.chapter_list.count():
            self.chapter_list.setCurrentRow(self.reader.current_chapter)

    def chapter_selected(self, item):
        """Jump to the selected chapter."""
        chapter_index = item.data(Qt.UserRole)

        if chapter_index is None:
            return

        self.reader.current_chapter = chapter_index
        self.current_page = 0

        self.display_current_chapter()
        self.save_position()
    
    def next_page(self):
        """Advance to the next page or chapter."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.show_current_page()
            self.save_position()

        # Move to the next chapter after the final page.
        elif self.reader.next_chapter():
            self.current_page = 0
            self.display_current_chapter()

    def previous_page(self):
        """Go back to the previous page or chapter."""
        if self.current_page > 0:
            self.current_page -= 1
            self.show_current_page()
            self.save_position()

        # Move to the end of the previous chapter.
        elif self.reader.previous_chapter():
            self.go_to_last_page = True
            self.display_current_chapter()

    def update_book_pages_read(self):
        """Update the current global page position."""

        if (
            not self.reader or
            not self.chapter_page_counts
        ):
            return

        chapter_index = (
            self.reader.current_chapter
        )

        if (
            chapter_index < 0 or
            chapter_index >=
            len(self.chapter_page_counts)
        ):
            return

        pages_before_chapter = sum(
            self.chapter_page_counts[
                :chapter_index
            ]
        )

        current_chapter_page = min(
            self.current_page + 1,
            self.chapter_page_counts[
                chapter_index
            ]
        )

        self.book_pages_read = (
            pages_before_chapter +
            current_chapter_page
        )

    def next_chapter(self):
        """Advance directly to the next chapter."""
        if not self.reader:
            return

        if self.reader.next_chapter():
            self.current_page = 0
            self.display_current_chapter()
            self.save_position()

    def previous_chapter(self):
        """Return directly to the previous chapter."""
        if not self.reader:
            return

        if self.reader.previous_chapter():
            self.current_page = 0
            self.display_current_chapter()
            self.save_position()

    def save_position(self):
        """Save the current reading position and progress."""
        if not self.reader or not self.current_book_id:
            return
        
        if self.book_total_pages > 0:
            progress_percent = round(
                self.book_pages_read /
                self.book_total_pages
                * 100
            )
        else:
            chapter_count = max(1, self.reader.chapter_count)
            chapter_progress = (self.reader.current_chapter +
                (
                    (self.current_page + 1) /
                    max(1, self.total_pages)
                )
            )
            progress_percent = round(chapter_progress / chapter_count * 100)

        chapter_count = max(1, self.reader.chapter_count)
        total_pages = max(1, self.total_pages)

        # Include the current page in the chapter progress so that
        # the final page of the final chapter reaches 100%.
        # page_progress = min(1.0, (self.current_page + 1) / total_pages)
        # overall_progress = (
        #     (self.reader.current_chapter + page_progress)
        #     / chapter_count
        # ) * 100

        progress_percent = max(0, min(100, progress_percent))

        # pages_read = round(total_pages * progress_percent / 100)

        self.library.save_position(
            self.current_book_id,
            self.reader.current_chapter,
            self.current_page,
            progress_percent,
            self.book_pages_read,
            self.book_total_pages
        )

    def show_bookmark_context_menu(self, position):
        """Show bookmark context menu."""

        item = self.bookmark_list.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        delete_action = menu.addAction("Delete Bookmark")
        action = menu.exec(self.bookmark_list.mapToGlobal(position))

        if action == delete_action:
            bookmark_id = item.data(Qt.UserRole)
            self.bookmarks.delete_bookmark(bookmark_id)

            self.refresh_bookmarks()

    def add_bookmark(self):
        """Create a bookmark for the current chapter."""
        if not self.reader or not self.current_book_id:
            return

        self.bookmarks.add_bookmark(
            self.current_book_id,
            self.reader.current_chapter,
            self.current_page,
            "Bookmark"
        )

        self.refresh_bookmarks()

        QMessageBox.information(
            self,
            "Bookmark",
            "Bookmark saved."
        )

    def delete_selected_bookmark(self):
        """Delete the selected bookmark."""

        item = self.bookmark_list.currentItem()

        if not item:
            return

        bookmark_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Delete Bookmark",
            "Delete selected bookmark?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.bookmarks.delete_bookmark(bookmark_id)

        self.refresh_bookmarks()

    def bookmark_selected(self, item):
        """Jump to the selected bookmark."""
        row = self.bookmark_list.row(item)

        bookmarks = self.bookmarks.get_bookmarks(self.current_book_id)

        if row >= len(bookmarks):
            return

        bookmark = bookmarks[row]

        self.reader.current_chapter = bookmark["chapter"]
        self.current_page = bookmark["page"]

        self.display_current_chapter()

    def refresh_bookmarks(self):
        """Refresh the bookmarks sidebar."""
        self.bookmark_list.clear()

        if not self.current_book_id:
            return

        bookmarks = self.bookmarks.get_bookmarks(
            self.current_book_id
        )

        for bookmark in bookmarks:
            item = QListWidgetItem(
                f"Chapter {bookmark['chapter'] + 1}, "
                f"Page {bookmark['page'] + 1}"
            )

            item.setData(Qt.UserRole, bookmark["id"])

            # Hover to see timestamp created
            item.setToolTip(f"Created: {bookmark['created_at']}")

            self.bookmark_list.addItem(item)

    def show_bookmarks(self):
        """Open the bookmark selection dialog."""
        if not self.current_book_id:
            return

        dialog = BookmarkDialog(
            self.bookmarks.get_bookmarks(self.current_book_id),
            self
        )

        if dialog.exec():
            bookmark = dialog.selected_bookmark

            if bookmark:
                self.reader.current_chapter = bookmark["chapter"]
                self.current_page = bookmark["page"]
                self.display_current_chapter()


    def save_settings(self):
        """Persist reader settings."""
        settings = self.settings.load()
        settings["font_size"] = self.font_size
        self.settings.save(settings)

    def increase_font_size(self):
        """Increase the reading font size."""
        if self.font_size < 48:
            self.font_size += 2
            self.save_settings()

            if self.reader:
                self.display_current_chapter()
                QTimer.singleShot(0, self.calculate_book_page_counts)

    def decrease_font_size(self):
        """Decrease the reading font size."""
        if self.font_size > 10:
            self.font_size -= 2
            self.save_settings()

            if self.reader:
                self.display_current_chapter()
                QTimer.singleShot(0, self.calculate_book_page_counts)

    def library_book_selected(self, item):
        """Open a book selected from the library."""
        book_id = item.data(Qt.UserRole)

        book = self.library.get_book(book_id)

        if book:
            self.load_book(book["path"])

    def closeEvent(self, event):
        """Save state before closing the application."""
        self.save_position()
        event.accept()
