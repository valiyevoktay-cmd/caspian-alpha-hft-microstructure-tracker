import sqlite3
import pandas as pd
import numpy as np
import logging
import os
import datetime

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Robust path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "ofi_data.db")

class EventDrivenBacktester:
    """
    Institutional-grade Event-Driven Backtester.
    Implements Limit Order (Maker) exits, strict TP/SL constraints, 
    and extreme Z-Score filtering for optimal R:R modeling.
    """
    def __init__(self, db_path: str, z_threshold: float = 3.5):
        self.db_path = db_path
        self.z_threshold = z_threshold
        
        # Asymmetric Fee Structure
        self.taker_fee = 0.0004  # 0.04% Market Order fee (Entry / Stop Loss)
        self.maker_fee = 0.0000  # 0.00% Limit Order fee (Take Profit)
        
        # Strict Risk Parameters
        self.tp_pct = 0.0015  # Take Profit at 0.15%
        self.sl_pct = 0.0015  # Stop Loss at 0.15%
        
        # State machine variables
        self.position = 0  # 1 for Long, -1 for Short, 0 for Flat
        self.entry_price = 0.0
        self.trades = []
        
    def load_data(self) -> pd.DataFrame:
        """Loads historical metrics from SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM metrics ORDER BY timestamp ASC", conn)
                return df
        except sqlite3.OperationalError:
            logging.error(f"Database not found at {self.db_path}. Run backend first.")
            return pd.DataFrame()

    def run_simulation(self) -> None:
        """Executes the event-driven loop tick by tick with Maker/Taker logic."""
        df = self.load_data()
        if df.empty or 'ofi_zscore' not in df.columns:
            logging.warning("Insufficient data. Let the backend gather more data.")
            return

        logging.info(f"Starting Backtest | Rows: {len(df)} | Z-Threshold: {self.z_threshold}")
        
        for row in df.itertuples():
            price = row.mid_price
            zscore = row.ofi_zscore
            
            # --- EXIT LOGIC ---
            if self.position == 1: # Long
                if price >= self.entry_price * (1 + self.tp_pct):
                    self._close_position(price, row.timestamp, "Take Profit (Maker)", self.maker_fee)
                elif price <= self.entry_price * (1 - self.sl_pct):
                    self._close_position(price, row.timestamp, "Stop Loss (Taker)", self.taker_fee)
                    
            elif self.position == -1: # Short
                if price <= self.entry_price * (1 - self.tp_pct):
                    self._close_position(price, row.timestamp, "Take Profit (Maker)", self.maker_fee)
                elif price >= self.entry_price * (1 + self.sl_pct):
                    self._close_position(price, row.timestamp, "Stop Loss (Taker)", self.taker_fee)

            # --- ENTRY LOGIC ---
            elif self.position == 0:
                # Enter Long (Taker)
                if zscore > self.z_threshold:
                    self.position = 1
                    self.entry_price = price
                
                # Enter Short (Taker)
                elif zscore < -self.z_threshold:
                    self.position = -1
                    self.entry_price = price

        # Close any open positions at the end of the dataset
        if self.position != 0:
            self._close_position(df.iloc[-1]['mid_price'], df.iloc[-1]['timestamp'], "End of Data Flush", self.taker_fee)

        self.print_statistics()

    def _close_position(self, exit_price: float, timestamp: int, reason: str, exit_fee: float) -> None:
        """Calculates PnL with dynamic fees (Maker vs Taker) and logs the trade."""
        if self.position == 1:
            gross_return = (exit_price - self.entry_price) / self.entry_price
        else:
            gross_return = (self.entry_price - exit_price) / self.entry_price
            
        # Net return = Gross - Entry Fee (Taker) - Exit Fee (Dynamic)
        total_fee = self.taker_fee + exit_fee
        net_return = gross_return - total_fee
        
        self.trades.append({
            'timestamp': timestamp,
            'side': 'Long' if self.position == 1 else 'Short',
            'entry': self.entry_price,
            'exit': exit_price,
            'net_return_pct': net_return * 100,
            'fee_paid_pct': total_fee * 100,
            'reason': reason
        })
        
        self.position = 0
        self.entry_price = 0.0

    def print_statistics(self) -> None:
        """Calculates and prints professional quantitative metrics."""
        if not self.trades:
            logging.info("No trades executed. Z-Score threshold is strict, waiting for true anomalies.")
            return
            
        trades_df = pd.DataFrame(self.trades)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['net_return_pct'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        
        returns = trades_df['net_return_pct'] / 100
        mean_return = returns.mean()
        std_return = returns.std()
        
        sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        sortino_ratio = (mean_return / downside_std) if downside_std > 0 else 0.0

        trades_df['cum_pnl'] = trades_df['net_return_pct'].cumsum()
        trades_df['high_water_mark'] = trades_df['cum_pnl'].cummax()
        trades_df['drawdown'] = trades_df['cum_pnl'] - trades_df['high_water_mark']
        
        cumulative_pnl = trades_df['cum_pnl'].iloc[-1]
        max_drawdown = trades_df['drawdown'].min() 
        
        peak_timestamp = trades_df['timestamp'].iloc[0]
        max_duration_sec = 0
        
        for idx, row in trades_df.iterrows():
            if row['drawdown'] == 0:
                peak_timestamp = row['timestamp']
            else:
                duration = row['timestamp'] - peak_timestamp
                if duration > max_duration_sec:
                    max_duration_sec = duration

        mdd_duration_formatted = str(datetime.timedelta(seconds=int(max_duration_sec)))
        
        print("\n" + "="*55)
        print("📊 INSTITUTIONAL TEARSHEET (RISK METRICS) 📊")
        print("="*55)
        print(f"Total Trades Taken:      {total_trades}")
        print(f"Win Rate (Net of Fees):  {win_rate:.2f}%")
        print(f"Cumulative Net PnL:      {cumulative_pnl:.4f}%")
        print("-" * 55)
        print(f"Sharpe Ratio (Per Trade):{sharpe_ratio:.4f}")
        print(f"Sortino Ratio:           {sortino_ratio:.4f}")
        print("-" * 55)
        print(f"Max Drawdown:            {max_drawdown:.4f}%")
        print(f"Max Drawdown Duration:   {mdd_duration_formatted} (HH:MM:SS)")
        print("="*55)
        
        if total_trades > 0:
            print("\nRecent Trades:")
            display_df = trades_df[['timestamp', 'side', 'net_return_pct', 'reason']].tail(5).copy()
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp'], unit='s')
            print(display_df.to_string(index=False))

if __name__ == "__main__":
    backtester = EventDrivenBacktester(db_path=DB_PATH)
    backtester.run_simulation()