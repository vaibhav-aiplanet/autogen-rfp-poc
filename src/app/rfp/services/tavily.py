import logging
from typing import Any

from tavily import AsyncTavilyClient

from app.core.config import config


class TavilyService:
    def __init__(self):
        self.client = AsyncTavilyClient(config.TAVILY)

    async def searchAnswer(self, query: str) -> dict[str, Any] | None:
        try:
            response = await self.client.search(query)
            return response
        except Exception as e:
            error = f"Error using web service (searchAnswer) : {str(e)}"
            logging.error(error)
