<div align="center">

# 🔱 CASPIAN ALPHA
### **High-Frequency Market Microstructure & Order Flow Engine**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Market: HFT](https://img.shields.io/badge/Market-HFT%20%2F%20Quant-FF6F61?style=for-the-badge)](https://en.wikipedia.org/wiki/High-frequency_trading)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Binance API](https://img.shields.io/badge/Data-Binance%20L2-F3BA2F?style=for-the-badge&logo=binance&logoColor=black)](https://binance-docs.github.io/apidocs/spot/en/)

**"Trading is the physics of liquidity. Caspian Alpha is the lens."**

[Explore Methodology](#-quantitative-methodology) • [Engineering Details](#-key-engineering-features) • [Quick Start](#-quick-start)

</div>

---

## 📑 Executive Summary
Most retail indicators are **lagging**—they tell you what happened. **Caspian Alpha** is **leading**—it tells you what is *happening*.

This engine bypasses traditional OHLC candles to analyze the **Limit Order Book (LOB)** in real-time. By reconstructing the L2 state of BTC/USDT at 100ms intervals, it identifies **"toxic" order flow**, **absorption**, and **informed momentum** before they manifest in price action. It transforms raw binary streams into institutional-grade alpha signals.

---

## 📊 Quantitative Methodology

The core of the engine is the **Order Flow Imbalance ($OFI_t$)** based on the *Cont-Stoikov (2010)* framework. We track the net aggressive pressure by deconstructing liquidity changes at the Best Bid ($P^B, V^B$) and Best Ask ($P^A, V^A$).

### **The Fundamental Equation**
$$OFI_t = \Delta W_t - \Delta V_t$$

Where **$\Delta W_t$** (Bid-side impact) is calculated as:
* **Price Improvement:** If $P^B_t > P^B_{t-1} \implies \Delta W_t = V^B_t$
* **Volume Accumulation:** If $P^B_t = P^B_{t-1} \implies \Delta W_t = V^B_t - V^B_{t-1}$
* **Liquidity Removal:** If $P^B_t < P^B_{t-1} \implies \Delta W_t = -V^B_{t-1}$

> **Multi-Factor Alpha:** The system correlates **OFI** with **OBI (Order Book Imbalance)** across 20 depth levels and **Aggressive Trade Delta** to filter out spoofing and fake liquidity.

---

## 🚀 Key Engineering Features

* **⚡ Async L2 Reconstruction:** Leverages `asyncio` and `WebSockets` to maintain a zero-latency local mirror of the exchange state. 
* **🧠 Intelligent Persistence:** Implements **Smart Batching**. High-frequency metrics are aggregated in-memory and committed to **SQLite** once per second using atomic writes to prevent I/O blocking.
* **📉 Professional Visualization:** A dual-axis **Streamlit** dashboard using `Plotly Graph Objects`. Features **Normalized Relative Performance** mode for direct comparison of Price Change vs. Cumulative OFI/Trades.
* **🛡️ Robust Connectivity:** Built-in exponential backoff reconnection logic to ensure 24/7 data ingestion even during network instability.

---

## 🛠 Tech Stack

| Category | Technology |
| :--- | :--- |
| **Language** | Python 3.10+ (Strictly Typed) |
| **Concurrency** | `asyncio`, `websockets` |
| **Analytics** | `Pandas`, `NumPy`, `SciPy` |
| **Database** | `SQLite` (WAL Mode) |
| **Visualization** | `Streamlit`, `Plotly` |

---



📈 Live Insight Demo
<img width="1861" height="915" alt="image (8)" src="https://github.com/user-attachments/assets/dc964658-624e-48fa-b444-0ab0dea72f1f" />

Signal Example: Observe how the Cumulative OFI (orange) drops significantly before the Price (purple) follows. This is the "Informed Flow" lead time captured by Caspian Alpha.

