import asyncio
import json
import time
import logging
import websockets
from websockets.exceptions import ConnectionClosed

from core.engine import OrderFlowEngine
from database.models import DatabaseManager

class BinanceStreamer:
    """Handles WebSocket connections, I/O routing, and database flushing timing."""
    
    def __init__(self, db_manager: DatabaseManager, engine: OrderFlowEngine):
        self.ws_url: str = "wss://stream.binance.com:9443/stream?streams=btcusdt@depth20@100ms/btcusdt@aggTrade"
        self.db = db_manager
        self.engine = engine
        self.current_second: int = int(time.time())

    def _check_flush(self) -> None:
        """Checks if a second has passed to flush aggregated data to the database."""
        now = int(time.time())
        if now > self.current_second:
            metrics = self.engine.aggregate_and_reset()
            
            if metrics:
                avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore = metrics
                
                # Route all 5 metrics to the database
                self.db.insert_metrics(self.current_second, avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore)
                
                logging.info(f"DB Flush | Mid: {avg_mid:.2f} | Z-Score: {ofi_zscore:>5.2f} | OBI: {avg_obi:.3f} | Trades: {trade_delta:.2f}")
            
            self.current_second = now

    async def connect(self) -> None:
        """Main async loop to handle combined stream payloads."""
        while True:
            try:
                logging.info(f"Connecting to {self.ws_url}...")
                async with websockets.connect(self.ws_url) as ws:
                    logging.info("WebSocket connected successfully.")
                    while True:
                        msg = await ws.recv()
                        payload = json.loads(msg)
                        
                        stream_name = payload.get("stream", "")
                        data = payload.get("data", {})
                        
                        if "depth" in stream_name:
                            self.engine.update_book(self.engine.bids, data.get("bids", []))
                            self.engine.update_book(self.engine.asks, data.get("asks", []))
                            self.engine.process_depth()
                        elif "aggTrade" in stream_name:
                            self.engine.process_trade(data)
                            
                        self._check_flush()
                        
            except ConnectionClosed as e:
                logging.error(f"WebSocket closed: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)
            except Exception as e:
                logging.error(f"Unexpected error: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)