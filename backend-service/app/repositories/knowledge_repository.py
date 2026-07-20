from abc import ABC, abstractmethod


class KnowledgeRepository(ABC):

    @abstractmethod
    def ask(self, question: str) -> str:
        """Return an answer."""
        pass