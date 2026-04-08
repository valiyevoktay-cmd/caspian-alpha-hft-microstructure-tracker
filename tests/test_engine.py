import pytest
from core.engine import OrderFlowEngine

def test_ofi_calculation_basic():
    """
    Tests the fundamental OFI (Order Flow Imbalance) math logic.
    Simulates a sequence of L2 order book updates and verifies the delta.
    Updated to handle all 7 metrics from Caspian Alpha v3.0.
    """
    engine = OrderFlowEngine()
    
    # --- TICK 1: Initial State ---
    # Setup initial Order Book
    bids_1 = [["100.0", "10.0"], ["99.0", "5.0"]]
    asks_1 = [["102.0", "10.0"], ["103.0", "5.0"]]
    
    engine.update_book(engine.bids, bids_1)
    engine.update_book(engine.asks, asks_1)
    engine.process_depth()
    
    # Internal state at Tick 1: 
    # Prev Best Bid = 100.0 (Vol: 10.0)
    # Prev Best Ask = 102.0 (Vol: 10.0)
    # OFI for Tick 1 is 0.0 (no previous data to compare)

    # --- TICK 2: Market Shift ---
    # Scenario: 
    # 1. New aggressive buyer puts a bid at 101.0 with volume 5.0.
    #    Delta W = 5.0 (Price improved, full new volume is added)
    # 2. Sellers add 2.0 volume to the best ask at 102.0 (Total becomes 12.0).
    #    Delta V = 12.0 - 10.0 = 2.0 (Price same, volume increased)
    # Expected OFI = Delta W - Delta V = 5.0 - 2.0 = 3.0
    
    bids_2 = [["101.0", "5.0"]]  # New Best Bid
    asks_2 = [["102.0", "12.0"]] # Update existing Best Ask
    
    engine.update_book(engine.bids, bids_2)
    engine.update_book(engine.asks, asks_2)
    engine.process_depth()
    
    # Aggregate and verify
    metrics = engine.aggregate_and_reset()
    assert metrics is not None, "Metrics should not be None after processing depth."
    
    # --- FIX: Unpack all 7 values now returned by the engine ---
    (avg_mid, total_ofi, avg_obi, trade_delta, 
     ofi_zscore, avg_spread, avg_depth_10) = metrics
    
    # Total OFI is sum of Tick 1 (0.0) and Tick 2 (3.0)
    assert total_ofi == 3.0, f"Expected OFI 3.0, got {total_ofi}"
    assert avg_spread > 0, "Spread should be positive in a healthy market simulation"


def test_trade_delta_logic():
    """
    Tests the parsing of aggTrade events and Trade Delta classification.
    """
    engine = OrderFlowEngine()
    
    # 1. Simulate a Taker Buy (Market Buy). Maker is NOT the buyer (m=False).
    # This should add to the trade delta (Aggressive Buying).
    engine.process_trade({"q": "1.5", "m": False})
    
    # 2. Simulate a Taker Sell (Market Sell). Maker IS the buyer (m=True).
    # This should subtract from the trade delta (Aggressive Selling).
    engine.process_trade({"q": "0.5", "m": True})
    
    # Expected Net Delta = 1.5 - 0.5 = 1.0
    assert engine.current_trade_delta == 1.0, f"Expected Trade Delta 1.0, got {engine.current_trade_delta}"