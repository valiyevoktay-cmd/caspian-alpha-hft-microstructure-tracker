import sqlite3
import pandas as pd
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class EventStudySlicer:
    """
    Analyzes market microstructure behavior around specific macroeconomic events.
    Focuses on detecting the 'Liquidity Vacuum' effect.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _fetch_event(self, event_id: str) -> Optional[pd.Series]:
        """Retrieves macro event metadata from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM macro_events WHERE event_id = ?"
                df = pd.read_sql_query(query, conn, params=(event_id,))
                if df.empty:
                    logger.warning(f"Event ID {event_id} not found in database.")
                    return None
                return df.iloc[0]
        except Exception as e:
            logger.error(f"Error fetching event metadata: {e}")
            return None

    def _fetch_tick_data(self, start_unix: int, end_unix: int) -> pd.DataFrame:
        """Fetches tick metrics between two unix timestamps."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM metrics WHERE timestamp BETWEEN ? AND ?"
                return pd.read_sql_query(query, conn, params=(start_unix, end_unix))
        except Exception as e:
            logger.error(f"Error fetching tick data: {e}")
            return pd.DataFrame()

    def analyze_liquidity_vacuum(self, event_id: str) -> None:
        """
        Slices depth data around T=0 and calculates the liquidity evaporation percentage.
        """
        event = self._fetch_event(event_id)
        if event is None:
            return

        # T=0 is our event timestamp (stored as ISO in DB, but we need Unix for metrics comparison)
        t_zero_iso = event['timestamp_utc']
        t_zero_dt = pd.to_datetime(t_zero_iso)
        t_zero_unix = int(t_zero_dt.timestamp())

        logger.info(f"Analyzing Event: {event['event_type']} | T=0: {t_zero_iso}")

        # Define Windows (in seconds)
        # Baseline: 5 minutes of normal market activity
        # Vacuum: 30 seconds immediately before the news
        baseline_start = t_zero_unix - 300
        baseline_end = t_zero_unix - 31
        vacuum_start = t_zero_unix - 30
        vacuum_end = t_zero_unix

        # Fetch Data slices
        df_baseline = self._fetch_tick_data(baseline_start, baseline_end)
        df_vacuum = self._fetch_tick_data(vacuum_start, vacuum_end)

        if df_baseline.empty or df_vacuum.empty:
            logger.error("Insufficient data points found in the requested windows.")
            logger.info(f"Baseline points: {len(df_baseline)} | Vacuum points: {len(df_vacuum)}")
            return

        # Calculate Results
        avg_baseline_depth = df_baseline['liquidity_depth_10'].mean()
        avg_vacuum_depth = df_vacuum['liquidity_depth_10'].mean()
        
        if avg_baseline_depth > 0:
            drop_pct = ((avg_baseline_depth - avg_vacuum_depth) / avg_baseline_depth) * 100
            
            logger.info(f"AVERAGE BASELINE DEPTH: {avg_baseline_depth:.4f} BTC")
            logger.info(f"AVERAGE VACUUM DEPTH:   {avg_vacuum_depth:.4f} BTC")
            logger.info(f"LIQUIDITY EVAPORATION:  {drop_pct:.2f}%")
            
            if drop_pct > 20:
                logger.info("RESULT: Liquidity Vacuum Detected. Market makers reduced exposure before news.")
            else:
                logger.info("RESULT: No significant liquidity pull-back observed.")
        else:
            logger.warning("Baseline depth is zero, cannot calculate drop percentage.")