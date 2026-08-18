import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QAction, QShortcut, QKeySequence

from models.library import LibraryModel
from models.bookmarks import BookmarkModel
from models.settings import Settings
from readers.epub_reader import EpubReader
from ui.bookmark_dialog import BookmarkDialog


class MainWindow(QMainWindow):
    def __init__(self):
        """Initialize the main window and application state."""
        super().__init__()

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

        # timer for resizing window size
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize_finished)

        self._create_ui()
        self._load_library()
        self.load_last_book()

    def _create_ui(self):
        """Create and configure all UI elements."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Top bar buttons.
        open_btn = QPushButton("Open")
        next_chapter_btn = QPushButton("Next Chapter")
        prev_chapter_btn = QPushButton("Previous Chapter")
        next_page_btn = QPushButton("Next Page")
        prev_page_btn = QPushButton("Previous Page")
        view_bookmarks_btn = QPushButton("Bookmarks")
        bookmark_btn = QPushButton("Add Bookmark")

        # Font dropdown
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


        toolbar.addWidget(open_btn)
        toolbar.addWidget(next_chapter_btn)
        toolbar.addWidget(prev_chapter_btn)
        toolbar.addWidget(next_page_btn)
        toolbar.addWidget(prev_page_btn)
        toolbar.addWidget(view_bookmarks_btn)
        toolbar.addWidget(bookmark_btn)
        toolbar.addWidget(font_btn)

        open_btn.clicked.connect(self.open_book)
        next_chapter_btn.clicked.connect(self.next_chapter)
        prev_chapter_btn.clicked.connect(self.previous_chapter)
        next_page_btn.clicked.connect(self.next_page)
        prev_page_btn.clicked.connect(self.previous_page)
        view_bookmarks_btn.clicked.connect(self.show_bookmarks)
        bookmark_btn.clicked.connect(self.add_bookmark)


        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self.library_book_selected)
        self.bookmark_list = QListWidget()

        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.calculate_pages)

        # Dockable side panels.
        self.library_dock = QDockWidget("Library")
        self.library_dock.setWidget(self.library_list)
        self.addDockWidget(Qt.LeftDockWidgetArea,self.library_dock)

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

        self.bookmark_dock = QDockWidget("Bookmarks")
        self.bookmark_dock.setMinimumWidth(150)
        self.bookmark_dock.setMaximumWidth(250)
        self.bookmark_dock.setWidget(self.bookmark_list)
        self.addDockWidget(
            Qt.RightDockWidgetArea,
            self.bookmark_dock
        )
        self.resizeDocks(
            [self.library_dock, self.bookmark_dock],
            [250, 180],
            Qt.Horizontal
        )
        self.bookmark_list.itemDoubleClicked.connect(self.bookmark_selected)
        self.bookmark_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmark_list.customContextMenuRequested.connect(self.show_bookmark_context_menu)

        # Keyboard shortcuts for page navigation.
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

        splitter = QSplitter()
        splitter.addWidget(self.web_view)
        splitter.setSizes([200, 800, 200])

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(splitter, 1)

        # Progress bar in footer.
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)

        self.status_label = QLabel("Ready")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdb8aa;
                border-radius: 4px;
                background: #f4f1e8;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #6b8e23;
                border-radius: 3px;
            }
            """)

        footer_layout.addWidget(self.status_label)
        footer_layout.addWidget(self.progress_bar)

        layout.addWidget(footer)

        self.setCentralWidget(container)

    def display_html(self, content):
        """Display raw HTML content."""

        html = f"""
        <html>
        <head>
        <style>

        html {{
            overflow-x: hidden;
            overflow-y: hidden;
            background-color: #d9d4c7;
        }}

        body {{
            width: min(90%, 700px);

            margin: 60px auto;
            padding: 50px 40px;

            background: white;
            box-sizing: border-box;
            box-shadow: 0 0 12px rgba(0, 0, 0, 0.15);
            border-radius: 4px;

            font-family: Georgia, serif;
            font-size: {self.font_size}px;
            line-height: 1.6;

            overflow: hidden;
        }}

        img {{
            max-width: 100%;
        }}

        </style>
        </head>

        <body>
        {content}
        </body>

        </html>
        """

        self.web_view.setHtml(html)

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

    def refresh_front_matter(self):
        """Refresh the front matter list."""

        self.front_matter_list.clear()

        if not self.reader:
            return

        for index, entry in enumerate(
            self.reader.front_matter
        ):
            item = QListWidgetItem(
                entry["title"]
            )

            item.setData(
                Qt.UserRole,
                index
            )

            self.front_matter_list.addItem(item)

    def front_matter_selected(self, item):
        """Open the selected front matter item."""
        index = item.data(Qt.UserRole)

        if index is None:
            return

        self.display_html(
            self.reader.front_matter[index]["content"]
        )

    def refresh_chapters(self):
        """Refresh the chapter list."""
        self.chapter_list.clear()

        if not self.reader:
            return

        for index in range(self.reader.chapter_count):
            title = self.reader.chapters[index]["title"]

            item = QListWidgetItem(title)
            item.setData(
                Qt.UserRole,
                index
            )

            self.chapter_list.addItem(item)

    def update_progress(self):
        """Update the reading progress bar."""

        if not self.reader:
            return

        chapter_progress = (
            self.reader.current_chapter +
            (self.current_page / max(1, self.total_pages))
        )

        progress = (
            chapter_progress /
            self.reader.chapter_count
        ) * 100

        self.progress_bar.setValue(int(progress))

    def _load_library(self):
        """Populate the library pane with known books."""
        self.library_list.clear()

        for book in self.library.get_books():
            item = QListWidgetItem(book["title"])

            # Store the database ID with the list item.
            item.setData(Qt.UserRole,book["id"])
            self.library_list.addItem(item)

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

    def load_book(self, path):
        """Load a book and restore its saved reading position."""
        try:
            self.reader = EpubReader(path)

            title = self.reader.title

            book_id = self.library.add_book(path, title)
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
            self.refresh_chapters()
            self.display_current_chapter()

            self.status_label.setText(title)

            self._load_library()

        except Exception as ex:
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

    def get_page_height(self):
        """Return the usable page height."""

        return max(
            100,
            self.web_view.height()
        )

    def on_page_height(self, height):
        """Compute total pages from the rendered chapter height."""
        if not height:
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


    def show_current_page(self):
        """Display the current page within the chapter."""
        page_height = self.get_page_height()

        # Scroll to the appropriate page offset.
        js = f"""
        window.scrollTo(
            0,
            {self.current_page * page_height + 20}
        );
        """

        self.web_view.page().runJavaScript(js)

        self.update_progress()

        self.status_label.setText(
            f"{self.reader.title} | " # Book title
            f"{self.progress_bar.value()}% | " # progress bar %
            f"{self.reader.current_chapter_title} | " # Chapter title
            f"Page {self.current_page + 1}/{self.total_pages} | " # Page number
        )
        

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
        """Save the current reading position."""
        if not self.reader or not self.current_book_id:
            return

        self.library.save_position(
            self.current_book_id,
            self.reader.current_chapter,
            self.current_page
        )

    def show_bookmark_context_menu(self, position):
        """Show bookmark context menu."""

        item = self.bookmark_list.itemAt(position)

        if item is None:
            return

        menu = QMenu(self)

        delete_action = menu.addAction(
            "Delete Bookmark"
        )

        action = menu.exec(
            self.bookmark_list.mapToGlobal(position)
        )

        if action == delete_action:
            bookmark_id = item.data(Qt.UserRole)

            self.bookmarks.delete_bookmark(
                bookmark_id
            )

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

        bookmarks = self.bookmarks.get_bookmarks(
            self.current_book_id
        )

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

            item.setData(
                Qt.UserRole,
                bookmark["id"]
            )

            # Hover to see timestamp created
            item.setToolTip(
                f"Created: {bookmark['created_at']}"
            )

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

    def decrease_font_size(self):
        """Decrease the reading font size."""
        if self.font_size > 10:
            self.font_size -= 2
            self.save_settings()

            if self.reader:
                self.display_current_chapter()

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
