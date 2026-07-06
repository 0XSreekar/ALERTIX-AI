__version__ = "0.1.0"

# psycopg3 async requires SelectorEventLoop on Windows. Must be set before
# uvicorn creates its event loop — this file is imported very early.
import asyncio as _asyncio
import platform as _platform

if _platform.system() == "Windows":
    _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
