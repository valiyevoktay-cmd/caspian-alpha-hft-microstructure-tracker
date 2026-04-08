import heapq
import statistics
from typing import Dict, Optional, List, Tuple
from collections import deque

class OrderFlowEngine:
    """
    Core mathematical engine separated from I/O operations.
    Calculates OFI, OBI, Trade Delta, Rolling OFI Z-Score, Spread, and Liquidity Depth.
    Maintains O(1) to O(K log K) efficiency.
    """
    
    def __init__(self, zscore_window: int = 300):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        
        self.prev_best_bid: Optional[float] = None
        self.prev_best_ask: Optional[float] = None
        self.prev_bid_vol: Optional[float] = None
        self.prev_ask_vol: Optional[float] = None
        
        self.current_trade_delta: float = 0.0
        
        # Buffer format: (mid_price, ofi, obi, spread, liquidity_depth_10)
        self.tick_buffer: List[Tuple[float, float, float, float, float]] = []
        
        # Z-Score memory state
        self.zscore_window = zscore_window
        self.ofi_history = deque(maxlen=self.zscore_window)

    def update_book(self, order_dict: Dict[float, float], updates: List[List[str]]) -> None:
        """
        Updates the internal L2 order book dictionary from a partial depth stream.
        Clears the previous state to prevent phantom orders from accumulating.
        """
        order_dict.clear()  # CRITICAL: Clear phantom levels from the previous tick
        
        for price_str, qty_str in updates:
            order_dict[float(price_str)] = float(qty_str)

    def _get_top_k_volume(self, book_side: Dict[float, float], is_bid: bool, k: int = 10) -> float:
        """
        Efficiently calculates the volume of the top K levels using O(K log K).
        Bids are largest keys; Asks are smallest keys.
        """
        if not book_side:
            return 0.0
        
        # heapq is highly optimized in C and prevents full dictionary sorting
        if is_bid:
            top_k_prices = heapq.nlargest(min(k, len(book_side)), book_side.keys())
        else:
            top_k_prices = heapq.nsmallest(min(k, len(book_side)), book_side.keys())
            
        return sum(book_side[p] for p in top_k_prices)

    def process_depth(self) -> None:
        """Calculates structural metrics based on L2 updates and buffers them."""
        if not self.bids or not self.asks:
            return

        best_bid = max(self.bids.keys())
        best_ask = min(self.asks.keys())
        bid_vol = self.bids[best_bid]
        ask_vol = self.asks[best_ask]

        # --- 1. OBI Calculation (Fixed O(1) performance) ---
        obi = 0.0
        if (bid_vol + ask_vol) > 0:
            obi = (bid_vol - ask_vol) / (bid_vol + ask_vol)

        # --- 2. OFI Calculation ---
        ofi = 0.0
        if self.prev_best_bid is not None and self.prev_best_ask is not None:
            if best_bid > self.prev_best_bid: delta_w = bid_vol
            elif best_bid == self.prev_best_bid: delta_w = bid_vol - self.prev_bid_vol
            else: delta_w = -self.prev_bid_vol

            if best_ask < self.prev_best_ask: delta_v = ask_vol
            elif best_ask == self.prev_best_ask: delta_v = ask_vol - self.prev_ask_vol
            else: delta_v = -self.prev_ask_vol

            ofi = delta_w - delta_v

        # --- 3. Spread & Liquidity Vacuum Metrics ---
        mid_price = (best_bid + best_ask) / 2.0
        spread = best_ask - best_bid
        
        bid_depth_10 = self._get_top_k_volume(self.bids, is_bid=True, k=10)
        ask_depth_10 = self._get_top_k_volume(self.asks, is_bid=False, k=10)
        liquidity_depth_10 = bid_depth_10 + ask_depth_10

        # --- 4. State Update ---
        self.prev_best_bid = best_bid
        self.prev_best_ask = best_ask
        self.prev_bid_vol = bid_vol
        self.prev_ask_vol = ask_vol

        self.tick_buffer.append((mid_price, ofi, obi, spread, liquidity_depth_10))

    def process_trade(self, trade_data: dict) -> None:
        """Processes real-time market trades to calculate aggressive flow."""
        qty = float(trade_data["q"])
        is_maker = trade_data["m"]
        if is_maker:
            self.current_trade_delta -= qty
        else:
            self.current_trade_delta += qty

    def aggregate_and_reset(self) -> Optional[Tuple[float, float, float, float, float, float, float]]:
        """Aggregates data, calculates Z-Score, and resets engine state."""
        if not self.tick_buffer:
            return None
            
        n_ticks = len(self.tick_buffer)
        avg_mid = sum(t[0] for t in self.tick_buffer) / n_ticks
        total_ofi = sum(t[1] for t in self.tick_buffer)
        avg_obi = sum(t[2] for t in self.tick_buffer) / n_ticks
        avg_spread = sum(t[3] for t in self.tick_buffer) / n_ticks
        avg_depth_10 = sum(t[4] for t in self.tick_buffer) / n_ticks
        
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
        
        return (avg_mid, total_ofi, avg_obi, trade_delta, ofi_zscore, avg_spread, avg_depth_10)