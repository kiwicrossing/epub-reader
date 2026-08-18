
import re
from ebooklib import epub
from ebooklib import ITEM_DOCUMENT


class EpubReader:
    """Read and navigate EPUB content."""

    def __init__(self, file_path):
        """Load the EPUB and initialize reader state."""
        self.file_path = file_path

        self.book = epub.read_epub(file_path)

        self.title = self._extract_title()

        self.front_matter = []
        self.chapters = []

        self._load_chapters()

        self.current_chapter = 0

    def _extract_title(self):
        """Extract the book title from EPUB metadata."""
        metadata = self.book.get_metadata(
            "DC",
            "title"
        )

        if metadata:
            return metadata[0][0]

        return self.file_path

    def _is_chapter_title(self, title):
        """Return True if the title appears to be a chapter."""

        title = title.strip()

        return bool(
            re.match(
                r"^(chapter\s+\w+|\d+)$",
                title,
                re.IGNORECASE
            )
        )

    def _load_chapters(self):
        """Load chapter content and titles from the EPUB."""
        chapter_index = 0

        for item in self.book.get_items():
            if item.get_type() == ITEM_DOCUMENT:

                html = item.get_content().decode(
                    "utf-8",
                    errors="ignore"
                )

                # Try to find a chapter heading.
                title_match = re.search(
                    r"<h[1-3][^>]*>(.*?)</h[1-3]>",
                    html,
                    re.IGNORECASE | re.DOTALL
                )

                if title_match:
                    title = title_match.group(1)

                    # Remove any embedded HTML tags.
                    title = re.sub(
                        r"<[^>]+>",
                        "",
                        title
                    ).strip()

                else:
                    title = f"Chapter {chapter_index + 1}"

                entry = {
                    "title": title,
                    "content": html
                }
                if self._is_chapter_title(title):
                    self.chapters.append(entry)
                else:
                    self.front_matter.append(entry)

                chapter_index += 1

    @property
    def chapter_count(self):
        """Return the number of chapters."""
        return len(self.chapters)

    @property
    def current_chapter_title(self):
        """Return the title of the current chapter."""

        if not self.chapters:
            return ""

        return self.chapters[
            self.current_chapter
        ]["title"]

    def get_current_chapter(self):
        """Return HTML for the current chapter."""
        return self.chapters[self.current_chapter]["content"]

    def next_chapter(self):
        """Move to the next chapter."""

        if self.current_chapter >= (
            len(self.chapters) - 1
        ):
            return False

        self.current_chapter += 1
        return True

    def previous_chapter(self):
        """Move to the previous chapter."""

        if self.current_chapter <= 0:
            return False

        self.current_chapter -= 1
        return True