from app.retrieval.models import RetrievedChunk


class PromptBuilder:
    """Builds prompts for grounded question answering."""

    @staticmethod
    def build(
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        context = "\n\n".join(
            chunk.content
            for chunk in chunks
        )

        return f"""
You are an engineering knowledge assistant.

Answer ONLY using the supplied context.

If the answer cannot be found in the context,
say that the information is unavailable.

Context:
{context}

Question:
{question}

Answer:
""".strip()