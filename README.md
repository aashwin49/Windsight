# Windsight

**A day-ahead wind generation forecast accuracy dashboard for Great Britain (GB).**

Windsight helps an energy utility procurement team review how historical wind generation forecasts compared with actual generation at delivery time. It selects the forecast publication that would have been available at a configurable decision cutoff, aligns it with actual generation, and presents forecast errors and accuracy metrics in a dashboard.

<p align="center">
  <a href="https://windsight-delta.vercel.app"><strong>Open the live dashboard</strong></a>
  ·
  <a href="https://windsight-api-szax.onrender.com/docs"><strong>Explore the API</strong></a>
  ·
  <a href="https://github.com/aashwin49/Windsight"><strong>GitHub repository</strong></a>
</p>

## Live deployment

| Service | Link |
|---|---|
| Windsight dashboard | https://windsight-delta.vercel.app |
| Backend API | https://windsight-api-szax.onrender.com |
| Interactive API documentation (Swagger) | https://windsight-api-szax.onrender.com/docs |
| Source code | https://github.com/aashwin49/Windsight |

The frontend is hosted on Vercel and the FastAPI backend is hosted on Render.

## The business problem

Wind generation is variable, so day-ahead forecasts will not always match the generation that is ultimately delivered. A procurement team needs a consistent way to assess the size and direction of those deviations using only the forecast information that would have been available when a decision was made.

Comparing actual generation with the latest forecast publication can create hindsight bias: later forecast updates may not have been available at the original decision time. Windsight addresses this by selecting forecast versions using a configurable decision cutoff.

## What the application does

- Displays hourly wind generation forecasts alongside actual generation.
- Selects the latest eligible forecast publication available at the configured decision cutoff.
- Supports a configurable cutoff hour, using UK local time (`Europe/London`).
- Calculates forecast error and summary accuracy metrics.
- Shows forecast publication history and missing-data information.
- Preserves missing values as missing rather than treating them as zero.
- Provides API endpoints for dashboard data, generation, accuracy and forecast history.

## Dashboard

Open the deployed application: **[windsight-delta.vercel.app](https://windsight-delta.vercel.app)**.

The dashboard is intended to support review and analysis. It is not a live forecasting engine, automated trading system or procurement recommendation engine.

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI, Uvicorn |
| Data | Elexon BMRS API, JSON |
| Date and time handling | `Europe/London` timezone; UTC source timestamps |
| Deployment | Vercel (frontend), Render (backend) |
| Containerisation | Docker, Docker Compose |
| Testing | Python backend test suite; frontend production build |

## Architecture

```text
Elexon BMRS API
   ├── FUELHH: half-hourly actual wind generation
   └── WINDFOR: hourly wind forecast publications
                  |
                  v
          Raw JSON extracts
                  |
                  v
       Data processing and alignment
       - actuals aggregated to hourly
       - forecast versions retained
       - cutoff-based forecast selection
                  |
                  v
       Processed January 2026 dataset
                  |
                  v
          FastAPI backend
       - dashboard endpoint
       - generation endpoint
       - accuracy endpoint
       - forecast history endpoint
                  |
                  v
           React + Vite UI
                  |
                  v
       Deployed Windsight dashboard
```

## Data sources and coverage

Windsight uses two datasets from the **Elexon BMRS API**:

- **FUELHH** — half-hourly generation by fuel type. The project filters this dataset to actual wind generation (`fuelType=WIND`).
- **WINDFOR** — wind generation forecast publications, including publication time, delivery time and forecast generation.

Official Elexon references:

- [FUELHH stream endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- [WINDFOR stream endpoint](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
- [Elexon API Swagger specification](https://data.elexon.co.uk/swagger/v1/swagger.json)

### Dataset used

The current analysis covers **1–31 January 2026**:

| Data | Extracted records | Resolution |
|---|---:|---|
| FUELHH actual wind generation | 1,488 | Half-hourly |
| WINDFOR records associated with January delivery | 18,080 | Hourly delivery intervals, multiple publications |
| Unique January delivery hours | 744 | Hourly |

The WINDFOR extraction returned 36,208 records across the wider publication-time query window; 18,080 of those records have January 2026 delivery timestamps. The number of forecast publications varies by delivery hour.

Raw extracts are retained separately from the processed output:

- `backend/raw/actual_generation.json`
- `backend/raw/forecast_generation.json`
- `backend/processed/january_2026_processed.json`

## Forecast selection logic

A delivery hour may have multiple WINDFOR forecast publications. These are different forecast versions, not duplicate rows.

For each delivery interval, Windsight:

1. Converts the delivery timestamp to `Europe/London`.
2. Calculates the configured cutoff on the previous local calendar day.
3. Converts the cutoff to UTC.
4. Keeps only forecast publications with `publishTime` at or before the cutoff.
5. Selects the eligible publication with the latest `publishTime`.

The default cutoff is **12:00 noon UK local time on the day before delivery**. The cutoff hour is configurable. Using `Europe/London` accounts for GMT/BST changes, while the source timestamps are UTC.

For the January 2026 dataset, the noon previous-day rule selected a forecast for all 744 delivery hours. This is a result for this dataset and assumption, not a guarantee for other periods.

**Important:** The noon cutoff is a working analytical assumption, not a confirmed procurement policy. It should be validated with the intended users before operational use.

## Forecast accuracy metrics

Forecast error is defined as:

```text
error = forecast - actual
```

- Positive error: the forecast was higher than actual generation (over-forecast).
- Negative error: the forecast was lower than actual generation (under-forecast).

Metrics are calculated using valid forecast/actual pairs:

| Metric | Definition | Interpretation |
|---|---|---|
| MAE | Mean of absolute errors | Typical absolute forecast deviation, in MW |
| RMSE | Square root of mean squared errors | Gives larger errors greater influence, in MW |
| Bias | Mean signed error | Positive indicates average over-forecast; negative indicates average under-forecast, in MW |
| WAPE | Sum of absolute errors ÷ sum of absolute actuals × 100 | Aggregate absolute error relative to actual generation, as a percentage |

Missing forecasts and actuals are not converted to zero. They are excluded from valid metric pairs and surfaced through the relevant interval/missing-data counts. A genuine zero-generation observation remains a valid observation.

These metrics describe forecast deviations. They do not directly quantify imbalance exposure, procurement costs, financial savings or the quality of a particular trading decision.

## Backend API

Base URL: `https://windsight-api-szax.onrender.com`

Interactive documentation: **[Swagger UI](https://windsight-api-szax.onrender.com/docs)**

| Endpoint | Purpose |
|---|---|
| `GET /api/dashboard` | Dashboard data for a delivery date and cutoff hour |
| `GET /api/generation` | Forecast and actual generation series |
| `GET /api/accuracy` | Forecast accuracy metrics |
| `GET /api/forecast-history` | Forecast publication history |

The dashboard request uses the `delivery_date` and `cutoff_hour` query parameters.

## Run locally

### Prerequisites

- Python 3.10 or later (use the version compatible with `backend/requirements.txt`)
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/aashwin49/Windsight.git
cd Windsight
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source venv/bin/activate

# Windows PowerShell
venv\Scripts\Activate.ps1
```

Install dependencies and start FastAPI:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend: `http://localhost:8000`  
API documentation: `http://localhost:8000/docs`

### 3. Start the frontend

Open a second terminal:

```bash
cd Windsight/frontend
```

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Then install dependencies and start Vite:

```bash
npm install
npm run dev
```

Open the local frontend URL printed by Vite (typically `http://localhost:5173`).

## Run with Docker

From the repository root:

```bash
docker compose up --build
```

With the current Compose port mapping:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

To stop the containers:

```bash
docker compose down
```

## Testing and validation

The completed project was checked using automated tests and manual validation:

- **22 backend tests passed.**
- Frontend production build completed successfully.
- Manual checks covered dashboard rendering, forecast selection at the noon cutoff, a midnight cutoff, independently calculated metrics, chart/table consistency, backend-unavailable handling, empty-date API responses and loading behaviour.
- Docker Compose configuration was validated and the application was run locally with Docker during project verification.

A representative API check for 12 January 2026 with a 12:00 cutoff returned 24 valid hourly pairs and no missing forecast or actual values:

| Metric | Result |
|---|---:|
| MAE | 4,688.8 MW |
| RMSE | 5,080.4 MW |
| Bias | +4,688.8 MW |
| WAPE | 32.44% |

This is one date/cutoff example, not a summary of January-wide performance.

## Assumptions and limitations

1. **Cutoff assumption:** Noon UK local time on the previous day is a working assumption and needs procurement stakeholder confirmation.
2. **Limited period:** The current dataset covers January 2026 only; it does not establish seasonal or year-round performance.
3. **Wind only:** The project evaluates wind generation, not all renewable generation or the full GB electricity mix.
4. **Different source resolutions:** Actuals are half-hourly and forecasts are hourly. Actuals are aggregated to hourly average MW for comparison.
5. **Metric interpretation:** Accuracy metrics measure forecast deviations but do not calculate financial impact or prove procurement savings.
6. **Historical dataset:** The deployed dashboard analyses the prepared historical dataset; it is not a live forecasting or automated trading platform.
7. **Production readiness:** Live data refresh, operational monitoring, broader data coverage and validation of the cutoff policy would be required before operational procurement use.

## AI tools and development support

AI-assisted tools were used as development support during the project:

- **ChatGPT** — project planning, technical guidance, debugging support, documentation and review.
- **OpenAI Codex** — coding assistance, code review, cleanup and test support.

The project implementation, validation and deployment were reviewed as part of the development workflow. AI tools were used as assistants; they do not replace verification of data, code or business assumptions.

## Future improvements

- Extend the historical dataset beyond January 2026.
- Compare performance across decision cutoffs and longer time periods.
- Add other generation types and weather-related analysis.
- Explore procurement-relevant financial analysis using validated market and imbalance cost data.
- Confirm decision-time and data-comparability assumptions with procurement users.

## Video Demonstration

[**Watch the Complete Windsight Project Demonstration on YouTube**](https://www.youtube.com/watch?v=4ol6y7jXVyE)

The video is divided into two parts:

- **Part 1 – Client Presentation:** Demonstrates the live dashboard, key features, wind generation comparisons, forecast accuracy insights, and business value.
- **Part 2 – Technical Review:** Covers the project architecture, data sources, processing logic, forecast selection methodology, backend and frontend implementation, testing, and deployment.