from typing import Dict, Optional, List, Tuple
from collections import deque
import statistics

class OrderFlowEngine:
    """
    Core mathematical engine separated from I/O operations.
    Calculates OFI, OBI, Trade Delta, and Rolling OFI Z-Score.
    """
    
    def __init__(self, zscore_window: int = 300):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        
        self.prev_best_bid: Optional[float] = None
        self.prev_best_ask: Optional[float] = None
        self.prev_bid_vol: Optional[float] = None
        self.prev_ask_vol: Optional[float] = None
        
        self.current_trade_delta: float = 0.0
        self.tick_buffer: List[Tuple[float, float, float]] = []
        
        # Z-Score memory state
        self.zscore_window = zscore_window
        self.ofi_history = deque(maxlen=self.zscore_window)

    def update_book(self, order_dict: Dict[float, float], updates: List[List[str]]) -> None:
        """Updates the internal L2 order book dictionary."""
        for price_str, qty_str in updates:
            price = float(price_str)
            qty = float(qty_str)
            if qty == 0.0:
                order_dict.pop(price, None)
            else:
                order_dict[price] = qty

    def process_depth(self) -> None:
        """Calculates OFI and OBI based on L2 updates and buffers them."""
        if not self.bids or not self.asks:
            return

        best_bid = max(self.bids.keys())
        best_ask = min(self.asks.keys())
        bid_vol = self.bids[best_bid]
        ask_vol = self.asks[best_ask]

        total_bid_vol = sum(self.bids.values())
        total_ask_vol = sum(self.asks.values())
        obi = 0.0
        if (total_bid_vol + total_ask_vol) > 0:
            obi = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol)

        ofi = 0.0
        if self.prev_best_bid is not None and self.prev_best_ask is not None:
            if best_bid > self.prev_best_bid: delta_w = bid_vol
            elif best_bid == self.prev_best_bid: delta_w = bid_vol - self.prev_bid_vol
            else: delta_w = -self.prev_bid_vol

            if best_ask < self.prev_best_ask: delta_v = ask_vol
            elif best_ask == self.prev_best_ask: delta_v = ask_vol - self.prev_ask_vol
            else: delta_v = -self.prev_ask_vol

            ofi = delta_w - delta_v

        mid_price = (best_bid + best_ask) / 2.0

        self.prev_best_bid = best_bid
        self.prev_best_ask = best_ask
        self.prev_bid_vol = bid_vol
        self.prev_ask_vol = ask_vol

        self.tick_buffer.append((mid_price, ofi, obi))

    def process_trade(self, trade_data: dict) -> None:
        """Processes real-time market trades to calculate aggressive flow."""
        qty = float(trade_data["q"])
        is_maker = trade_data["m"]
        if is_maker:
            self.current_trade_delta -= qty
        else:
            self.current_trade_delta += qty

    def aggregate_and_reset(self) -> Optional[Tuple[float, float, float, float, float]]:
        """Aggregates data, calculates Z-Score, and resets engine state."""
        if not self.tick_buffer:
            return None
            
        avg_mid = sum(t[0] for t in self.tick_buffer) / len(self.tick_buffer)
        total_ofi = sum(t[1] for t in self.tick_buffer)
        avg_obi = sum(t[2] for t in self.tick_buffer) / len(self.tick_buffer)
        trade_delta = self.current_trade_delta
        
        # Calculate Rolling Z-Score for OFI
        self.ofi_history.append(total_ofi)
        ofi_zscore = 0.0
        
        if len(self.ofi_history) > 1:
            mean_ofi = statistics.mean(self.ofi_history)
            std_ofi = statistics.stdev(self.ofi_history)
            if std_ofi > 0:
                ofi_zscore = (total_ofi - mean_ofi) / std_ofi
        
        # Reset buffers
        self.tick_buffer.clear()
        self.current_trade_delta = 0.0 
        
        return (avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore)