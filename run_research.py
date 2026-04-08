import sqlite3
import pandas as pd
import datetime
import logging
from strategies.event_study import EventStudySlicer

# Configure logging for clear terminal output
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_PATH = "ofi_data.db"

def inject_mock_event() -> str:
    """Injects a fake macroeconomic event into the middle of our dataset."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Find the timestamp of the last recorded tick in the database
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM metrics")
            row = cursor.fetchone()
            
            if not row or row[0] is None:
                logging.error("Database is empty! Let the streamer run for at least 5 minutes.")
                return None
                
            last_timestamp = row[0]
            
            # Place the event exactly 2 minutes before the most recent data point
            t_zero_unix = last_timestamp - 120 
            t_zero_iso = datetime.datetime.fromtimestamp(t_zero_unix, tz=datetime.timezone.utc).isoformat()
            
            event_id = "MOCK_CPI_001"
            cursor.execute("""
                INSERT OR REPLACE INTO macro_events 
                (event_id, event_type, timestamp_utc, previous_value, forecast_value, actual_value, surprise_metric)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, "US_CPI_YoY", t_zero_iso, 3.1, 3.1, 3.4, 0.3))
            conn.commit()
            
            logging.info(f"Mock event {event_id} successfully injected at T=0 ({t_zero_iso})")
            return event_id
            
    except Exception as e:
        logging.error(f"Error injecting mock event: {e}")
        return None

if __name__ == "__main__":
    logging.info("Starting Macro-Micro Event Simulation...")
    
    # 1. Inject the fake CPI event
    event_id = inject_mock_event()
    
    # 2. Call the Slicer to analyze the liquidity reaction around T=0
    if event_id:
        logging.info("-" * 60)
        slicer = EventStudySlicer(db_path=DB_PATH)
        slicer.analyze_liquidity_vacuum(event_id=event_id)
        logging.info("-" * 60)