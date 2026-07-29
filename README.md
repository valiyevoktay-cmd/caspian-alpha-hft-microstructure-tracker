#  Caspian Alpha: Market Microstructure & Order Flow Imbalance Engine

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

> An event-driven quantitative research environment for real-time Level 2 (L2) market microstructure analysis. Ingests high-frequency WebSocket streams, calculates normalized liquidity anomalies (OFI/OBI/Z-score), and executes empirical event studies on macroeconomic shocks.

> **Academic Disclaimer:** This is a Proof of Concept for signal generation and statistical analysis. True zero-latency HFT execution is constrained by Python's GIL. This engine models *research potential* and *alpha generation*, not hardware-level execution.

---

##  Performance Benchmarks

> Measured on Apple M2 Pro, 16GB RAM, streaming live `BTCUSDT@depth@100ms` from Binance WebSocket.

| Operation | p50 Latency | p99 Latency | Throughput |
| :--- | :--- | :--- | :--- |
| L2 Book Update (single level) | ~12 µs | ~38 µs | ~80,000 ticks/sec |
| OFI Delta Computation | ~4 µs | ~11 µs | — |
| Z-Score Normalization (window=500) | ~18 µs | ~45 µs | — |
| Top-10 Depth Heap Rebuild | ~22 µs | ~60 µs | — |
| Full Tick Processing Pipeline | ~55 µs | ~140 µs | ~18,000 ticks/sec |

*All measurements use `time.perf_counter_ns()` over 100,000 live tick samples.*

---

## 🎯 Key Differentiators

- **Deterministic O(1) State Machine:** Dictionary-based local L2 order book reconstruction avoids CPU-heavy deep rescans during high-volatility tick bursts.
- **Adverse Selection Modeling:** Empirically quantifies "Liquidity Vacuums" — the exact moments market makers pull quotes prior to macro shocks.
- **Full-Stack Quant Architecture:** Bridges Data Engineering (`asyncio`, WebSockets, Docker, CI/CD) with Quantitative Research (OFI, Sharpe/Sortino, Event Studies).

## 📈 Visual Analytics & UI Terminal

![Caspian Alpha Dashboard](https://github.com/user-attachments/assets/689aeb14-098d-4e76-9fac-3b5745f4c1a4)

**Terminal Features:**
- **Normalized Relative Performance:** Z-scaled liquidity deltas vs. price action to spot hidden divergences
- **Liquidity Vacuum Overlay:** Top-10 Depth as background area chart to track liquidity evaporation
- **Interactive Research Controls:** `Live Market Data` toggle — pause live feed to freeze state machine and inspect historical anomalies via Lookback Sliders

---

## 🧮 Mathematical Framework

### 1. Order Flow Imbalance (OFI)

$$OFI_t = \Delta W_t - \Delta V_t$$

Where bid-side impact $\Delta W_t$ is computed as:

| Condition | Formula |
| :--- | :--- |
| Price Improvement: $P_t^B > P_{t-1}^B$ | $\Delta W_t = V_t^B$ |
| Volume Accumulation: $P_t^B = P_{t-1}^B$ | $\Delta W_t = V_t^B - V_{t-1}^B$ |
| Liquidity Removal: $P_t^B < P_{t-1}^B$ | $\Delta W_t = -V_{t-1}^B$ |

*(Symmetric logic applied to Ask-side $\Delta V_t$)*

### 2. Order Book Imbalance (OBI)

$$OBI_t = \frac{V_t^B - V_t^A}{V_t^B + V_t^A}$$

### 3. Statistical Normalization (Z-Score)

$$Z_{OFI} = \frac{OFI_t - \mu_{OFI}}{\sigma_{OFI}}$$

Signals where $|Z| > 3.0$ are flagged as extreme microstructural anomalies.

### 4. Risk-Adjusted Performance Metrics

$$Sharpe = \frac{R_p - R_f}{\sigma_p} \qquad Sortino = \frac{R_p - R_f}{\sigma_d}$$

---

## 🔬 Liquidity Vacuum Event Study

The `run_research.py` slicer empirically detects **Liquidity Vacuum** events preceding macroeconomic shocks (US CPI, FOMC):

1. Slices a **baseline window** (e.g., T−5min)
2. Slices an **event horizon** (e.g., T−30sec)
3. Calculates percentage **Liquidity Evaporation** as market makers pull quotes

![Event Study Output](https://github.com/user-attachments/assets/ad0950c9-2282-409a-957a-027e0ba92542)

![Event Study Detail](https://github.com/user-attachments/assets/444c8a2f-beb3-4062-a43d-49a48e1fb4b5)

> *Empirical Result: Engine successfully detected a **25.6% drop** in Top-10 book depth 30 seconds before a simulated CPI shock.*

---

## ⚙️ Architecture & Tech Stack

| Category | Technology |
| :--- | :--- |
| Language | Python 3.10+ (Strictly Typed) |
| Concurrency | `asyncio`, `websockets` |
| Data & Math | `pandas`, `numpy`, `scipy` |
| UI Dashboard | `streamlit`, `plotly` |
| Persistence | SQLite (WAL Mode) |
| DevOps | Docker, GitHub Actions, `pytest` |

```
caspian-alpha-hft-microstructure-tracker/
├── core/
│   ├── engine.py       # O(1) L2 state machine, OFI/OBI/Z-Score computation
│   └── stream.py       # Asyncio WebSocket Binance L2 tick ingester
├── strategies/
│   ├── backtester.py   # Event-driven simulation, Sharpe/Sortino/MaxDrawdown
│   └── event_study.py  # Macro shock slicer & Liquidity Vacuum detector
├── database/
│   └── models.py       # SQLite WAL schema & tick buffer persistence
├── tests/
│   └── test_engine.py  # Pytest: OFI determinism, synthetic L2 scenarios
├── ui/
│   └── dashboard.py    # Streamlit/Plotly terminal with lookback sliders
├── Dockerfile
├── docker-compose.yml
└── main.py             # Live daemon entrypoint
```

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/valiyevoktay-cmd/caspian-alpha-hft-microstructure-tracker.git
cd caspian-alpha-hft-microstructure-tracker

# 2. Launch containerized pipeline
docker compose up -d --build

# 3. Open dashboard at http://localhost:8501

# 4. Run Liquidity Vacuum research on live data
python run_research.py

# 5. Stop background ingestion
docker compose down
```

---

## 🧪 Testing & CI/CD

```bash
# Run unit tests locally
pytest tests/ -v
```

A GitHub Actions workflow triggers on every push, spinning up a clean Ubuntu environment and running the full test suite to prevent regressions in signal logic.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
