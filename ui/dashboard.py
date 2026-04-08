import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import os

# Configure the Streamlit application layout
st.set_page_config(
    page_title="Multi-Factor Microstructure Terminal",
    page_icon="🔬",
    layout="wide"
)

# Robust path resolution: Automatically find the database in the parent directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DB_PATH: str = os.path.join(PROJECT_ROOT, "ofi_data.db")

# Default fallback, though now controlled by UI
LOOKBACK_SECONDS: int = 150  

def load_and_transform_data(limit: int = LOOKBACK_SECONDS) -> pd.DataFrame:
    """
    Retrieves data and applies Z-score normalization for cross-asset correlation.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT * FROM metrics ORDER BY timestamp DESC LIMIT {limit}"
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                # 1. Basic cleaning
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)
                
                # 2. Price Normalization (% change from window start)
                start_price = df['mid_price'].iloc[0]
                df['price_pct'] = (df['mid_price'] / start_price - 1) * 100
                
                # 3. Cumulative Flow Calculation
                df['cum_ofi'] = df['ofi'].cumsum()
                df['cum_trades'] = df['trade_delta'].cumsum()
                
                # 4. Z-Score Scaling to Price Volatility
                # Scaling order flows to match price variance for visual comparison
                price_std = df['price_pct'].std() if df['price_pct'].std() != 0 else 1
                
                for col in ['cum_ofi', 'cum_trades']:
                    col_std = df[col].std() if df[col].std() != 0 else 1
                    # Scale flow so its deviation matches price deviation
                    df[f'{col}_norm'] = ((df[col] - df[col].mean()) / col_std) * price_std
                
            return df
    except sqlite3.OperationalError:
        return pd.DataFrame()

def render_dashboard() -> None:
    """Renders the professional 4-pane quantitative dashboard with interactive controls."""
    
    # --- UI CONTROLS (Top Panel) ---
    col_title, col_controls = st.columns([0.7, 0.3])
    
    with col_title:
        st.title("Caspian Alpha 3.0 - Market Microstructure Analytics")
        st.markdown("**Instrument:** BTC/USDT | **Mode:** Normalized Relative Performance")
        
    with col_controls:
        st.write("") # Padding for vertical alignment
        # 1. LIVE MODE TOGGLE
        live_mode = st.toggle("🔴 Live Market Data", value=True, help="Turn off to pause updates and scroll charts freely.")
        # 2. HISTORY SLIDER
        history_limit = st.slider("Lookback Window (Ticks)", min_value=100, max_value=2000, value=300, step=100)

    # Fetch data based on the dynamic slider
    df = load_and_transform_data(limit=history_limit)

    if df.empty:
        st.warning(f"Waiting for data synchronization... Ensure backend is active and writing to {DB_PATH}")
    else:
        # Create 4-row layout with secondary Y-axes for overlaying different scales
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.4, 0.2, 0.2, 0.2],
            specs=[
                [{"secondary_y": True}],  # Row 1: Rel Performance + Liquidity Depth
                [{"secondary_y": False}], # Row 2: Trade Delta
                [{"secondary_y": False}], # Row 3: OBI
                [{"secondary_y": True}]   # Row 4: Z-Score + Spread
            ]
        )

        # --- ROW 1: RELATIVE DYNAMICS (Normalized) & LIQUIDITY DEPTH ---
        # User's Original Traces
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['price_pct'], name="Price % Change",
                       line=dict(color='#AB63FA', width=3)),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['cum_ofi_norm'], name="Cum OFI (Normalized)",
                       line=dict(color='#FFA15A', width=2, dash='dot')),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['cum_trades_norm'], name="Cum Trades (Normalized)",
                       line=dict(color='#00CC96', width=2, dash='dash')),
            row=1, col=1, secondary_y=False
        )
        # Liquidity Depth 10 Background
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['liquidity_depth_10'], name="Liquidity Depth 10",
                       fill='tozeroy', line=dict(color="rgba(255, 255, 255, 0.1)"), 
                       hoverinfo="y+name"),
            row=1, col=1, secondary_y=True
        )

        # --- ROW 2: AGGRESSIVE FLOW (Net Volume) ---
        trade_colors = ['#00CC96' if val > 0 else '#EF553B' for val in df['trade_delta']]
        fig.add_trace(
            go.Bar(x=df['datetime'], y=df['trade_delta'], name="Trade Delta", 
                   marker_color=trade_colors, opacity=0.8),
            row=2, col=1
        )

        # --- ROW 3: STATIC LIQUIDITY (OBI) ---
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['obi'], name="OBI (Depth)", fill='tozeroy',
                       line=dict(color='#00B5F7', width=1.5), fillcolor='rgba(0, 181, 247, 0.1)'),
            row=3, col=1
        )

        # --- ROW 4: ANOMALIES & FRICTION (Z-Score & Spread) ---
        # Z-Score (Left Y)
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['ofi_zscore'], name="OFI Z-Score",
                       line=dict(color='#FFCC00', width=2)),
            row=4, col=1, secondary_y=False
        )
        # Institutional Threshold lines for Z-Score
        fig.add_hline(y=3, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=4, col=1, secondary_y=False)
        fig.add_hline(y=-3, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=4, col=1, secondary_y=False)
        
        # Spread (Right Y)
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['spread'], name="Spread",
                       line=dict(color='#F494E8', width=1.5), fill='tozeroy', fillcolor='rgba(244, 148, 232, 0.1)'),
            row=4, col=1, secondary_y=True
        )

        # --- Layout styling ---
        fig.update_layout(
            template="plotly_dark", height=1000, hovermode="x unified",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # NEW: Enable Range Slider on the bottom x-axis for zooming
        fig.update_xaxes(rangeslider_visible=True, row=4, col=1)

        fig.update_yaxes(title_text="<b>Rel. Performance</b>", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="<b>Depth (BTC)</b>", showgrid=False, row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="<b>Trade Delta</b>", row=2, col=1)
        fig.update_yaxes(title_text="<b>OBI</b> (-1 to 1)", row=3, col=1, range=[-1, 1])
        fig.update_yaxes(title_text="<b>Z-Score</b>", row=4, col=1, secondary_y=False)
        fig.update_yaxes(title_text="<b>Spread</b>", showgrid=False, row=4, col=1, secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

        # --- Live Metrics (Expanded) ---
        st.subheader("Latest Microstructure State")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        c1.metric("Mid-Price", f"{latest['mid_price']:.2f}", f"{latest['mid_price'] - prev['mid_price']:.2f}")
        c2.metric("OBI (Static)", f"{latest['obi']:.3f}", f"{latest['obi'] - prev['obi']:.3f}")
        c3.metric("OFI (Passive)", f"{latest['ofi']:.2f}", f"{latest['ofi'] - prev['ofi']:.2f}")
        c4.metric("Volatility (150s)", f"{df['price_pct'].std():.4f}%")
        
        # New Metrics integrated into your UI
        z_color = "normal" if abs(latest['ofi_zscore']) < 3 else "inverse"
        c5.metric("Z-Score", f"{latest['ofi_zscore']:.2f}", f"{latest['ofi_zscore'] - prev['ofi_zscore']:.2f}", delta_color=z_color)
        c6.metric("Spread", f"{latest['spread']:.2f}", f"{latest['spread'] - prev['spread']:.2f}", delta_color="inverse")

    # --- CONDITIONAL REFRESH LOGIC ---
    if live_mode:
        time.sleep(2)
        st.rerun()
    else:
        st.info("⏸️ **Dashboard Paused.** Auto-refresh disabled. Use the slider above to fetch more history, and the range slider on the bottom chart to zoom.")

if __name__ == "__main__":
    render_dashboard()