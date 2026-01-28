# MarketAgent Deployment Checklist

## Project Overview
MarketAgent is an automated market intelligence system that runs twice daily (pre-market at 15:30 UTC, after-market at 22:30 UTC) to fetch market data, generate AI-powered reports, and send them to Telegram.

---

## ✅ Pre-Deployment Verification (Completed)

### Code Quality
- [x] All Python files syntax-checked (22 files)
- [x] All imports resolved (4 packages: finnhub-python, python-dotenv, openai, requests)
- [x] No hardcoded API keys found
- [x] All environment variables properly used with defaults
- [x] Data persistence verified (earnings_2026.json tracked in git)

### Stock Symbols (7 total)
- [x] TSLA (Tesla)
- [x] AMD (Advanced Micro Devices)
- [x] QQQ (Invesco QQQ - Nasdaq)
- [x] GOOG (Google/Alphabet)
- [x] NVDA (NVIDIA)
- [x] MSTR (MicroStrategy)
- [x] SMCI (Super Micro Computer)

### Market Sessions
- [x] Pre-market: 15:30 UTC (15:30 cron)
  - Sends: Daily reports + Market news + Company info + Earnings alerts
- [x] After-market: 22:30 UTC (22:30 cron)
  - Sends: Daily reports + Market news + Company info (no earnings)

### Date Format
- [x] All timestamps: `dd/mm/yyyy hh:mm UTC` (e.g., 28/01/2026 15:30 UTC)
- [x] Earnings dates: `dd/mm/yyyy` format
- [x] Company info header: `Updated: dd/mm/yyyy hh:mm UTC`

### Pipeline Steps (4 total)
1. [x] **Step 1/4**: Fetch market data from Finnhub
   - Fetches: Stock quotes, company profiles, financials, news (10 per stock), market news (24h)
   - Saves to: `data/snapshots/market_snapshot-{timestamp}.json`

2. [x] **Step 2/4**: Generate AI report with OpenAI GPT-4
   - Input: Latest market snapshot
   - Output: `data/reports/ai_report-{timestamp}.txt`

3. [x] **Step 3/4**: Send reports to Telegram (4 topics)
   - Topic 2 (Daily Reports): Stock summary + AI report (split in 2 messages) with session label
   - Topic 4 (Market News): 24h filtered market news with links
   - Topic 71 (Company Info): Current metrics (price, change, high/low, P/E, 52-week range, volume, market cap, beta)

4. [x] **Step 4/4**: Send earnings alerts (pre-market only)
   - Checks: Upcoming earnings in next 7 days
   - Sends to: Topic 79 (Earnings)
   - Includes: Company, date, days until, EPS/revenue estimates

### Telegram Configuration (8 variables)
- [x] TELEGRAM_BOT_TOKEN - Bot authentication
- [x] TELEGRAM_CHAT_ID - Group chat ID
- [x] TELEGRAM_TOPIC_DAILY_REPORTS - Topic 2 for daily reports
- [x] TELEGRAM_TOPIC_MARKET_NEWS - Topic 4 for market news
- [x] TELEGRAM_TOPIC_COMPANY_INFO - Topic 71 for company info
- [x] TELEGRAM_TOPIC_EARNINGS - Topic 79 for earnings alerts

### API Keys (3 required)
- [x] FINNHUB_API_KEY - Market data provider
- [x] OPENAI_API_KEY - AI report generation
- [x] TELEGRAM_BOT_TOKEN - Message delivery (listed above)

---

## 🚀 GitHub Deployment Steps

### Step 1: Create GitHub Repository
```bash
# Initialize git repo and push to GitHub
git init
git add .
git commit -m "Initial commit: MarketAgent with GitHub Actions automation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/MarketAgent.git
git push -u origin main
```

### Step 2: Add GitHub Secrets
Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add all 8 secrets:
1. **FINNHUB_API_KEY** - Get from https://finnhub.io
2. **OPENAI_API_KEY** - Get from https://platform.openai.com/api-keys
3. **TELEGRAM_BOT_TOKEN** - Get from @BotFather in Telegram
4. **TELEGRAM_CHAT_ID** - Your group chat ID
5. **TELEGRAM_TOPIC_DAILY_REPORTS** - Topic 2 ID
6. **TELEGRAM_TOPIC_MARKET_NEWS** - Topic 4 ID
7. **TELEGRAM_TOPIC_COMPANY_INFO** - Topic 71 ID
8. **TELEGRAM_TOPIC_EARNINGS** - Topic 79 ID

### Step 3: Verify Workflow
1. Go to **Actions** tab
2. Select **"Run MarketAgent Twice Daily"** workflow
3. Click **"Run workflow"** to manually trigger
4. Select market session: "pre-market" or "after-market"
5. Verify execution completes successfully

### Step 4: Check Scheduled Runs
Workflow will automatically run:
- **15:30 UTC daily** (pre-market) ← Includes earnings alerts
- **22:30 UTC daily** (after-market) ← No earnings alerts

---

## 📊 Getting Required Values

### Finnhub API Key
1. Go to https://finnhub.io
2. Sign up for free tier account
3. Copy API key from dashboard
4. Add to GitHub Secrets as `FINNHUB_API_KEY`

### OpenAI API Key
1. Go to https://platform.openai.com
2. Create account or login
3. Click **"API keys"** in sidebar
4. Create new secret key
5. Add to GitHub Secrets as `OPENAI_API_KEY`

### Telegram Bot Token & Chat ID
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy token → GitHub Secrets as `TELEGRAM_BOT_TOKEN`
4. Create a private group and add bot as administrator
5. Send a message in the group
6. Message @getidsbot to get `TELEGRAM_CHAT_ID`

### Telegram Topic IDs
1. In your Telegram group, create 4 topics:
   - Topic 2: "Daily Reports"
   - Topic 4: "Market News"
   - Topic 71: "Company Info"
   - Topic 79: "Earnings Calendar"
2. Right-click each topic → "Copy link"
3. Extract topic ID from link (last number after topic/numeric)
4. Add each to corresponding GitHub Secret

---

## ✔️ Post-Deployment Verification

### Immediately After First Run
- [ ] Check GitHub Actions workflow runs successfully
- [ ] Verify Telegram messages arrive in all 4 topics
- [ ] Confirm market session label appears (📈 PRE-MARKET or 📉 AFTER-MARKET)
- [ ] Check data format (dd/mm/yyyy hh:mm UTC)

### Within 24 Hours
- [ ] Pre-market run (15:30 UTC) completes with earnings alerts
- [ ] After-market run (22:30 UTC) completes without earnings
- [ ] Market prices update correctly
- [ ] Company metrics display correctly

### Weekly Checks
- [ ] Review Telegram message formatting
- [ ] Verify earnings alerts appear on pre-market runs
- [ ] Check that after-market runs skip earnings
- [ ] Monitor for API rate limit issues

---

## 🔧 Troubleshooting

### Workflow doesn't run
- [ ] Check workflow file: `.github/workflows/marketagent-cron.yml`
- [ ] Verify all 8 GitHub Secrets are configured
- [ ] Enable "Read and write permissions" for Actions

### No Telegram messages
- [ ] Verify TELEGRAM_BOT_TOKEN is correct
- [ ] Check bot is admin in group with permission to post in topics
- [ ] Verify all 4 topic IDs are correct
- [ ] Check TELEGRAM_CHAT_ID is correct

### Earnings not showing on pre-market
- [ ] Verify MARKET_SESSION=pre-market is set
- [ ] Check earnings_2026.json has data
- [ ] Confirm TELEGRAM_TOPIC_EARNINGS ID is correct

### API rate limits exceeded
- [ ] Check Finnhub API usage (max 60 requests/minute on free tier)
- [ ] Consider upgrading API plan
- [ ] Reduce number of stocks if needed

---

## 📁 Project Structure

```
MarketAgent/
├── .github/workflows/
│   └── marketagent-cron.yml          # GitHub Actions workflow (2x daily cron)
├── contracts/                         # Data models
│   ├── market_report.py
│   └── market_snapshot.py
├── data/
│   ├── snapshots/                    # Market data (ephemeral)
│   ├── reports/                      # AI reports (ephemeral)
│   └── earnings/
│       └── earnings_2026.json        # Cached earnings (persistent)
├── engine/                            # Core business logic
│   ├── run_ai_report.py              # Generate AI market report
│   ├── send_telegram_report.py       # Post to Telegram topics
│   ├── send_earnings_alert.py        # Check & send earnings
│   ├── earnings_checker.py           # Load & format earnings
│   ├── telegram_formatter.py         # Format all messages
│   ├── telegram_sender.py            # Telegram API wrapper
│   ├── finnhub_client.py             # Finnhub API wrapper
│   ├── data_curator.py               # Process market data
│   ├── prompts.py                    # OpenAI prompt templates
│   └── report_engine.py              # Report generation logic
├── finnhub_scripts/
│   ├── fetch_and_store.py            # Fetch market data
│   └── fetch_earnings.py             # Fetch earnings calendar
├── run_full_pipeline.py              # Main orchestrator (4 steps)
├── requirements.txt                   # Python dependencies
├── .gitignore                        # Git configuration
└── DEPLOYMENT_CHECKLIST.md           # This file
```

---

## 📋 Environment Variables Reference

| Variable | Example | Source | Purpose |
|----------|---------|--------|---------|
| FINNHUB_API_KEY | `d1a2b3c4...` | https://finnhub.io | Fetch market data |
| OPENAI_API_KEY | `sk-proj-...` | https://platform.openai.com | Generate AI reports |
| TELEGRAM_BOT_TOKEN | `123456789:ABCdef...` | @BotFather | Bot authentication |
| TELEGRAM_CHAT_ID | `-1001234567890` | @getidsbot | Group chat ID |
| TELEGRAM_TOPIC_DAILY_REPORTS | `2` | Your group topics | Topic for daily reports |
| TELEGRAM_TOPIC_MARKET_NEWS | `4` | Your group topics | Topic for market news |
| TELEGRAM_TOPIC_COMPANY_INFO | `71` | Your group topics | Topic for company info |
| TELEGRAM_TOPIC_EARNINGS | `79` | Your group topics | Topic for earnings alerts |
| MARKET_SESSION | `pre-market` | GitHub Actions | Set by workflow (pre-market or after-market) |

---

## 📞 Support

For issues or questions:
1. Check GitHub Actions logs: **Actions tab → Workflow run → Logs**
2. Review Telegram for error messages
3. Check project README.md for additional information

---

**Status**: ✅ Project is production-ready for deployment to GitHub
