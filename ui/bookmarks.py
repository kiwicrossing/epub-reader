from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QListWidgetItem,
    QMessageBox,
    QMenu,
)

class Bookmark:
    # Bookmark CRUD
    # Bookmark display / navigation

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