from PySide6.QtWidgets import (
    QDialog,
    QListWidget,
    QPushButton,
    QVBoxLayout
)


class BookmarkDialog(QDialog):
    def __init__(self, bookmarks, parent=None):
        super().__init__(parent)

        self.selected_bookmark = None

        self.setWindowTitle("Bookmarks")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()

        for bookmark in bookmarks:
            self.list_widget.addItem(
                f"{bookmark['id']} | Chapter {bookmark['chapter']}"
            )

        layout.addWidget(self.list_widget)

        open_button = QPushButton("Open Bookmark")
        open_button.clicked.connect(
            self.open_selected
        )

        layout.addWidget(open_button)

        self.bookmarks = bookmarks

    def open_selected(self):
        row = self.list_widget.currentRow()

        if row < 0:
            return

        self.selected_bookmark = self.bookmarks[row]
        self.accept()
