from app.prompts.rag_prompts import (
    RAG_SYSTEM_PROMPT,
    RAG_USER_PROMPT_TEMPLATE,
)
from app.retrieval.models import RetrievedChunk


class PromptBuilder:
    """Build prompts for internal document question answering."""

    @staticmethod
    def build(
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

        if not chunks:
            raise ValueError(
                "At least one retrieved chunk is required."
            )

        context_sections: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            document_name = chunk.metadata.get(
                "document_name",
                chunk.document_id,
            )
            page = chunk.metadata.get("page")

            source_header = f"Source {index}: {document_name}"

            if page is not None:
                source_header += f", page {page}"

            context_sections.append(
                f"{source_header}\n{chunk.content.strip()}"
            )

        context = "\n\n".join(context_sections)

        user_prompt = RAG_USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question.strip(),
        )

        return f"{RAG_SYSTEM_PROMPT}\n\n{user_prompt}"