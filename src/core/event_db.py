"""SQLite event database for storing and querying AI object detections."""

import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

DB_DIR = Path.home() / '.config' / 'camview'
DB_FILE = DB_DIR / 'events.db'


class EventDatabase:
    """Thread-safe SQLite database manager for AI object detection events."""

    _instance = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: Path | str | None = None) -> 'EventDatabase':
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(db_path=db_path)
            return cls._instance

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_FILE
        self._lock = threading.Lock()
        self._last_logged: dict[tuple[int, str], float] = {}

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS ai_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp REAL NOT NULL,
                            datetime_str TEXT NOT NULL,
                            channel INTEGER NOT NULL,
                            category TEXT NOT NULL,
                            label TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            snapshot_path TEXT
                        );
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON ai_events (timestamp);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_channel ON ai_events (channel);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_category ON ai_events (category);")
            finally:
                conn.close()

    def log_event(
        self,
        channel: int,
        category: str,
        label: str,
        confidence: float,
        snapshot_path: str | None = None,
        cooldown: float = 10.0,
    ) -> bool:
        """Log an AI detection event with a 10s cooldown per channel/category.

        Returns True if the event was inserted, or False if skipped due to cooldown.
        """
        now = time.monotonic()
        key = (channel, category.lower())

        with self._lock:
            last_time = self._last_logged.get(key, 0.0)
            if now - last_time < cooldown:
                return False  # Cooldown active, ignore redundant frame event

            self._last_logged[key] = now

            wall_time = time.time()
            datetime_str = datetime.fromtimestamp(wall_time).strftime('%Y-%m-%d %H:%M:%S')

            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO ai_events (timestamp, datetime_str, channel, category, label, confidence, snapshot_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        wall_time,
                        datetime_str,
                        channel,
                        category.lower(),
                        label,
                        round(confidence, 3),
                        snapshot_path,
                    ))
                return True
            finally:
                conn.close()

    def query_events(
        self,
        channel: int | None = None,
        category: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Query detection events with optional filters."""
        query = "SELECT * FROM ai_events WHERE 1=1"
        params = []

        if channel is not None:
            query += " AND channel = ?"
            params.append(channel)

        if category is not None and category.lower() != 'all':
            query += " AND category = ?"
            params.append(category.lower())

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def get_statistics(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        max_channels: int = 16,
    ) -> dict:
        """Compute aggregated detection statistics and channel-by-category matrix."""
        where_clause = " WHERE 1=1"
        params = []

        if start_time is not None:
            where_clause += " AND timestamp >= ?"
            params.append(start_time)

        if end_time is not None:
            where_clause += " AND timestamp <= ?"
            params.append(end_time)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Total count
                cursor.execute(f"SELECT COUNT(*) as total FROM ai_events{where_clause}", params)
                total_events = cursor.fetchone()['total']

                # Category breakdown
                cat_query = f"""
                    SELECT category, COUNT(*) as count 
                    FROM ai_events{where_clause} 
                    GROUP BY category
                """
                cursor.execute(cat_query, params)
                category_counts = {
                    'person': 0,
                    'vehicle': 0,
                    'animal': 0,
                }
                for row in cursor.fetchall():
                    category_counts[row['category']] = row['count']

                # Channel by category matrix
                matrix_query = f"""
                    SELECT channel, category, COUNT(*) as count 
                    FROM ai_events{where_clause} 
                    GROUP BY channel, category
                """
                cursor.execute(matrix_query, params)
                
                channel_matrix: dict[int, dict[str, int]] = {}
                for row in cursor.fetchall():
                    ch = row['channel']
                    cat = row['category']
                    cnt = row['count']
                    if ch not in channel_matrix:
                        channel_matrix[ch] = {'person': 0, 'vehicle': 0, 'animal': 0, 'total': 0}
                    channel_matrix[ch][cat] = cnt
                    channel_matrix[ch]['total'] += cnt

                return {
                    'total_events': total_events,
                    'category_counts': category_counts,
                    'channel_matrix': channel_matrix,
                }
            finally:
                conn.close()

    def clear_history(self) -> None:
        """Delete all recorded detection events."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM ai_events;")
                    conn.execute("VACUUM;")
            finally:
                conn.close()
