from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from bs4 import BeautifulSoup
import re 

TRAINING_DATA = [
    ("Cover", "front"),
    ("Title", "front"),
    ("Quote", "front"),
    ("Quotations", "front"),
    ("Dedication", "front"),
    ("Foreword", "front"),
    ("Preface", "front"),
    ("Introduction", "front"),
    ("Copyright", "front"),
    ("Contents", "front"),

    ("Chapter 1", "chapter"),
    ("Chapter 2", "chapter"),
    ("1", "chapter"),
    ("2", "chapter"),
    ("Act 1", "chapter"),
    ("Act I", "chapter"),
    ("Act One", "chapter"),
    ("Act 2", "chapter"),
    ("Act II", "chapter"),
    ("Chapter Three", "chapter"),
    ("The Journey Begins", "chapter"),
    ("Winter", "chapter"),
    ("The Last Stand", "chapter"),
    ("1939-1958", "chapter"),
    ("1972-1974", "chapter"),
    ("1964", "chapter"),
    ("1968", "chapter"),
    ("A year and a half later", "chapter"),

    ("Appendix", "back"),
    ("Index", "back"),
    ("Credits", "back"),
    ("Acknowledgements", "back"),
    ("Acknowledgments", "back"),
    ("Bibliography", "back"),
    ("References", "back"),
    ("About the Author", "back"),
    ("What's next on your reading list?", "back"),
    ("Author's Note", "back"),
    ("About the Publisher", "back"),
    ("Permissions", "back"),
    ("Reading group guide", "back"),
    ("Discussion Questions", "back"),
    ("Ba1", "back"),
]

class SectionClassifier:
    JUNK_PATTERNS = [
        r"epub",
        r"cvi",
        r"r\d+$",
        r"pg[_-]?\d+",
        r"oebps",
        r"calibre",
        r"tp",
        r"cop",
        r"epi",
        r"r1",
    ]
    def __init__(self):
        titles = [row[0] for row in TRAINING_DATA]
        labels = [row[1] for row in TRAINING_DATA]

        self.model = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                ),
            ),
            ("clf", LogisticRegression(),),
        ])

        self.model.fit(titles, labels,)

    def is_junk_title(self, title: str) -> bool:
        if not title:
            return True
        title = title.strip()
        lower = title.lower()

        for pattern in self.JUNK_PATTERNS:
            if re.search(pattern, lower):
                return True

        return False

    def is_junk_section(self, title: str, text: str) -> bool:
        if self.is_junk_title(title):
            return True
        if not text:
            return True
        words = text.split()

        if len(words) < 5:
            return True

        return False

    def _looks_like_chapter_title(self, title):
        if not title:
            return False

        title = title.strip().lower()

        patterns = [
            r"^chapter\s+\d+",
            r"^chapter\s+[ivxlcdm]+",
            r"^\d+$",
            r"^[ivxlcdm]+$",
            r"^part\s+\d+",
            r"^part\s+[ivxlcdm]+",
            r"^prologue$",
            r"^epilogue$",
            r"^book\s+\d+",
        ]

        return any(re.match(p, title) for p in patterns)

    def is_copyright_page(self, title, text):
        if not text:
            return False

        text_lower = text.lower()

        patterns = [
            r"copyright\s*[©()]?",
            r"license",
            r"free distribution",
            r"all rights reserved",
            r"published by",
            r"published in the",
            r"library of congress",
            r"cataloging[- ]in[- ]publication",
            r"\bisbn\b",
            r"\beisbn\b",
            r"printed in",
            r"registered trademark",
            r"trademark",
            r"publisher",
            r"www\.",
            r"imprint of",
        ]

        matches = sum(
            1
            for pattern in patterns
            if re.search(pattern, text_lower)
        )

        # Strong copyright signal
        if matches >= 2:
            return True

        return False

    def is_dedication_page(
        self,
        title,
        text,
        index=None,
        total_sections=None,
    ):
        if not text:
            return False

        lines = [
            l.strip()
            for l in text.splitlines()
            if l.strip()
        ]

        words = len(text.split())

        if words > 100:
            return False

        score = 0

        title_lower = (title or "").lower()

        if "dedication" in title_lower:
            return True

        if lines:
            first_line = lines[0].lower()

            if first_line.startswith(
                (
                    "for ",
                    "to ",
                    "for my ",
                    "for our ",
                    "to my ",
                    "dedicated to ",
                )
            ):
                score += 5

        if len(lines) <= 4:
            score += 1

        if (
            index is not None
            and total_sections is not None
            and index < total_sections * 0.2
        ):
            score += 1

        return score >= 5

    def is_toc_page(self, title, text):
        if not text:
            return False

        combined = f"{title}\n{text}"
        combined_lower = combined.lower()

        score = 0

        # Explicit TOC title
        if (
            "contents" in title.lower()
            or "table of contents" in title.lower()
        ):
            return True

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        # TOCs usually contain many short entries
        short_lines = sum(
            1 for line in lines
            if len(line.split()) <= 6
        )

        long_lines = sum(
            1
            for line in lines
            if len(line.split()) > 10
        )

        if long_lines >= 3:
            return False

        if len(lines) >= 5 and short_lines / len(lines) > 0.8:
            score += 2

        # Count chapter-like entries
        chapter_entries = sum(
            1
            for line in lines
            if re.search(
                r"(chapter|part|prologue|epilogue)",
                line,
                re.I,
            )
        )

        if chapter_entries >= 5:
            score += 5

        # Common TOC entries
        toc_entries = (
            "cover",
            "title page",
            "dedication",
            "epigraph",
            "preface",
            "foreword",
            "introduction",
        )

        toc_count = sum(
            1
            for entry in toc_entries
            if entry in combined_lower
        )

        if toc_count >= 3:
            score += 4

        return score >= 5


    def is_quote(
        self,
        title,
        text,
        next_title=None,
        index=None,
        total_sections=None,
    ):
        if not text:
            return False

        text = text.strip()
        if self.is_copyright_page(title, text):
            return False
        if self.is_toc_page(title, text):
            return False
        if self.is_dedication_page(title, text, index, total_sections):
            return False
        if self.is_about_publisher_page(title, text):
            return False

        words = len(text.split())

        # Quotes are usually short
        if words > 250:
            return False

        score = 0

        # Strong signal: immediately before a chapter
        if next_title and self._looks_like_chapter_title(next_title):
            score += 5

        # Usually near beginning of book
        if (
            index is not None
            and total_sections is not None
            and index < total_sections * 0.30
        ):
            score += 2

        # Short content
        if words < 150:
            score += 2

        # Few paragraphs
        paragraphs = [
            p.strip()
            for p in re.split(r"\n\s*\n", text)
            if p.strip()
        ]

        if len(paragraphs) <= 3:
            score += 1

        # Attribution line
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if lines:
            last_line = lines[-1]

            attribution_patterns = [
                r"^[-–—]+\s*[A-Z]",
                r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}$",
            ]

            if any(
                re.match(pattern, last_line)
                for pattern in attribution_patterns
            ):
                score += 2

        # Don't classify known back matter as quotes
        title_lower = title.lower()

        excluded = (
            "about",
            "author",
            "acknowledg",
            "acknowledgement",
            "acknowledgment",
            "bibliography",
            "references",
            "copyright",
            "index",
            "notes",
            "glossary",
        )

        if any(word in title_lower for word in excluded):
            return False

        return score >= 5

    def is_acknowledgments_page(self, title, text):
        if self.is_toc_page(title, text):
            return False
        
        combined = f"{title}\n{text[:1000]}".lower()

        patterns = [
            "acknowledgments",
            "acknowledgements",
        ]

        return any(p in combined for p in patterns)

    def is_about_publisher_page(self, title, text):
        if not text:
            return False

        combined = f"{title}\n{text}".lower()

        score = 0

        # Explicit title
        if any(
            phrase in combined[:500]
            for phrase in (
                "about the publisher",
                "publisher information",
                "about the publishing house",
            )
        ):
            score += 10

        # Publisher/company terms
        publisher_terms = (
            "publishers",
            "publisher",
            "publishing",
            "harpercollins",
            "penguin",
            "random house",
            "macmillan",
            "simon & schuster",
            "hachette",
        )

        score += sum(
            1
            for term in publisher_terms
            if term in combined
        )

        # Multiple URLs are common
        urls = len(
            re.findall(
                r"www\.",
                combined,
            )
        )

        if urls >= 2:
            score += 3

        # Corporate naming patterns
        corporate_patterns = [
            r"\bltd\b",
            r"\binc\b",
            r"\bllc\b",
            r"\bpty\.?\s*ltd\b",
            r"\bcorp\b",
        ]

        matches = sum(
            1
            for pattern in corporate_patterns
            if re.search(pattern, combined)
        )

        score += matches

        # Country headings are common
        countries = (
            "australia",
            "canada",
            "india",
            "new zealand",
            "united kingdom",
            "uk",
            "usa",
            "united states",
        )

        country_count = sum(
            1
            for country in countries
            if country in combined
        )

        if country_count >= 2:
            score += 3

        return score >= 5

    def predict(self, title: str, text: str = ""):
        # Explicit junk detection
        if self.is_junk_section(title, text):
            return {
                "section": "junk",
                "title": title,
            }

        probabilities = self.model.predict_proba([title])[0]

        best_idx = probabilities.argmax()

        section = self.model.classes_[best_idx]
        confidence = probabilities[best_idx]

        print(
            f"ML: {title} -> {section} ({confidence:.2f})"
        )

        return {
            "section": section,
            "title": title,
            "confidence": float(confidence),
        }