
import re
import os
from bs4 import BeautifulSoup
from ebooklib import epub
from ebooklib import ITEM_DOCUMENT

from ML.section_classifier import SectionClassifier


class EpubReader:
    """Read and navigate EPUB content."""

    def __init__(self, file_path):
        """Load the EPUB and initialize reader state."""
        self.file_path = file_path

        self.book = epub.read_epub(file_path)

        cover_item = self.book.get_item_with_id("cover")

        self.title = self._extract_title()

        self.ml_classifier = SectionClassifier()

        self.front_matter = []
        self.chapters = []
        self.back_matter = []

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

    def _filename_to_title(self, filename):
        """ex. change 002_Title_Page.xhtml -> Title Page"""
        filename = filename.split("/")[-1]

        # Remove extension
        filename = filename.rsplit(".", 1)[0]

        # Remove leading numbers
        filename = re.sub(r"^\d+[_-]*", "", filename)

        # Replace separators
        filename = filename.replace("_", " ")
        filename = filename.replace("-", " ")

        return filename.title()

    def _extract_section_title(self, html, filename):
        """
        Try progressively smarter ways to find a title.
        """

        soup = BeautifulSoup(html, "html.parser")

        # Try h1-h3 first
        for tag in ("h1", "h2", "h3"):
            heading = soup.find(tag)

            if heading:
                text = heading.get_text(strip=True)

                if text:
                    return text

        # Try common chapter/title classes
        element = soup.find(
            class_=re.compile(
                r"title|chapter|heading",
                re.IGNORECASE
            )
        )

        if element:
            text = element.get_text(strip=True)

            if text:
                return text

        # Fall back to filename
        return self._filename_to_title(filename)

    def extract_cover(self, output_dir):
        """Extract and save the EPUB cover image."""

        os.makedirs(output_dir, exist_ok=True)

        # Method 1: OPF metadata
        cover_meta = self.book.get_metadata(
            "OPF",
            "cover"
        )

        if cover_meta:
            cover_id = cover_meta[0][1].get("content")

            if cover_id:
                item = self.book.get_item_with_id(cover_id)

                if item:
                    path = os.path.join(
                        output_dir,
                        f"{self.title}.jpg"
                    )

                    with open(path, "wb") as f:
                        f.write(item.get_content())

                    return path

        # Method 2: Find image named "cover"
        for item in self.book.get_items():

            name = item.get_name().lower()

            if (
                "cover" in name
                and
                item.media_type.startswith("image/")
            ):
                path = os.path.join(
                    output_dir,
                    f"{self.title}.jpg"
                )

                with open(path, "wb") as f:
                    f.write(item.get_content())

                return path

        # Method 3: First image in the EPUB
        for item in self.book.get_items():

            if item.media_type.startswith("image/"):
                path = os.path.join(
                    output_dir,
                    f"{self.title}.jpg"
                )

                with open(path, "wb") as f:
                    f.write(item.get_content())

                return path

        return None


    def _is_chapter_title(self, title):
        """Classification of chapters."""

        CHAPTER_PATTERNS = [
            r"^chapter\s+\w+",
            r"^\d+$",
            r"^part\s+[ivxlcdm\d]+$",
            r"^book\s+\w+$",
        ]
        title = title.strip().lower()

        for pattern in CHAPTER_PATTERNS:
            if re.match(pattern, title, re.IGNORECASE):
                return True

        return False

    def chapter_confidence(title):
        """Confidence score that is chapter."""
        title = title.lower().strip()

        score = 0

        if re.match(r"^chapter\s+\w+", title):
            score += 10

        if re.match(r"^\d+$", title):
            score += 8

        if len(title.split()) <= 2:
            score -= 2

        if title in FRONT_MATTER_WORDS:
            score -= 20

        return score

    def _classify_section(
        self,
        title,
        index,
        total_sections,
        epub_type=None,
    ):
        # 1. EPUB metadata
        if epub_type == "frontmatter":
            return "front"

        # 2. Strong rules
        result = self._classify_rules(
            title,
            index,
            total_sections,
        )

        if result is not None:
            return result

        # 3. ML fallback
        prediction = self.ml_classifier.predict(title)
        return prediction


    def _classify_rules(
        self,
        title,
        index,
        total_sections,
    ):
        title_lower = title.lower().strip()

        front_words = {
            "title page",
            "copyright",
            "dedication",
            "epigraph",
            "foreword",
            "preface",
            "introduction",
            "contents",
            "acknowledgements",
            "acknowledgments",
        }

        back_words = {
            "about the author",
            "about author",
            "bibliography",
            "references",
            "appendix",
            "index",
        }

        if title_lower in front_words:
            return "front"

        if title_lower in back_words:
            return "back"

        if self._is_chapter_title(title):
            return "chapter"

        return None

    def _load_chapters(self):
        """Load chapter content and titles from the EPUB."""

        documents = [
            item
            for item in self.book.get_items()
            if item.get_type() == ITEM_DOCUMENT
        ]

        total_sections = len(documents)

        for index, item in enumerate(documents):

            html = item.get_content().decode(
                "utf-8",
                errors="ignore"
            )

            filename = item.get_name()

            filename_lower = filename.lower()

            if (
                "index_split" in filename_lower
                or "nav" in filename_lower
                or "toc" in filename_lower
            ):
                continue

            title = self._extract_section_title(
                html,
                filename
            )


            # Skip empty navigation pages
            if not title.strip():
                clean_text = re.sub(r"<[^>]+>", "", html).strip()

                if len(clean_text) < 100:
                    continue

                title = self._filename_to_title(item.get_name())

            entry = {
                "title": title,
                "content": html
            }

            section_type = self._classify_section(
                title=title,
                index=index,
                total_sections=total_sections,
                epub_type=None,  # add metadata detection later
            )

            if section_type == "front":
                self.front_matter.append(entry)
            elif section_type == "back":
                self.back_matter.append(entry)
            else:
                self.chapters.append(entry)

            # debugging
            # print(
            #     "chapters:",
            #     len(self.chapters),
            #     "front:",
            #     len(self.front_matter),
            #     "back:",
            #     len(self.back_matter),
            # )

    
    @property
    def chapter_count(self):
        """Return the number of chapters."""
        return len(self.chapters)

    @property
    def current_chapter_title(self):
        """Return the title of the current chapter."""

        if not self.chapters:
            return ""

        return self.chapters[self.current_chapter]["title"]

    def get_current_chapter(self):
        """Return HTML for the current chapter."""
        if not self.chapters:
            if self.front_matter:
                return self.front_matter[0]["content"]

            if self.back_matter:
                return self.back_matter[0]["content"]

            return "<h1>Book contains no readable sections.</h1>"

        return self.chapters[self.current_chapter]["content"]

    def next_chapter(self):
        """Move to the next chapter."""

        if self.current_chapter >= (len(self.chapters) - 1):
            return False

        self.current_chapter += 1
        return True

    def previous_chapter(self):
        """Move to the previous chapter."""

        if self.current_chapter <= 0:
            return False

        self.current_chapter -= 1
        return True