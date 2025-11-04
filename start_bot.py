#!/usr/bin/env python3
import sys
import os
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Simple healthcheck server
from flask import Flask
app = Flask(__name__)

# Global bot status
bot_status = "starting"

@app.route('/')
def health():
    return 'OK'

@app.route('/health')
def health_detailed():
    import time
    uptime = time.time() - start_time if 'start_time' in globals() else 0
    return {
        'status': bot_status,
        'bot_token': 'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET',
        'database': 'SET' if os.getenv('DATABASE_URL') else 'NOT SET',
        'uptime_seconds': round(uptime, 1),
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    }

def run_healthcheck():
    app.run(host='0.0.0.0', port=8000, debug=False)

print("=== Environment Variables Check ===")
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"TELEGRAM_BOT_TOKEN: {'SET (' + token[:10] + '...)' if token else 'NOT SET'}")

db_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL: {'SET' if db_url else 'NOT SET'}")

ocm_key = os.getenv('OCM_API_KEY')
print(f"OCM_API_KEY: {'SET' if ocm_key else 'NOT SET'}")

print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

if not token:
    print("ERROR: TELEGRAM_BOT_TOKEN is required!")
    sys.exit(1)

print("Environment check passed, starting healthcheck server...")

# Add startup timing logs
import time
start_time = time.time()
print(f"Starting bot at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

# Start healthcheck server in background
health_thread = threading.Thread(target=run_healthcheck, daemon=True)
health_thread.start()

print("Healthcheck server started on port 8000")
print("Starting bot...")

try:
    from chargebot.bot import run_bot
    import asyncio

    print("Bot module imported successfully")
    print("Starting bot...")

    if __name__ == "__main__":
        print(f"Bot startup took {time.time() - start_time:.2f} seconds")

        # Run bot with timeout
        async def run_with_timeout():
            try:
                await asyncio.wait_for(run_bot(), timeout=30.0)
                bot_status = "running"
            except asyncio.TimeoutError:
                print("Bot startup timed out after 30 seconds")
                bot_status = "timeout"
                raise
            except Exception as e:
                print(f"Error during bot startup: {e}")
                bot_status = "error"
                raise

        asyncio.run(run_with_timeout())
except Exception as e:
    print(f"Error starting bot: {e}")
    import traceback
    traceback.print_exc()
    print(f"Failed after {time.time() - start_time:.2f} seconds")
    bot_status = "failed"
    # Don't exit immediately, keep healthcheck server running for debugging
    print("Healthcheck server still running for debugging...")
    try:
        while True:
            time.sleep(60)  # Keep alive for monitoring
    except KeyboardInterrupt:
        print("Shutting down healthcheck server...")