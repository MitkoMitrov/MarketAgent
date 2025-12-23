# MarketAgent - AI-Powered Market Intelligence

An automated market analysis system that fetches real-time data from Finnhub, curates the most valuable insights, and uses ChatGPT to generate professional market reports.

## Features

- 📊 **Comprehensive Data Collection**: Fetches quotes, news, company profiles, and financials from Finnhub
- 🤖 **AI-Powered Analysis**: Uses ChatGPT (GPT-4o) to generate insightful, easy-to-read market reports
- 📰 **News Integration**: Correlates price moves with recent news catalysts
- 🎯 **Smart Curation**: Selects the most valuable data points for analysis

## Setup

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root with your API keys:

```env
FINNHUB_API_KEY=your_finnhub_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Get your API keys:**
- Finnhub: https://finnhub.io/register
- OpenAI: https://platform.openai.com/api-keys

### 3. Configure Stock Symbols

Edit the `SYMBOLS` list in `finnhub_scripts/fetch_and_store.py`:

```python
SYMBOLS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]
```

## Usage

### Step 1: Fetch Market Data

Collect the latest market data from Finnhub:

```powershell
python -m finnhub_scripts.fetch_and_store
```

This creates a snapshot file in `data/snapshots/`.

### Step 2: Generate AI Report

Generate an AI-powered market analysis report:

```powershell
python -m engine.run_ai_report
```

The report is saved to `reports/ai_report-<timestamp>.txt`.

### One-Step Pipeline

Run both steps sequentially:

```powershell
python -m finnhub_scripts.fetch_and_store; python -m engine.run_ai_report
```

## Project Structure

```
MarketAgent/
├── finnhub_scripts/
│   └── fetch_and_store.py      # Finnhub data fetcher
├── engine/
│   ├── data_curator.py          # Data curation and formatting
│   ├── prompts.py               # AI system prompts
│   ├── report_engine.py         # Report utilities
│   └── run_ai_report.py         # Main AI report generator
├── data/
│   └── snapshots/               # Market snapshots (JSON)
├── reports/                     # Generated AI reports
├── requirements.txt
└── .env                         # API keys (not in git)
```

## Example Output

The AI generates professional market reports with:

- 📊 Executive Summary
- 🔥 Notable Movers with explanations
- 📰 Key News & Catalysts
- 💡 Market Insights
- ⚠️ Risks to Watch
- ✅ Opportunities

## Customization

### Change AI Model

Edit `engine/run_ai_report.py`:

```python
model="gpt-4o"  # or "gpt-4-turbo", "gpt-3.5-turbo"
```

### Modify Report Style

Edit the `SYSTEM_PROMPT` in `engine/prompts.py`.

### Add More Data Points

Extend the Finnhub API calls in `finnhub_scripts/fetch_and_store.py` and update the curation logic in `engine/data_curator.py`.

## Notes

- **API Rate Limits**: Finnhub free tier has rate limits. Consider delays if fetching many symbols.
- **Costs**: OpenAI API charges per token. Monitor usage at https://platform.openai.com/usage
- **Market Hours**: The script detects market sessions (pre-market, regular, after-hours, closed).

## License

MIT
