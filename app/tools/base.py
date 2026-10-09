from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class that every tool must inherit from."""
    name: str
    description: str

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclass must override execute()")
