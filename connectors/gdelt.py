# GDELT DOC API. Fetches raw response only.
from .base import BaseConnector


class GDELTConnector(BaseConnector):
    def fetch(self, since=None, config=None):
        raise NotImplementedError("Phase 1")
