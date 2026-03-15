"""
BaseCollector — abstract contract for every data source.

Each collector:
 1. Receives a Source config on init.
 2. Implements fetch() → List[RawItem].
 3. RawItem is a minimal dict that the pipeline normalizer turns into a Signal.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import Source


@dataclass
class RawItem:
    """Minimal raw record returned by any collector."""
    source_id:    str
    raw_id:       str
    title:        str
    body:         str         = ""
    url:          str         = ""
    author:       str         = ""
    published_at: Optional[datetime] = None
    extra:        Dict[str, Any] = field(default_factory=dict)


class BaseCollector(ABC):
    """Abstract base for all Signal Terminal collectors."""

    def __init__(self, source: Source):
        self.source = source

    @abstractmethod
    def fetch(self) -> List[RawItem]:
        """Fetch raw items from the source. Must be synchronous."""
        ...

    @property
    def source_id(self) -> str:
        return self.source.id

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source={self.source.name!r}>"
