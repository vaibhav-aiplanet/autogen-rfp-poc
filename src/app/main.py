import asyncio

from app.core.llm_tracker import track_llm

# from app.examples.group_chat import main as func
from app.rfp.main import main as func


@track_llm
def main():
    try:
        asyncio.run(func())
    except KeyboardInterrupt:
        print("Quitting")
