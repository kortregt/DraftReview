import sqlite3
from dataclasses import dataclass
from typing import Optional, Dict, Any
import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class Draft:
    title: str
    url: str
    created_at: datetime.datetime

@dataclass
class User:
    username: str
    user_id: str
    last_updated: datetime.datetime

class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass

class DraftDatabase:
    def __init__(self, db_path: str = "drafts.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with timeout."""
        try:
            return sqlite3.connect(self.db_path, timeout=20)
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Database connection failed: {e}")

    def _init_db(self) -> None:
        """Initialize the database with required tables."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create drafts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drafts (
                    title TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
        finally:
            if conn:
                conn.close()

    def add_draft(self, title: str, url: str) -> None:
        """Add a new draft to the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO drafts (title, url, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (title, url)
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to add draft {title}: {e}")
            raise DatabaseError(f"Failed to add draft: {e}")
        finally:
            if conn:
                conn.close()

    def add_user(self, username: str, user_id: str) -> None:
        """Add or update a user in the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO users (username, user_id, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (username, user_id)
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to add user {username}: {e}")
            raise DatabaseError(f"Failed to add user: {e}")
        finally:
            if conn:
                conn.close()

    def get_user(self, username: str) -> Optional[User]:
        """Get a user from the database."""
        conn = None
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, user_id, last_updated FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return User(
                    username=row['username'],
                    user_id=row['user_id'],
                    last_updated=datetime.datetime.fromisoformat(row['last_updated'])
                )
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get user {username}: {e}")
            raise DatabaseError(f"Failed to get user: {e}")
        finally:
            if conn:
                conn.close()

    def get_user_cache_age(self, username: str) -> Optional[float]:
        """Get the age of a user's cached data in seconds."""
        user = self.get_user(username)
        if user:
            return (datetime.datetime.now() - user.last_updated).total_seconds()
        return None

    def remove_draft(self, title: str) -> None:
        """Remove a draft from the database."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drafts WHERE title = ?", (title,))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to remove draft {title}: {e}")
            raise DatabaseError(f"Failed to remove draft: {e}")
        finally:
            if conn:
                conn.close()

    def get_all_drafts(self) -> Dict[str, Draft]:
        """Get all drafts as a dictionary of title -> Draft object."""
        conn = None
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT title, url, created_at FROM drafts")
            rows = cursor.fetchall()
            return {
                row['title']: Draft(
                    title=row['title'],
                    url=row['url'],
                    created_at=datetime.datetime.fromisoformat(row['created_at'])
                )
                for row in rows
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get all drafts: {e}")
            raise DatabaseError(f"Failed to get drafts: {e}")
        finally:
            if conn:
                conn.close()

    def get_draft(self, title: str) -> Optional[Draft]:
        """Get a specific draft by title."""
        conn = None
        try:
            conn = self._get_connection()
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
        except sqlite3.Error as e:
            logger.error(f"Failed to get draft {title}: {e}")
            raise DatabaseError(f"Failed to get draft: {e}")
        finally:
            if conn:
                conn.close()
