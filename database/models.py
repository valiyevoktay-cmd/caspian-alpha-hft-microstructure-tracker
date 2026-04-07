import sqlite3
import logging

class DatabaseManager:
    """Handles all SQLite database I/O operations."""
    
    def __init__(self, db_path: str = "ofi_data.db"):
        self.db_path = db_path
        self._setup_db()

    def _setup_db(self) -> None:
        """Initializes the SQLite database with the new Z-Score schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp INTEGER,
                    mid_price REAL,
                    ofi REAL,
                    obi REAL,
                    trade_delta REAL,
                    ofi_zscore REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")
            conn.commit()
        logging.info(f"Database initialized at {self.db_path} with Z-Score Schema")

    def insert_metrics(self, timestamp: int, avg_mid: float, total_ofi: float, avg_obi: float, trade_delta: float, ofi_zscore: float) -> None:
        """Executes the insertion of aggregated data including rolling Z-Score."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO metrics (timestamp, mid_price, ofi, obi, trade_delta, ofi_zscore) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore)
            )
            conn.commit()