# ⚡ Real-Time Order Flow Imbalance (OFI) Tracker

**High-Frequency Trading (HFT) Infrastructure | Microstructure Analysis | Quantitative Finance**

## 📌 Executive Summary
This project implements a high-performance **Order Flow Imbalance (OFI)** monitoring system for the BTC/USDT pair on Binance. Unlike traditional technical indicators based on OHLC candles, this tool operates at the **Limit Order Book (LOB)** level, capturing the net aggressive buying/selling pressure at 100ms intervals. 

It is designed to identify "toxic" order flow and short-term price momentum by analyzing liquidity changes at the Best Bid and Best Ask levels.



## 🚀 Key Engineering Features
* **Asynchronous Depth Reconstruction:** Uses `asyncio` and `WebSockets` to maintain a local L2 Order Book state from Binance's partial depth streams.
* **High-Frequency Mathematical Engine:** Implements the **Cont-Stoikov (2010)** methodology for calculating OFI, distinguishing between liquidity provision and aggressive execution.
* **Dual-Service Architecture:** * **Backend:** A non-blocking ingestion engine that handles 10+ messages per second, aggregates metrics, and performs atomic writes to SQLite.
    * **Frontend:** A real-time Streamlit dashboard with sub-second polling for live visualization of mid-price vs. OFI dynamics.
* **Efficient Data Persistence:** Implements 1-second batching to prevent I/O bottlenecks while maintaining high-resolution historical data.

## 📊 Quantitative Methodology
The system calculates the **Order Flow Imbalance ($OFI_t$)** by monitoring the dynamics of the Best Bid ($P^B, V^B$) and Best Ask ($P^A, V^A$). 

The net pressure is defined as:
$$OFI_t = \Delta W_t - \Delta V_t$$

Where the Bid-side impact ($\Delta W_t$) is calculated as:
- If $P^B_t > P^B_{t-1}$: $\Delta W_t = V^B_t$ (Price improvement)
- If $P^B_t = P^B_{t-1}$: $\Delta W_t = V^B_t - V^B_{t-1}$ (Volume change)
- If $P^B_t < P^B_{t-1}$: $\Delta W_t = -V^B_{t-1}$ (Liquidity removal)

*(Equivalent logic applied to the Ask-side $\Delta V_t$)*



## 🛠 Tech Stack
* **Language:** Python 3.10+
* **Concurrency:** `asyncio`, `websockets`
* **Analysis:** `Pandas`, `NumPy`
* **Database:** `SQLite` (Atomic commits)
* **Visualization:** `Streamlit`, `Plotly Graph Objects`

📈 Live Insight Demo
<img width="1861" height="915" alt="image (8)" src="https://github.com/user-attachments/assets/dc964658-624e-48fa-b444-0ab0dea72f1f" />

Signal Example: Observe how the Cumulative OFI (orange) drops significantly before the Price (purple) follows. This is the "Informed Flow" lead time captured by Caspian Alpha.

