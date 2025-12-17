from dotenv import load_dotenv
import os
import finnhub

# Load .env file once
load_dotenv()

# Get API key from environment
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# Initialize Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
