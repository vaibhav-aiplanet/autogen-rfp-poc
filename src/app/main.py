import asyncio

from app.examples.group_chat import main as func
from app.llm_tracker import track_llm


@track_llm
def main():
    try:
        asyncio.run(func())
    except KeyboardInterrupt:
        print("Quitting")
