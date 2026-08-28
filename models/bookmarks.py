import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/app.db")


class BookmarkModel:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks(
            id INTEGER PRIMARY KEY,
            book_id INTEGER,
            chapter INTEGER,
            page INTEGER DEFAULT 0,
            name TEXT,
            note TEXT,
            created_at TEXT
        )
        """)

        try:
            self.conn.execute(
                """
                ALTER TABLE bookmarks
                ADD COLUMN name TEXT
                """
            )
        except sqlite3.OperationalError:
            pass

        self.conn.commit()

    def add_bookmark(
        self,
        book_id,
        chapter,
        page,
        name,
        note=""
    ):
        created_at = datetime.now().strftime("%b %d, %Y %I:%M %p")
        self.conn.execute(
            """
            INSERT INTO bookmarks(
                book_id,
                chapter,
                page,
                name,
                note,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                book_id,
                chapter,
                page,
                name,
                note,
                created_at
            ),
        )

        self.conn.commit()

    def delete_bookmark(self, bookmark_id):
        """Delete a bookmark."""

        self.conn.execute(
            """
            DELETE FROM bookmarks
            WHERE id=?
            """,
            (bookmark_id,)
        )

        self.conn.commit()

    def delete_bookmarks_for_book(self, book_id):
        """Delete all bookmarks associated with a book."""

        self.conn.execute(
            """
            DELETE FROM bookmarks
            WHERE book_id = ?
            """,
            (book_id,)
        )

        self.conn.commit()

    def get_bookmarks(self, book_id):
        return self.conn.execute(
            """
            SELECT *
            FROM bookmarks
            WHERE book_id = ?
            ORDER BY chapter, page
            """,
            (book_id,)
        ).fetchall()