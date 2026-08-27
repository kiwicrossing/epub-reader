import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import (
    QPixmap,
    QColor,
    QPainter,
    QFont,
)

class Library:
    # Library screen
    # Book management
    # Cover management

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


    def library_book_selected(self, item):
        """Open a book selected from the library."""
        book_id = item.data(Qt.UserRole)

        book = self.library.get_book(book_id)

        if book:
            self.load_book(book["path"])

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
        