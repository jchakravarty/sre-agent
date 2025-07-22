"""This module contains the base class for LLM clients."""
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """Base class for LLM clients."""
    @abstractmethod
    def call(self, messages, tools=None):
        """Makes a call to the LLM."""
