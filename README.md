# 🌊 Caspian Alpha: Market Microstructure & Order Flow Imbalance Engine

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="Actions" />
</p>

📌 **Executive Summary**
**Caspian Alpha** is an institutional-grade, event-driven quantitative research environment designed to analyze Level 2 (L2) market microstructure dynamics in real-time. Built with a focus on data engineering and econometric rigor, this pipeline ingests high-frequency WebSocket streams, calculates normalized liquidity anomalies, and executes empirical event studies on macroeconomic shocks.

> *Academic & Engineering Disclaimer:* This project is strictly a Proof of Concept (PoC) for signal generation and statistical analysis. True zero-latency High-Frequency Trading (HFT) execution is fundamentally constrained by Python's Global Interpreter Lock (GIL) and garbage collector. As such, this engine models *research potential* and *alpha generation* rather than hardware-level execution.

---

## 🎯 Key Differentiators (For Quant & Engineering Teams)
* **Full-Stack Quant Architecture:** Bridges the gap between Data Engineering (asyncio, WebSockets, Docker, CI/CD) and Quantitative Research (OFI, Sharpe/Sortino ratios, Event Studies).
* **Adverse Selection Modeling:** Moves beyond standard price action by empirically tracking "Liquidity Vacuums"—the exact moments market makers pull quotes prior to macro-shocks.
* **Deterministic $\mathcal{O}(1)$ State Machine:** Implements a highly optimized local order book reconstruction, avoiding CPU-heavy deep rescans during high-volatility tick bursts.

---

## 📈 Visual Analytics & UI Terminal

<img width="1866" height="919" alt="image (16)" src="https://github.com/user-attachments/assets/689aeb14-098d-4e76-9fac-3b5745f4c1a4" />

![Caspian Alpha Dashboard]

The system includes a state-of-the-art Streamlit/Plotly dashboard for real-time visual inspection of the order book physics. 

**Terminal Features:**
* **Normalized Relative Performance:** Visualizes Z-scaled liquidity deltas versus price action to spot hidden divergences.
* **Liquidity Vacuum Overlay:** Displays Top-10 Depth as a background area chart to visually track liquidity evaporation.
* **Interactive Research Controls:** Features a `Live Market Data` toggle. Analysts can pause the live feed to freeze the state machine, allowing them to zoom, pan, and granularly investigate historical anomalies using Lookback Sliders.
   
---

## 🧮 Mathematical Framework

The core engine avoids moving averages or lagging price indicators, focusing entirely on the physics of the limit order book and the mechanics of liquidity consumption.

### 1. Multi-Factor Liquidity Analysis
Beyond raw price action, the engine tracks the interaction between different layers of liquidity to identify high-probability alpha signals:

* **Order Flow Imbalance (OFI):** Measures the net pressure of passive liquidity provision and consumption at the best quotes.
  $$OFI_t = \Delta W_t - \Delta V_t$$
  Where $\Delta W_t$ (Bid-side impact) is explicitly calculated as:
  * **Price Improvement:** If $P_t^B > P_{t-1}^B \implies \Delta W_t = V_t^B
  * **Volume Accumulation:** If $P_t^B = P_{t-1}^B \implies \Delta W_t = V_t^B - V_{t-1}^B
  * **Liquidity Removal:** If $P_t^B < P_{t-1}^B \implies \Delta W_t = -V_{t-1}^B
  *(An equivalent symmetric logic is applied to the Ask-side $\Delta V_t$)*

* **Order Book Imbalance (OBI):** A normalized measure of static liquidity depth at the best bid/ask levels, indicating immediate directional bias.
  $$OBI_t = \frac{V_t^B - V_t^A}{V_t^B + V_t^A}$$

* **Liquidity Depth Profile:** Calculates the total aggregate volume in the top $K=10$ levels of the book using an $\mathcal{O}(K \log K)$ heap structure to monitor institutional risk appetite.

### 2. Statistical Normalization (Z-Score)
To filter out background market noise and identify statistically significant spoofing or liquidity absorption events, the raw OFI is standardized over a rolling intraday window:
$$Z_{OFI} = \frac{OFI_t - \mu_{OFI}}{\sigma_{OFI}}$$
Signals where $|Z| > 3.0$ are flagged as extreme microstructural anomalies.

### 3. Risk-Adjusted Performance Metrics
The integrated backtester strictly enforces institutional market frictions, applying asymmetric fee structures. Strategy viability is evaluated using core risk metrics:

* **Sharpe Ratio:** Measures the excess return per unit of total risk.
  $$Sharpe = \frac{R_p - R_f}{\sigma_p}$$
* **Sortino Ratio:** Focuses on downside risk by differentiating harmful volatility from total overall volatility.
  $$Sortino = \frac{R_p - R_f}{\sigma_d}$$

---

## 🔬 Event-Driven Macro Research (Liquidity Vacuum)

Caspian Alpha includes a dedicated research slicer (`run_research.py`) designed to empirically prove microstructural theories, specifically the **Liquidity Vacuum effect** during macroeconomic shocks (e.g., US CPI, FOMC).

<img width="1403" height="240" alt="image (15)" src="https://github.com/user-attachments/assets/444c8a2f-beb3-4062-a43d-49a48e1fb4b5" />

> *Empirical Proof: The engine successfully slicing event windows and detecting a 25.6% drop in Top-10 book depth just 30 seconds before a simulated CPI shock.*

By injecting timestamped macro-events into the database, the `EventStudySlicer` algorithm:
1. Slices a **baseline window** (e.g., 5 minutes prior to T=0).
2. Slices an **event horizon window** (e.g., 30 seconds before T=0).
3. Calculates the exact percentage of **Liquidity Evaporation** as market makers pull quotes to avoid adverse selection (toxic flow) before the news breaks.
   
---

## ⚙️ Architecture & Tech Stack

| Category | Technology Used |
| :--- | :--- |
| **Language** | Python 3.10+ (Strictly Typed) |
| **Concurrency** | `asyncio`, `websockets` |
| **Data & Math** | `pandas`, `numpy`, `scipy` |
| **UI Dashboard** | `streamlit`, `plotly` |
| **Persistence** | SQLite (WAL Mode) |
| **DevOps** | Docker, GitHub Actions, `pytest` |

**Project Structure:**
* `core/`: Contains the asynchronous WebSocket ingester and the $\mathcal{O}(1)$ L2 Order Book state machine.
* `ui/`: A Streamlit/Plotly dashboard for real-time visual inspection with history slicing.
* `strategies/`: Event-driven historical simulation engines and macro-event slicers.
* `database/`: Thread-safe SQLite buffer for high-frequency tick aggregation.
* `run_research.py`: Execution script for liquidity vacuum and anomaly research.

---

## 🚀 Quick Start (Dockerization)

The entire environment is containerized. You do not need to manage local Python environments or database dependencies.

**1. Clone the repository:**
```
git clone [https://github.com/valiyevoktay-cmd/caspian-alpha-hft-microstructure-tracker.git](https://github.com/valiyevoktay-cmd/caspian-alpha-hft-microstructure-tracker.git)
cd caspian-alpha-hft-microstructure-tracker
```
**2. Launch the containerized pipeline:**
```
docker compose up -d --build
```
**3. Access the Dashboard & Run Research:**
UI Terminal: Navigate your browser to http://localhost:8501.

Macro Simulation: To test the Liquidity Vacuum detector on live data, open a secondary terminal and run:
```
python run_research.py
```
To stop the background data ingestion daemon, run:
```
docker compose down
```
---
**🧪 CI/CD & Testing**
This project embraces DevOps best practices to ensure mathematical and operational integrity.Unit Testing (pytest): The tests/ directory contains localized tests that feed synthetic L2 snapshots into the engine to validate the determinism of the $\mathcal{O}(1)$ state machine and OFI mathematics.Run locally: pytest tests/ -vAutomated Pipelines: A GitHub Actions workflow is triggered on every push and pull_request. The pipeline spins up a clean Ubuntu container, installs dependencies, and executes the test suite.Regression Control: This automated process ensures that any architectural refactoring does not introduce regressions into the signal logic.
