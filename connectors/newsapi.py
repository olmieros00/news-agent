# Optional NewsAPI. Fetches raw response only.
from .base import BaseConnector


class NewsAPIConnector(BaseConnector):
    def fetch(self, since=None, config=None):
        raise NotImplementedError("Phase 1")
