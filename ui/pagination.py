import math

from PySide6.QtCore import QTimer

from ui.reader_html import build_reader_html

class Pagination:
    # How many pages exist?
    # Where am I globally?
    # What percentage complete is the book?

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

    def get_page_height(self):
        """Return the usable page height."""
        return max(100, self.web_view.height())

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
            build_reader_html(
                chapter["content"],
                self.font_size
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
        QTimer.singleShot(0, self._request_content_height)

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

        self.measured_content_height = float(height)

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

        self.chapter_page_counts.append(chapter_pages)
        self.page_count_index += 1

        QTimer.singleShot(0, self._load_next_chapter_for_measurement)

    def _finish_book_page_calculation(self):
        """Finish calculating global book pagination."""
        if not self.reader:
            return

        if (
            len(self.chapter_page_counts) !=
            self.reader.chapter_count
        ):
            self.page_count_label.setText("-- / --")
            return

        self.book_total_pages = sum(self.chapter_page_counts)

        self.update_book_pages_read()
        self.update_book_page_display()
        self.update_progress()
        self.save_position()
        self.is_calculating_book_pages = False

    def _page_measurement_failed(self, reason):
        """Stop book pagination after a measurement failure."""
        self.page_count_label.setText("-- / --")
        self.is_calculating_book_pages = False

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
            max(0, min(100, round(progress)))
        )

    def update_book_pages_read(self):
        """Update the current global page position."""
        if (
            not self.reader or
            not self.chapter_page_counts
        ):
            return

        chapter_index = (self.reader.current_chapter)

        if (
            chapter_index < 0 or
            chapter_index >=
            len(self.chapter_page_counts)
        ):
            return

        pages_before_chapter = sum(
            self.chapter_page_counts[:chapter_index]
        )

        current_chapter_page = min(
            self.current_page + 1,
            self.chapter_page_counts[chapter_index]
        )

        self.book_pages_read = (
            pages_before_chapter +
            current_chapter_page
        )

    def update_book_page_display(self):
        """Update the total pages read display."""
        if self.book_total_pages <= 0:
            self.page_count_label.setText("-- / --")
            return

        self.page_count_label.setText(
            f"{self.book_pages_read:,} / "
            f"{self.book_total_pages:,}"
        )

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