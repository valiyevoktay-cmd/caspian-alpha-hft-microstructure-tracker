import asyncio
import logging
from database.models import DatabaseManager
from core.engine import OrderFlowEngine
from core.stream import BinanceStreamer

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

if __name__ == "__main__":
    # Dependency Injection: Wiring the modules together
    db_path = "ofi_data.db"
    
    db_manager = DatabaseManager(db_path=db_path)
    quant_engine = OrderFlowEngine()
    streamer = BinanceStreamer(db_manager=db_manager, engine=quant_engine)
    
    try:
        logging.info("Starting Modular Caspian Alpha Backend...")
        asyncio.run(streamer.connect())
    except KeyboardInterrupt:
        logging.info("Engine stopped by user.")