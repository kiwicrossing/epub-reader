import sqlite3
from pathlib import Path

DB_PATH = Path("data/app.db")


class LibraryModel:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)

        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            title TEXT,
            cover_path TEXT,
            last_chapter INTEGER DEFAULT 0,
            last_page INTEGER DEFAULT 0,
            progress_percent INTEGER DEFAULT 0,
            pages_read INTEGER DEFAULT 0,
            total_pages INTEGER DEFAULT 0
        )
        """)

        try:
            self.conn.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            self.conn.execute("ALTER TABLE books ADD COLUMN last_page INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            self.conn.execute("""ALTER TABLE books ADD COLUMN progress_percent INTEGER DEFAULT 0""")
        except sqlite3.OperationalError:
            pass

        try:
            self.conn.execute("""ALTER TABLE books ADD COLUMN pages_read INTEGER DEFAULT 0""")
        except sqlite3.OperationalError:
            pass

        try:
            self.conn.execute("""ALTER TABLE books  ADD COLUMN total_pages INTEGER DEFAULT 0""")
        except sqlite3.OperationalError:
                pass

        self.conn.commit()

    def add_book(
        self,
        path,
        title,
        cover_path=None
    ):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO books(
                path,
                title,
                cover_path
            )
            VALUES (?, ?, ?)
            """,
            (
                path,
                title,
                cover_path
            ),
        )

        self.conn.execute(
            """
            UPDATE books
            SET
                title=?,
                cover_path=?
            WHERE path=?
            """,
            (
                title,
                cover_path,
                path
            ),
        )

        self.conn.commit()

        row = self.conn.execute(
            """
            SELECT id
            FROM books
            WHERE path=?
            """,
            (path,),
        ).fetchone()

        return row["id"]

    def delete_book(self, book_id):
        """Delete a book from the library database."""

        self.conn.execute(
            """
            DELETE FROM books
            WHERE id = ?
            """,
            (book_id,)
        )

        self.conn.commit()

    def get_books(self):
        return self.conn.execute(
            "SELECT * FROM books ORDER BY title"
        ).fetchall()

    def get_book(self, book_id):
        return self.conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,),
        ).fetchone()

    def save_position(
        self,
        book_id,
        chapter,
        page,
        progress_percent,
        pages_read,
        total_pages
    ):
        """Save reading position and overall progress."""

        self.conn.execute(
            """
            UPDATE books
            SET
                last_chapter=?,
                last_page=?,
                progress_percent=?,
                pages_read=?,
                total_pages=?
            WHERE id=?
            """,
            (
                chapter,
                page,
                progress_percent,
                pages_read,
                total_pages,
                book_id
            ),
        )

        self.conn.commit()

    def update_cover_path(
        self,
        book_id,
        cover_path
    ):
        """Update the cover image path for a book."""

        self.conn.execute(
            """
            UPDATE books
            SET cover_path=?
            WHERE id=?
            """,
            (
                cover_path,
                book_id
            ),
        )

        self.conn.commit()