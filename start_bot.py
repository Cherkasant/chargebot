#!/usr/bin/env python3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=== Environment Variables Check ===")
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"TELEGRAM_BOT_TOKEN: {'SET (' + token[:10] + '...)' if token else 'NOT SET'}")

db_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL: {'SET' if db_url else 'NOT SET'}")

ocm_key = os.getenv('OCM_API_KEY')
print(f"OCM_API_KEY: {'SET' if ocm_key else 'NOT SET'}")

print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

if not token:
    print("❌ TELEGRAM_BOT_TOKEN is required!")
    sys.exit(1)

print("✅ Environment check passed, starting bot...")

try:
    from chargebot.bot import run_bot
    import asyncio

    print("Bot module imported successfully")
    print("Starting bot...")

    if __name__ == "__main__":
        asyncio.run(run_bot())
except Exception as e:
    print(f"Error starting bot: {e}")
    import traceback
    traceback.print_exc()