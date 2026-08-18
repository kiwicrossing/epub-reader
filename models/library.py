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
            last_chapter INTEGER DEFAULT 0,
            last_page INTEGER DEFAULT 0
        )
        """)

        try:
            self.conn.execute(
                "ALTER TABLE books ADD COLUMN last_page INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass

        self.conn.commit()

    def add_book(self, path, title):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO books(
                path,
                title
            )
            VALUES (?, ?)
            """,
            (path, title),
        )

        self.conn.commit()

        row = self.conn.execute(
            "SELECT id FROM books WHERE path=?",
            (path,),
        ).fetchone()

        return row["id"]

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
        page
    ):
        self.conn.execute(
            """
            UPDATE books
            SET
                last_chapter=?,
                last_page=?
            WHERE id=?
            """,
            (
                chapter,
                page,
                book_id
            ),
        )

        self.conn.commit()
