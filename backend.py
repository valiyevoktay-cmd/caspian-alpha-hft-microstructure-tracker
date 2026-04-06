import asyncio
import json
import sqlite3
import time
import logging
from typing import Dict, Optional, List, Tuple
import websockets
from websockets.exceptions import ConnectionClosed

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

class QuantEngine:
    """
    Advanced HFT infrastructure engine.
    Calculates Order Flow Imbalance (OFI), Order Book Imbalance (OBI), 
    and Trade Delta using Binance Combined Streams.
    """

    def __init__(self, db_path: str = "ofi_data.db"):
        # Combined stream: depth (L2) + aggTrade (Market Trades)
        self.ws_url: str = "wss://stream.binance.com:9443/stream?streams=btcusdt@depth20@100ms/btcusdt@aggTrade"
        self.db_path: str = db_path
        
        # L2 Order Book state
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        
        # Previous tick state for OFI math
        self.prev_best_bid: Optional[float] = None
        self.prev_best_ask: Optional[float] = None
        self.prev_bid_vol: Optional[float] = None
        self.prev_ask_vol: Optional[float] = None
        
        # Aggregation state
        self.current_second: int = int(time.time())
        self.current_trade_delta: float = 0.0
        self.tick_buffer: List[Tuple[float, float, float]] = []  # mid_price, ofi, obi
        
        self._setup_db()

    def _setup_db(self) -> None:
        """Initializes the SQLite database with the new multi-factor schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp INTEGER,
                    mid_price REAL,
                    ofi REAL,
                    obi REAL,
                    trade_delta REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)")
            conn.commit()
        logging.info(f"Database initialized at {self.db_path} with Multi-Factor Schema")

    def update_book(self, order_dict: Dict[float, float], updates: List[List[str]]) -> None:
        """Updates the L2 order book."""
        for price_str, qty_str in updates:
            price = float(price_str)
            qty = float(qty_str)
            if qty == 0.0:
                order_dict.pop(price, None)
            else:
                order_dict[price] = qty

    def process_depth(self) -> None:
        """Calculates OFI and OBI based on L2 updates."""
        if not self.bids or not self.asks:
            return

        best_bid = max(self.bids.keys())
        best_ask = min(self.asks.keys())
        bid_vol = self.bids[best_bid]
        ask_vol = self.asks[best_ask]

        # 1. Calculate Order Book Imbalance (OBI) across all available levels
        total_bid_vol = sum(self.bids.values())
        total_ask_vol = sum(self.asks.values())
        obi = 0.0
        if (total_bid_vol + total_ask_vol) > 0:
            obi = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)

        # 2. Calculate Order Flow Imbalance (OFI)
        ofi = 0.0
        if self.prev_best_bid is not None and self.prev_best_ask is not None:
            # Bid side delta (Delta W_t)
            if best_bid > self.prev_best_bid:
                delta_w = bid_vol
            elif best_bid == self.prev_best_bid:
                delta_w = bid_vol - self.prev_bid_vol
            else:
                delta_w = -self.prev_bid_vol

            # Ask side delta (Delta V_t)
            if best_ask < self.prev_best_ask:
                delta_v = ask_vol
            elif best_ask == self.prev_best_ask:
                delta_v = ask_vol - self.prev_ask_vol
            else:
                delta_v = -self.prev_ask_vol

            ofi = delta_w - delta_v

        mid_price = (best_bid + best_ask) / 2.0

        # Update previous states
        self.prev_best_bid = best_bid
        self.prev_best_ask = best_ask
        self.prev_bid_vol = bid_vol
        self.prev_ask_vol = ask_vol

        # Buffer the depth metrics
        self.tick_buffer.append((mid_price, ofi, obi))
        self._check_flush()

    def process_trade(self, trade_data: dict) -> None:
        """Processes real-time market trades to calculate aggressive flow."""
        qty = float(trade_data["q"])
        is_maker = trade_data["m"]
        
        # If the buyer is the market maker (m=True), it's a Market Sell.
        # If the buyer is the market taker (m=False), it's a Market Buy.
        if is_maker:
            self.current_trade_delta -= qty
        else:
            self.current_trade_delta += qty
            
        self._check_flush()

    def _check_flush(self) -> None:
        """Flushes data to SQLite every second."""
        now = int(time.time())
        
        if now > self.current_second:
            if self.tick_buffer:
                # Aggregate metrics for the past second
                avg_mid = sum(t[0] for t in self.tick_buffer) / len(self.tick_buffer)
                total_ofi = sum(t[1] for t in self.tick_buffer)
                avg_obi = sum(t[2] for t in self.tick_buffer) / len(self.tick_buffer)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO metrics (timestamp, mid_price, ofi, obi, trade_delta) VALUES (?, ?, ?, ?, ?)",
                        (self.current_second, avg_mid, total_ofi, avg_obi, self.current_trade_delta)
                    )
                    conn.commit()
                
                # Updated Heartbeat Log
                logging.info(f"DB Flush | Mid: {avg_mid:.2f} | OFI: {total_ofi:.2f} | OBI: {avg_obi:.3f} | Net Trades: {self.current_trade_delta:.2f}")
                
            # Reset buffers and timers for the new second
            self.tick_buffer.clear()
            self.current_trade_delta = 0.0 
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
                        
                        # Combined streams wrap data in {"stream": "...", "data": {...}}
                        stream_name = payload.get("stream", "")
                        data = payload.get("data", {})
                        
                        if "depth" in stream_name:
                            self.update_book(self.bids, data.get("bids", []))
                            self.update_book(self.asks, data.get("asks", []))
                            self.process_depth()
                        elif "aggTrade" in stream_name:
                            self.process_trade(data)
                            
            except ConnectionClosed as e:
                logging.error(f"WebSocket closed: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)
            except Exception as e:
                logging.error(f"Unexpected error: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)

if __name__ == "__main__":
    engine = QuantEngine()
    try:
        asyncio.run(engine.connect())
    except KeyboardInterrupt:
        logging.info("Engine stopped by user.")