# MarketAgent - AI-Powered Market Intelligence with Telegram

An automated market analysis system that fetches real-time data from Finnhub, curates the most valuable insights, uses OpenAI's GPT-4o to generate professional market reports, and delivers them to Telegram in real-time.

## 🚀 Features

- 📊 **Real-Time Data Collection**: Fetches quotes, today's news (10 per stock), market news, company profiles, and financials from Finnhub API
- 🤖 **AI-Powered Analysis**: Uses OpenAI's GPT-4o to generate insightful, narrative market reports with actionable context
- 📰 **Intelligent News Curation**: 
  - Today's company-specific news (10 most recent per stock)
  - General market news filtered for relevance (last 24h)
  - Excludes lifestyle/non-market content automatically
- 📱 **Telegram Integration**: Auto-sends reports to Telegram group with dedicated topics:
  - Daily Reports topic: Stock summary + AI analysis (split into 2 messages to avoid truncation)
  - Market News topic: Formatted news with sources and links
- 🎯 **Smart Data Curation**: Per-stock briefings with price changes and relevant news
- ⏰ **Market Session Detection**: Automatically identifies market status
- 💾 **Full Pipeline Automation**: Single command runs entire workflow (fetch → analyze → send)

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
- `requests` - HTTP library for Telegram Bot API

### 2. Configure API Keys

Create a `.env` file in the project root (same level as `README.md`):

```env
# Finnhub API
FINNHUB_API_KEY=your_finnhub_api_key_here

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_group_chat_id_here
TELEGRAM_TOPIC_DAILY_REPORTS=2
TELEGRAM_TOPIC_MARKET_NEWS=4
```

**Get your API keys:**
- **Finnhub**: Sign up at https://finnhub.io/register (free tier: 60 calls/minute)
- **OpenAI**: Get your key at https://platform.openai.com/api-keys
- **Telegram Bot**:
  1. Message [@BotFather](https://t.me/botfather) on Telegram
  2. Create a new bot with `/newbot`
  3. Copy the token provided
  4. Add bot to your Telegram group
  5. Get chat ID by sending a message and checking updates via `https://api.telegram.org/bot<TOKEN>/getUpdates`
  6. Topic IDs are visible in Telegram group settings

⚠️ **Important**: The `.env` file is gitignored and should never be committed to version control.

### 3. Configure Stock Symbols

Edit the `SYMBOLS` list in [engine/finnhub_client.py](engine/finnhub_client.py) (shared by the snapshot, the news site and Telegram):

```python
SYMBOLS = ["QQQ", "TSLA", "AMD", "GOOG", "NVDA", "MSTR", "SMCI"]
```

### 4. Create Telegram Group with Topics

1. Create a Telegram group (supergroup)
2. Enable Topics in group settings
3. Create two topics:
   - **Daily Reports** (get topic ID, set as `TELEGRAM_TOPIC_DAILY_REPORTS`)
   - **Market News** (get topic ID, set as `TELEGRAM_TOPIC_MARKET_NEWS`)
4. Add your bot to the group as admin

### 5. News Site (GitHub Pages)

A static page (http://mitko.mk/MarketAgent/) with these tabs:
- **News** (entry page): all watchlist + market news of the last 24h in a 3-column card grid with
  thumbnails. Duplicate / >90% similar stories are grouped into one card (main headline +
  "Similar coverage" list). Ticker filters show each stock's daily move.
- **Watchlist**: one card per stock with the same figures as the Telegram *Company Info*
  post (price, change, today's and 52-week range, open, previous close, P/E, market cap, beta,
  10-day average volume), plus analyst consensus, EPS beat/miss for the last 4 quarters, insider
  buying/selling (90 days); upcoming earnings below the cards. **Details →** opens a company page with:
  analyst ratings (4 months), earnings history, quarterly financials (from SEC filings), insider
  trades (Form 4) and monthly insider sentiment (MSPR), latest news, SEC filings, peers,
  lobbying spend, H-1B hiring and US government contracts.
- **US market**: market status (header badge), major indices and the 11 sectors (via ETFs),
  large companies reporting earnings this week, IPO calendar, market holidays.
- **Economy**: Treasury bond, commodity, US dollar, crypto and volatility proxies (ETFs, since
  the free plan has no direct yields/forex/commodities) and the FDA advisory committee calendar.
- **Daily report**: the AI report with the day's stock moves, plus past reports.

It is rebuilt every 15 minutes by [.github/workflows/news-pages.yml](.github/workflows/news-pages.yml)
(Finnhub only, no OpenAI calls). Quotes, market status and news are fetched every run (~45 calls);
company details, calendars and metrics change slowly and are cached for 6–24 hours
(`.cache/*.json`, persisted with `actions/cache`). All Finnhub calls go through a rate limiter
(50/minute, the free tier allows 60), so a run that refreshes everything takes ~2 minutes and a
normal run well under one. The site writes `news.json`, `market.json` and `companies/<SYM>.json`.

**Thumbnails.** Finnhub often returns only a publisher logo (most Yahoo items), so the site
builder reads the article's preview image (`og:image`) for stories without one
([engine/thumbnails.py](engine/thumbnails.py)). Results are cached between runs with
`actions/cache` (`.cache/thumbnails.json`), so each run only checks new articles. Images used
by 3+ unrelated stories are treated as publisher defaults and skipped.

**Reports and the `data` branch.** The daily job saves each AI report as JSON to the
`data` branch (`reports/<date>-<session>.json` + `reports/index.json`, see
[engine/report_store.py](engine/report_store.py)) and triggers a site rebuild. The news job
checks out `data` and copies the reports into the page. Code stays on `main`; generated
data stays on `data`.

One-time setup:
1. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Make sure the `FINNHUB_API_KEY` repository secret exists (already used by the daily job).
3. Run the workflow once from the **Actions** tab (*News Site (GitHub Pages)* → *Run workflow*).
   The page URL appears in the run summary (`https://<user>.github.io/<repo>/`).

Build locally:

```powershell
python -m engine.build_news_site --out site                       # live from Finnhub
python -m engine.build_news_site --out site --snapshot data/snapshots/<file>.json   # offline
python -m engine.report_store --data-dir data-store                # save latest AI report like CI does
python -m engine.build_news_site --out site --data-dir data-store  # include stored reports
python -m http.server 8000 -d site                                 # open http://localhost:8000
```

How grouping works ([engine/news_grouping.py](engine/news_grouping.py)):
- Same URL or identical headline → one item (tickers merged, e.g. `TSLA` + `GOOG`).
- Headlines ≥ 90% similar (character similarity, also with words sorted) → same story.
- Identical summaries also group, but only if the headlines are ≥ 60% similar
  (publishers reuse boilerplate summaries for different articles).
- Headlines with different numbers (`$2.4B fund…` vs `$7.2B fund…`) are never grouped.
- Text-only: the same story written with completely different words stays separate.

The Telegram *Market News* post uses the same grouping (`· +N similar`).

**AI input.** The snapshot keeps *all* company news of the last 24h. Before the OpenAI call,
[engine/data_curator.py](engine/data_curator.py) groups duplicates and sends the top
`NEWS_PER_STOCK` (5) distinct stories per stock (most-covered first, then newest), so the
prompt size and cost stay the same no matter how much news Finnhub returns.

**Failures.** If the AI step fails (e.g. no OpenAI credits), the pipeline still sends the
stock summary, Market News, Company Info and earnings alerts to Telegram, then exits non-zero
so the GitHub run is marked failed.

## 🎯 Usage

### Quick Start (Full Automated Pipeline)

Run the complete workflow in one command:

```powershell
python run_full_pipeline.py
```

**What it does (sequentially):**
1. ✅ **Step 1**: Fetches latest market data from Finnhub
2. ✅ **Step 2**: Generates AI analysis report with OpenAI
3. ✅ **Step 3**: Sends formatted reports to Telegram

**Output example:**
```
============================================================
📊 MARKETAGENT FULL PIPELINE
============================================================

🚀 STEP: 1/3 - Fetch Market Data
✅ Market snapshot saved with 50 news items + 18 market news items

🚀 STEP: 2/3 - Generate AI Report
✅ AI report generated successfully

🚀 STEP: 3/3 - Send Telegram Reports
📤 Message 1/2 posted to Daily Reports ✅
📤 Message 2/2 posted to Daily Reports ✅
📤 Market News posted ✅
```

### Step-by-Step Manual Execution

#### Step 1: Fetch Market Data

Collect comprehensive market data from Finnhub:

```powershell
python -m finnhub_scripts.fetch_and_store
```

**What it does:**
- Fetches real-time quotes for configured symbols
- Retrieves company profiles (name, industry, market cap)
- Collects key financials (P/E ratio, 52-week ranges, beta)
- Gets **today's company news (10 most recent per stock)**
- Fetches **general market news from last 24 hours**
- Filters market news for relevance (excludes lifestyle, personal finance)
- Detects current market session
- Saves snapshot to `data/snapshots/market_snapshot-<timestamp>.json`

**Output example:**
```
📥 Fetching market data from Finnhub...
  → Fetching TSLA...
  → Fetching AMD...
  ...
✅ Market snapshot saved to data/snapshots/market_snapshot-20251225-120000.json
   Stocks: 6
   News items: 50 (10 per stock)
   Market news items (24h): 18
```

#### Step 2: Generate AI Report

Generate an AI-powered market analysis report:

```powershell
python -m engine.run_ai_report
```

**What it does:**
- Loads the latest market snapshot
- Curates data (organizes news by stock)
- Formats data into AI-friendly structure
- Sends to OpenAI GPT-4o with professional analyst prompt
- Generates comprehensive narrative report
- Saves to `reports/ai_report-<timestamp>.txt`

**Output example:**
```
🎯 AI Market Report Generator

📂 Loading latest market snapshot...
   Loaded: market_snapshot-20251225-120000.json
🤖 Curating data for AI analysis...
📝 Formatting data for ChatGPT prompt...
🚀 Sending to ChatGPT (GPT-4o)...

✅ AI report generated successfully!
   📄 Saved to: reports/ai_report-20251225-120000.txt
```

#### Step 3: Send Reports to Telegram

Send formatted reports to Telegram topics:

```powershell
python -m engine.send_telegram_report
```

**What it sends:**

**Daily Reports Topic (2 messages):**
1. **Message 1**: Stock summary with color indicators + first part of AI analysis
   ```
   Today's Stock Moves:
   🟢 TSLA $485.40 | -0.03%
   🟢 AMD $215.04 | +0.07%
   🔴 NVDA $188.61 | -0.32%
   
   [Executive Summary, Notable Movers, Key News & Catalysts sections...]
   ```

2. **Message 2**: Market Insights + Risks + Opportunities sections

**Market News Topic:**
   ```
   [12:30] Bloomberg: AI Chip Demand Surges (https://...)
   [11:45] Reuters: Federal Reserve Signals Rate Cuts Ahead (https://...)
   [10:15] CNBC: Tesla Beats Q3 Estimates (https://...)
   ```

## 📁 Project Structure

```
MarketAgent/
├── finnhub_scripts/
│   ├── __init__.py
│   └── fetch_and_store.py           # Snapshot builder (python -m finnhub_scripts.fetch_and_store)
│                                     # - Fetches quotes, profiles, financials
│                                     # - Today's news (10 per stock)
│                                     # - Market news (24h, filtered)
├── engine/
│   ├── __init__.py
│   ├── finnhub_client.py             # SYMBOLS + lazy Finnhub client
│   ├── news_fetcher.py               # Company/market news fetch + relevance filter
│   ├── news_grouping.py              # Duplicate / similar news grouping
│   ├── market_data.py                # Quotes, metrics, earnings (Telegram + site)
│   ├── company_data.py               # Insiders, analysts, financials, filings, lobbying, H-1B...
│   ├── market_overview.py            # Indices, sectors, macro ETFs, IPOs, holidays, FDA calendar
│   ├── slow_cache.py                 # TTL cache for slowly changing Finnhub data
│   ├── build_news_site.py            # Builds site/ (index.html + news.json + reports)
│   ├── thumbnails.py                 # og:image lookup for missing thumbnails (cached)
│   ├── report_store.py               # Saves AI reports as JSON to the data branch
│   ├── data_curator.py               # Data curation for AI
│   │                                 # - Per-stock briefings
│   │                                 # - News organization
│   ├── prompts.py                    # AI system prompts
│   │                                 # - Report structure guidelines
│   │                                 # - Tone and content rules
│   ├── report_engine.py              # Report utilities
│   │                                 # - Latest snapshot loader
│   ├── run_ai_report.py              # AI report generator
│   │                                 # - OpenAI GPT-4o integration
│   ├── telegram_sender.py            # Telegram bot API client
│   │                                 # - Message posting to topics
│   ├── telegram_formatter.py         # Telegram output formatting
│   │                                 # - Stock summary with emojis
│   │                                 # - AI report splitting (2 parts)
│   │                                 # - Market news with links
│   └── send_telegram_report.py       # Telegram orchestrator
│                                     # - Loads snapshot + AI report
│                                     # - Formats and sends all messages
├── contracts/
│   ├── __init__.py
│   ├── market_report.py              # Data contracts
│   └── market_snapshot.py
├── data/
│   └── snapshots/                    # Market snapshots (JSON)
│       └── market_snapshot-*.json
├── reports/                          # AI-generated reports
│   └── ai_report-*.txt
├── web/
│   └── index.html                    # News page (cards), deployed to GitHub Pages
├── tests/
│   ├── test_news_grouping.py         # python -m unittest discover -s tests -t .
│   ├── test_pipeline_parts.py        # curation, report storage, site builder
│   └── test_mock_run.py              # Test utilities
├── .env                              # API keys (gitignored - create this!)
├── .gitignore
├── requirements.txt
├── run_full_pipeline.py              # Complete automation script
├── test_send_ai_report.py            # Test Telegram sender
└── README.md
```

## 📊 Example Output

### Generated AI Report Structure

The AI creates professional narrative reports with these sections:

- **📊 Executive Summary** - Market overview and key themes
- **🔥 Notable Movers** - Stock analysis with explanations
- **📰 Key News & Catalysts** - Important news grouped by theme
- **💡 Market Insights** - Patterns and sector trends
- **⚠️ Risks to Watch** - Potential disruptions
- **✅ Opportunities** - Bullish setups and value areas

### Example Report (December 24, 2025)

```
📊 Executive Summary

The market closed with a mixed sentiment today, as investors navigated 
through a blend of sector-specific performances and broader economic 
indicators. While the S&P 500 is nearing record highs, individual 
stocks displayed varied performances.

🔥 Notable Movers

Tesla: Closed at $485.40, down 0.03%. The decline comes amid 
mixed sentiment surrounding valuation and margin pressures.

NVIDIA: Fell by 0.32% to $188.61. The decline reflects market 
assessment of trade tensions and increased competition in AI chips.
```

[See full examples in the `reports/` directory]

## 📝 Customization

### Change Stock Symbols

Edit [engine/finnhub_client.py](engine/finnhub_client.py):

```python
SYMBOLS = ["QQQ", "TSLA", "AMD", "GOOG", "NVDA", "MSTR", "SMCI"]
```

### Change News Fetching Parameters

In [engine/news_fetcher.py](engine/news_fetcher.py):

```python
# Fetch today's news (days=1), 10 items per stock
fetch_company_news(symbol, days=1, limit=10)

# Fetch market news from last 24 hours
fetch_market_news(hours=24)
```

### Customize Market News Filtering

In [engine/news_fetcher.py](engine/news_fetcher.py), edit `is_relevant_market_news()` and the keyword sets:

```python
POSITIVE_KEYWORDS = ["gdp", "cpi", "fed", "earnings", "ai", "crypto"]
NEGATIVE_KEYWORDS = ["lifestyle", "career advice", "ice cream"]
```

### Change AI Model or Style

Edit [engine/run_ai_report.py](engine/run_ai_report.py):

```python
model="gpt-4o"           # Best quality (default)
# model="gpt-4-turbo"    # Good balance, lower cost
# model="gpt-3.5-turbo"  # Fastest, cheapest
```

Edit [engine/prompts.py](engine/prompts.py) to modify:
- Report structure and sections
- Writing tone (formal/casual)
- Analysis angles and focus areas
- Content guidelines

### Adjust Telegram Message Formatting

Edit [engine/telegram_formatter.py](engine/telegram_formatter.py):

```python
# Stock summary emoji: 🟢 (gain), 🔴 (loss), ⚪ (neutral)
# Market news format: [HH:MM] Source: Headline(link)
# Modify colors, emoji, or text formatting as needed
```

### Add Custom Finnhub Data

In [finnhub_scripts/fetch_and_store.py](finnhub_scripts/fetch_and_store.py):
1. Add new Finnhub API calls (see https://finnhub.io/docs/api)
2. Update [engine/data_curator.py](engine/data_curator.py) to process new data
3. Modify AI prompt in [engine/prompts.py](engine/prompts.py) if needed

## ⚙️ Scheduling (Automation)

### Windows Task Scheduler

Create a scheduled task to run the pipeline daily:

```powershell
# PowerShell as Administrator
$TaskAction = New-ScheduledTaskAction -Execute "python" -Argument "C:\workspace\MarketAgent\run_full_pipeline.py" -WorkingDirectory "C:\workspace\MarketAgent"
$TaskTrigger = New-ScheduledTaskTrigger -Daily -At 4:00PM
Register-ScheduledTask -Action $TaskAction -Trigger $TaskTrigger -TaskName "MarketAgent" -Description "Daily AI market report"
```

### Linux/Mac Cron

Add to crontab:

```bash
0 16 * * * cd /path/to/MarketAgent && python run_full_pipeline.py
```

This runs at 4:00 PM (16:00) daily.

## 📈 API Costs & Rate Limits

### Finnhub (Free Tier)
- **60 API calls/minute** limit
- Free tier includes: quotes, profiles, financials, news, general news
- Consider upgrading for higher limits: https://finnhub.io/pricing

### OpenAI API
- **GPT-4o**: ~$2.50/$10 per 1M input/output tokens (~$0.02-0.05 per report)
- **GPT-4-turbo**: ~$10/$30 per 1M tokens
- **GPT-3.5-turbo**: ~$0.50/$1.50 per 1M tokens
- Monitor usage: https://platform.openai.com/usage

### Telegram Bot API
- Completely free - no rate limits for bots

## 🐛 Troubleshooting

### "API key not found" errors
- Check `.env` file exists in project root
- Verify format: `KEY_NAME=value` (no spaces/quotes)
- Confirm API keys are valid and not expired

### "Chat not found" (Telegram)
- Verify `TELEGRAM_CHAT_ID` is negative (e.g., `-1003634803551`)
- Ensure bot is added to the group as admin
- Check topic IDs match group's actual topics

### "No module named 'engine'"
- Run as module: `python -m engine.run_ai_report`
- Not as script: `python engine/run_ai_report.py`

### "Message is too long" (Telegram)
- Report is split into 2 messages automatically
- If still failing, AI report may be extremely long
- Reduce stock count or news items per stock

### Rate limit errors
- Add delays between Finnhub requests
- Reduce number of stocks in `SYMBOLS`
- Upgrade Finnhub plan

## 🚀 Future Enhancements

- **Email Delivery**: Send reports via email
- **Web Dashboard**: Flask/FastAPI frontend for viewing reports
- **Chart Generation**: Add price/volume charts with matplotlib
- **Sentiment Analysis**: NLP-based news sentiment scoring
- **Historical Tracking**: Compare to previous days/weeks
- **Sector Analysis**: Group analysis by industry
- **Discord Integration**: Alternative messaging platform
- **Portfolio Tracking**: Monitor specific holdings
- **Advanced Alerts**: Price targets, volume spikes, volatility
- **Multi-timeframe**: Intraday, daily, weekly analysis

## 🤝 Contributing

Contributions welcome! Areas for enhancement:
- Additional data sources (Yahoo Finance, Alpha Vantage)
- Alternative AI models (Claude, Gemini)
- Enhanced error handling and logging
- Unit tests and CI/CD pipelines

## 📄 License

MIT License - Use freely for personal or commercial projects.

## ⚠️ Disclaimer

This tool is for **informational purposes only**. It does not provide financial advice. Always conduct your own research and consult a qualified financial advisor before making investment decisions. Past performance does not guarantee future results. Use at your own risk.

---

**Built with ❤️ using Finnhub API, OpenAI GPT-4o, and Telegram Bot API**

*Last Updated: December 25, 2025*
