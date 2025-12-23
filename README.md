# MarketAgent - AI-Powered Market Intelligence

An automated market analysis system that fetches real-time data from Finnhub, curates the most valuable insights, and uses OpenAI's ChatGPT to generate professional, easy-to-read market reports.

## 🚀 Features

- 📊 **Comprehensive Data Collection**: Fetches quotes, news, company profiles, financials (P/E ratios, 52-week ranges, beta, market cap) from Finnhub API
- 🤖 **AI-Powered Analysis**: Uses OpenAI's GPT-4o to generate insightful, narrative market reports with actionable context
- 📰 **News Integration**: Correlates price moves with recent news catalysts and company-specific events
- 🎯 **Smart Data Curation**: Intelligently selects and formats the most valuable data points for AI analysis
- ⏰ **Market Session Detection**: Automatically identifies pre-market, regular hours, after-hours, and closed sessions
- 📈 **Top Movers Analysis**: Identifies biggest gainers, losers, and most volatile stocks with context

## 📦 Setup

### 1. Install Dependencies

Install required Python packages:

```powershell
pip install -r requirements.txt
```

**Dependencies:**
- `finnhub-python` - Finnhub API client
- `python-dotenv` - Environment variable management
- `openai` - OpenAI API client for GPT-4o

### 2. Configure API Keys

Create a `.env` file in the project root (same level as `README.md`):

```env
FINNHUB_API_KEY=your_finnhub_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Get your API keys:**
- **Finnhub**: Sign up at https://finnhub.io/register (free tier available)
- **OpenAI**: Get your key at https://platform.openai.com/api-keys

⚠️ **Important**: The `.env` file is gitignored and should never be committed to version control.

### 3. Configure Stock Symbols

Edit the `SYMBOLS` list in `finnhub_scripts/fetch_and_store.py`:

```python
SYMBOLS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]
```

## 🎯 Usage

### Quick Start (Full Pipeline)

Run both data collection and AI report generation:

```powershell
python -m finnhub_scripts.fetch_and_store; python -m engine.run_ai_report
```

### Step-by-Step

#### Step 1: Fetch Market Data

Collect comprehensive market data from Finnhub:

```powershell
python -m finnhub_scripts.fetch_and_store
```

**What it does:**
- Fetches real-time quotes for configured symbols
- Retrieves company profiles (name, industry, market cap)
- Collects key financials (P/E ratio, 52-week ranges, beta)
- Gets last 7 days of company news (top 5 per stock)
- Detects current market session
- Saves snapshot to `data/snapshots/market_snapshot-<timestamp>.json`

**Output example:**
```
📥 Fetching market data from Finnhub...
  → Fetching TSLA...
  → Fetching AMD...
  ...
✅ Market snapshot saved to data/snapshots/market_snapshot-20251223-012224.json
   Stocks: 6
   News items: 30
```

#### Step 2: Generate AI Report

Generate an AI-powered market analysis report:

```powershell
python -m engine.run_ai_report
```

**What it does:**
- Loads the latest market snapshot
- Curates data (identifies top movers, organizes news by stock)
- Formats data into AI-friendly structure
- Sends to OpenAI GPT-4o with professional analyst prompt
- Generates comprehensive narrative report
- Saves to `reports/ai_report-<timestamp>.txt`

**Output example:**
```
============================================================
🎯 AI Market Report Generator
============================================================

📂 Loading latest market snapshot...
   Loaded: market_snapshot-20251223-012224.json
🤖 Curating data for AI analysis...
📝 Formatting data for ChatGPT prompt...
🚀 Sending to ChatGPT (GPT-4o)...

✅ AI report generated successfully!
   📄 Saved to: reports/ai_report-20251223-012224.txt
   📊 Report length: 3847 characters
```

## 📁 Project Structure

```
MarketAgent/
├── finnhub_scripts/
│   ├── __init__.py
│   └── fetch_and_store.py           # Comprehensive Finnhub data fetcher
│                                     # - Fetches quotes, profiles, financials, news
│                                     # - Error handling per symbol
│                                     # - Market session detection
├── engine/
│   ├── __init__.py
│   ├── data_curator.py               # Smart data curation for AI
│   │                                 # - Identifies top movers/gainers/losers
│   │                                 # - Groups news by stock
│   │                                 # - Formats data for LLM consumption
│   ├── prompts.py                    # AI system prompts
│   │                                 # - Guides ChatGPT report structure
│   │                                 # - Defines tone and content guidelines
│   ├── report_engine.py              # Report utilities
│   │                                 # - Loads latest snapshots
│   │                                 # - Analysis helpers
│   └── run_ai_report.py              # Main AI report generator
│                                     # - OpenAI API integration
│                                     # - End-to-end report pipeline
├── contracts/
│   ├── __init__.py
│   ├── market_report.py              # Data contracts (optional)
│   └── market_snapshot.py
├── data/
│   └── snapshots/                    # Market snapshots (JSON format)
│       └── market_snapshot-*.json    # Timestamped data files
├── reports/                          # Generated AI reports
│   └── ai_report-*.txt               # Timestamped narrative reports
├── tests/
│   └── test_mock_run.py              # Test with mock data
├── .env                              # API keys (gitignored, create this!)
├── .gitignore
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## 📊 Example AI Report Output

The AI generates professional, narrative market reports with structured sections:

### Report Structure:
- **📊 Executive Summary** - High-level overview of market sentiment and key themes (2-3 sentences)
- **🔥 Notable Movers** - Detailed analysis of top gainers and losers with explanations tied to news catalysts
- **📰 Key News & Catalysts** - Summary of important news driving market moves, grouped by theme
- **💡 Market Insights** - Broader patterns, sector trends, and technical observations
- **⚠️ Risks to Watch** - Potential disruptors and concerns investors should monitor
- **✅ Opportunities** - Areas showing value, momentum, or interesting setups

### Real Example (Generated December 23, 2025):

```
📊 Executive Summary
The market closed on a positive note today, with a generally upbeat sentiment 
driven by gains in key technology stocks. Tesla (TSLA) and NVIDIA (NVDA) were 
among the top gainers, benefiting from positive market conditions and news of 
strategic advancements.

🔥 Notable Movers
- Tesla Inc (TSLA): Rose by 1.56% to $488.73. Tesla's stock was buoyed by 
  optimism following recent news of being in a buy zone, driven by advancements 
  in its robotaxi technology and favorable court rulings regarding CEO Elon 
  Musk's compensation package.

- NVIDIA Corp (NVDA): Increased by 1.49% to $183.69. NVIDIA's rebound is 
  linked to its strategic positioning in the AI sector despite recent 
  discussions around a potential AI bubble burst.
```

[Full example report available at: reports/ai_report-20251223-012224.txt]

## ⚙️ Customization

### Change Stock Symbols

Edit the `SYMBOLS` list in `finnhub_scripts/fetch_and_store.py`:

```python
SYMBOLS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]  # Add/remove as needed
```

### Change AI Model

Edit `engine/run_ai_report.py` to use different OpenAI models:

```python
model="gpt-4o"           # Best quality, higher cost
# model="gpt-4-turbo"    # Good balance
# model="gpt-3.5-turbo"  # Faster, cheaper
```

### Modify Report Style and Tone

Edit the `SYSTEM_PROMPT` in `engine/prompts.py` to:
- Change report structure and sections
- Adjust writing tone (formal/casual, bullish/neutral)
- Add/remove specific analysis angles
- Modify content guidelines

### Add More Data Points

**In `finnhub_scripts/fetch_and_store.py`:**
- Add more Finnhub API calls (e.g., `recommendation_trends`, `price_target`, `earnings`)
- Reference: https://finnhub.io/docs/api

**In `engine/data_curator.py`:**
- Update `curate_for_ai()` to process new data
- Modify `format_for_prompt()` to include in AI input

### Adjust News Lookback Period

In `finnhub_scripts/fetch_and_store.py`, modify the `fetch_news()` function:

```python
def fetch_news(symbol, days=7):  # Change days parameter (default: 7)
    # ... rest of function
```

## 📝 Important Notes

### API Costs and Rate Limits

- **Finnhub Free Tier**: 
  - 60 API calls/minute
  - Consider adding delays between requests if fetching many symbols
  - Upgrade for higher limits: https://finnhub.io/pricing

- **OpenAI API Costs**: 
  - GPT-4o: ~$2.50/$10 per 1M input/output tokens
  - GPT-4-turbo: ~$10/$30 per 1M tokens
  - GPT-3.5-turbo: ~$0.50/$1.50 per 1M tokens
  - Monitor usage: https://platform.openai.com/usage
  - Each report costs approximately $0.01-0.05 depending on model and data size

### Market Hours Detection

The system automatically detects market sessions based on time:
- **Pre-market**: 4:00 AM - 9:30 AM ET
- **Regular hours**: 9:30 AM - 4:00 PM ET
- **After-hours**: 4:00 PM - 8:00 PM ET
- **Closed**: All other times

*Note: Uses local system time; adjust logic in `fetch_and_store.py` if needed*

### Data Storage

- Snapshots are stored indefinitely in `data/snapshots/`
- Reports are stored indefinitely in `reports/`
- Consider archiving old files periodically to save space

### Error Handling

- Each stock fetch is error-handled independently
- If one stock fails, others continue processing
- Check console output for warnings: `⚠️ Error fetching...`

## 🐛 Troubleshooting

**"FINNHUB_API_KEY not found"** or **"OPENAI_API_KEY not found"**
- Ensure `.env` file exists in project root (same level as `README.md`)
- Check `.env` has correct format: `KEY_NAME=value` (no spaces, no quotes)
- Verify API keys are valid

**"No module named 'engine'"**
- Run scripts as modules: `python -m engine.run_ai_report` (not `python engine/run_ai_report.py`)
- Ensure you're in the project root directory

**"No market snapshot files found"**
- Run `python -m finnhub_scripts.fetch_and_store` first
- Check that `data/snapshots/` directory exists and contains JSON files

**API Rate Limit Exceeded**
- Add delays between Finnhub requests
- Reduce number of symbols in `SYMBOLS` list
- Upgrade Finnhub plan

## 🚀 Future Enhancements

Potential improvements to consider:

- **Telegram/Discord Integration**: Auto-send reports to messaging platforms
- **Scheduled Automation**: Daily/hourly report generation with cron/Windows Task Scheduler
- **Chart Generation**: Add matplotlib charts to visualize price movements
- **Sentiment Analysis**: Analyze news sentiment using NLP
- **Historical Comparison**: Compare today's moves to historical patterns
- **Multi-timeframe Analysis**: Intraday + daily + weekly views
- **Sector Analysis**: Group stocks by sector for broader insights
- **Portfolio Integration**: Track specific portfolios vs market
- **Email Delivery**: Send reports via email automatically
- **Web Dashboard**: Flask/FastAPI frontend for viewing reports

## 🤝 Contributing

Feel free to fork, modify, and enhance! Key areas for contribution:
- Additional data sources (Alpha Vantage, Yahoo Finance)
- Enhanced data visualization
- Alternative AI models (Claude, Gemini)
- Better error handling and logging
- Unit tests and CI/CD

## 📄 License

MIT License - Feel free to use for personal or commercial projects.

## ⚠️ Disclaimer

This tool is for informational and educational purposes only. It does not provide financial advice. Always do your own research and consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.

---

**Built with ❤️ using Finnhub API and OpenAI GPT-4o**
