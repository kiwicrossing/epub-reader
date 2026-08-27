from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QListWidgetItem,
    QMessageBox,
    QMenu,
)

from ui.reader_html import build_reader_html

class Navigation:
    # What chapter/page is displayed?
    # How does the user move around?

    def display_html(self, content):
        """Display raw HTML content."""
        self.web_view.setHtml(build_reader_html(content, self.font_size))

    def display_current_chapter(self):
        """Render the current chapter in the reading view."""
        if not self.reader:
            return

        self.display_html(self.reader.get_current_chapter())
        self.save_position()

        if self.reader.current_chapter < self.chapter_list.count():
            self.chapter_list.setCurrentRow(self.reader.current_chapter)

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

        self.web_view.page().runJavaScript(js)

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
        progress_percent = max(0, min(100, progress_percent))

        self.library.save_position(
            self.current_book_id,
            self.reader.current_chapter,
            self.current_page,
            progress_percent,
            self.book_pages_read,
            self.book_total_pages
        )

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