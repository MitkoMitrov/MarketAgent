"""
Telegram sender module for posting messages to specific topics in a group.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required in .env")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message_to_topic(topic_id, text, parse_mode="Markdown"):
    """
    Send a message to a specific topic in a Telegram group.
    
    Args:
        topic_id (int): The message_thread_id (topic ID).
        text (str): Message text.
        parse_mode (str): "Markdown" or "MarkdownV2" or "HTML".
    
    Returns:
        dict: Response from Telegram API, or None on error.
    """
    try:
        payload = {
            "chat_id": int(TELEGRAM_CHAT_ID),
            "message_thread_id": int(topic_id),
            "text": text,
            "disable_web_page_preview": True
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload, timeout=10)
        if response.status_code != 200:
            error_data = response.json()
            print(f"⚠️  Telegram API error (code {response.status_code}): {error_data.get('description', 'Unknown error')}")
            response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending Telegram message to topic {topic_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def send_test_message(topic_id, topic_name):
    """Send a quick test message to a topic."""
    text = f"✅ Test message to *{topic_name}* topic from MarketAgent!"
    return send_message_to_topic(topic_id, text)
