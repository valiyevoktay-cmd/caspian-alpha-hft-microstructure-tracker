import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all SQLite database I/O operations."""
    
    def __init__(self, db_path: str = "ofi_data.db"):
        self.db_path = db_path
        self._setup_db()

    def _setup_db(self) -> None:
        """Initializes the SQLite database with the Z-Score, Liquidity metrics, and Macro Events schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable Write-Ahead Logging for concurrent read/write operations (HFT standard)
            conn.execute("PRAGMA journal_mode=WAL;")
            
            cursor = conn.cursor()
            
            # --- 1. Original Metrics Table (Updated with Spread & Depth) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp INTEGER,
                    mid_price REAL,
                    ofi REAL,
                    obi REAL,
                    trade_delta REAL,
                    ofi_zscore REAL,
                    spread REAL,
                    liquidity_depth_10 REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")
            
            # --- 2. NEW: Macro Events Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp_utc DATETIME NOT NULL,
                    previous_value REAL,
                    forecast_value REAL,
                    actual_value REAL,
                    surprise_metric REAL
                )
            """)
            
            conn.commit()
        logging.info(f"Database initialized at {self.db_path} with Z-Score, Depth & Macro Schema (WAL enabled)")

    def insert_metrics(self, timestamp: int, avg_mid: float, total_ofi: float, 
                       avg_obi: float, trade_delta: float, ofi_zscore: float, 
                       spread: float, liquidity_depth_10: float) -> None:
        """Executes the insertion of aggregated tick data including rolling Z-Score and liquidity metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO metrics (timestamp, mid_price, ofi, obi, trade_delta, ofi_zscore, spread, liquidity_depth_10) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore, spread, liquidity_depth_10)
                )
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error during metrics insertion: {e}")

    def insert_macro_event(self, event_id: str, event_type: str, timestamp_utc: str, 
                           previous_value: Optional[float], forecast_value: Optional[float], 
                           actual_value: Optional[float], surprise_metric: Optional[float]) -> None:
        """Executes the insertion or update of a macro economic event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO macro_events 
                    (event_id, event_type, timestamp_utc, previous_value, forecast_value, actual_value, surprise_metric)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event_id, event_type, timestamp_utc, previous_value, forecast_value, actual_value, surprise_metric))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error during macro event insertion: {e}")