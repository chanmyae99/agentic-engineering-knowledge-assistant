from app.repositories.knowledge_repository import KnowledgeRepository


class MemoryRepository(KnowledgeRepository):

    def ask(self, question: str) -> str:
        return (
            f"This is a mock response.\n\n"
            f"Question: {question}"
        )