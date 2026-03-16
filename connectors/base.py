# Contract for all source connectors: fetch(since, config) -> list[RawItem].
# RawItem = opaque payload + source_id + fetched_at.
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    def fetch(self, since=None, config=None):
        """Return list of raw items. No transformation."""
        pass
