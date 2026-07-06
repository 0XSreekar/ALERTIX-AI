"""Entry point that sets the Windows event-loop policy BEFORE uvicorn boots.

On Windows, psycopg3 async requires SelectorEventLoop. Uvicorn's default
asyncio loop is ProactorEventLoop, which psycopg refuses to run on. We must
override the policy before uvicorn imports asyncio.
"""
import asyncio
import platform
import sys

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    port = 8000
    log_level = "info"
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 1 < len(sys.argv) - 1:
            port = int(sys.argv[i + 2])
        if arg == "--log-level" and i + 1 < len(sys.argv) - 1:
            log_level = sys.argv[i + 2]
    uvicorn.run("app.main:app", port=port, log_level=log_level, loop="asyncio")
