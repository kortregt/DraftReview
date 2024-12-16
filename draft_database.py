import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict
import datetime

@dataclass
class Draft:
    title: str
    url: str
    created_at: datetime.datetime

class DraftDatabase:
    def __init__(self, db_path: str = "drafts.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    title TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_draft(self, title: str, url: str) -> None:
        """Add a new draft to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO drafts (title, url, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (title, url)
            )
            conn.commit()

    def remove_draft(self, title: str) -> None:
        """Remove a draft from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drafts WHERE title = ?", (title,))
            conn.commit()

    def get_all_drafts(self) -> Dict[str, str]:
        """Get all drafts as a dictionary of title -> url."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title, url FROM drafts")
            return dict(cursor.fetchall())

    def get_draft(self, title: str) -> Optional[Draft]:
        """Get a specific draft by title."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, url, created_at FROM drafts WHERE title = ?",
                (title,)
            )
            row = cursor.fetchone()
            if row:
                return Draft(
                    title=row['title'],
                    url=row['url'],
                    created_at=datetime.datetime.fromisoformat(row['created_at'])
                )
            return None