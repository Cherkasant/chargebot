#!/usr/bin/env python3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Starting ChargeBot...")
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")

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