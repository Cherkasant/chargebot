#!/usr/bin/env python3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chargebot.bot import run_bot
import asyncio

if __name__ == "__main__":
    asyncio.run(run_bot())