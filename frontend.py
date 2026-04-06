import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import numpy as np

# Configure the Streamlit application layout
st.set_page_config(
    page_title="Multi-Factor Microstructure Terminal",
    page_icon="🔬",
    layout="wide"
)

DB_PATH: str = "ofi_data.db"
LOOKBACK_SECONDS: int = 150 # Увеличили окно для лучшей наглядности тренда

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
                # Мы подгоняем масштаб потоков под масштаб цены для визуального сравнения
                price_std = df['price_pct'].std() if df['price_pct'].std() != 0 else 1
                
                for col in ['cum_ofi', 'cum_trades']:
                    col_std = df[col].std() if df[col].std() != 0 else 1
                    # Масштабируем поток так, чтобы его отклонение соответствовало отклонению цены
                    df[f'{col}_norm'] = ((df[col] - df[col].mean()) / col_std) * price_std
                
            return df
    except sqlite3.OperationalError:
        return pd.DataFrame()

def render_dashboard() -> None:
    """Renders the professional 3-pane quantitative dashboard."""
    st.title("Caspian Alpha- Market Microstructure Analytics (L2 + Trades)")
    st.markdown("**Instrument:** BTC/USDT | **Mode:** Normalized Relative Performance")

    df = load_and_transform_data()

    if df.empty:
        st.warning("Waiting for data synchronization... Ensure backend.py is active.")
    else:
        # Create 3-row layout
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.5, 0.25, 0.25]
        )

        # --- ROW 1: RELATIVE DYNAMICS (Normalized) ---
        # Линия цены в %
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['price_pct'], name="Price % Change",
                       line=dict(color='#AB63FA', width=3)),
            row=1, col=1
        )
        # Линия пассивного потока (OFI)
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['cum_ofi_norm'], name="Cum OFI (Normalized)",
                       line=dict(color='#FFA15A', width=2, dash='dot')),
            row=1, col=1
        )
        # Линия агрессивного потока (Trades)
        fig.add_trace(
            go.Scatter(x=df['datetime'], y=df['cum_trades_norm'], name="Cum Trades (Normalized)",
                       line=dict(color='#00CC96', width=2, dash='dash')),
            row=1, col=1
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

        # Layout styling
        fig.update_layout(
            template="plotly_dark", height=850, hovermode="x unified",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_yaxes(title_text="<b>Rel. Performance</b>", row=1, col=1)
        fig.update_yaxes(title_text="<b>Trade Delta</b>", row=2, col=1)
        fig.update_yaxes(title_text="<b>OBI</b> (-1 to 1)", row=3, col=1, range=[-1, 1])

        st.plotly_chart(fig, width="stretch")

        # Live Metrics
        st.subheader("Latest Microstructure State")
        c1, c2, c3, c4 = st.columns(4)
        latest = df.iloc[-1]
        
        c1.metric("Mid-Price", f"{latest['mid_price']:.2f}")
        c2.metric("OBI (Static)", f"{latest['obi']:.3f}")
        c3.metric("OFI (Passive)", f"{latest['ofi']:.2f}")
        c4.metric("Volatility (150s)", f"{df['price_pct'].std():.4f}%")

    time.sleep(2)
    st.rerun()

if __name__ == "__main__":
    render_dashboard()