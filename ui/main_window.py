import traceback

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListView,
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import (
    QWebEngineView
)
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QShortcut,
)

from models.library import LibraryModel
from models.bookmarks import BookmarkModel
from models.settings import Settings
from readers.epub_reader import EpubReader

from ui.navigation import Navigation
from ui.pagination import Pagination
from ui.bookmarks import Bookmark
from ui.library import Library
from ui.settings import SettingsUI
from ui.reader_html import build_reader_html

class MainWindow(
    Library,
    Bookmark,
    Pagination,
    Navigation,
    SettingsUI,
    QMainWindow
):
    def __init__(self):
        """Initialize the main window and application state."""
        super().__init__()

        self.chapter_page_counts = []
        self.book_total_pages = 0
        self.book_pages_read = 0

        self.page_count_index = 0
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


    def closeEvent(self, event):
        """Save state before closing the application."""
        self.save_position()
        event.accept()
