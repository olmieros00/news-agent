# Cluster = same event; list of normalized item ids.
from dataclasses import dataclass


@dataclass
class Cluster:
    cluster_id: str
    member_ids: list[str]
