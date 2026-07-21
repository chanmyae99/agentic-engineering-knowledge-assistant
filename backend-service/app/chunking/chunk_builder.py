"""
Chunk construction for the structure-aware document pipeline.

This module converts ``StructuredElement`` objects into final
``DocumentChunk`` objects.

Phase 1 responsibilities
------------------------
- group related elements under the same section
- preserve headings together with their section content
- build chunks up to the configured maximum token limit
- preserve page, paragraph, section, and source metadata
- assign sequential chunk indexes

Later phases will add:
- sentence-aware splitting for oversized elements
- sentence-based overlap between chunks
- more advanced content-type handling
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable
from uuid import UUID

from app.chunking.models import (
    ChunkMetadata,
    ContentType,
    DocumentChunk,
)
from app.chunking.structure_analyzer import (
    ElementType,
    StructuredElement,
)
from app.chunking.tokenizer import Tokenizer
from app.core.config import get_settings


@dataclass(slots=True)
class _ChunkBuffer:
    """
    Internal mutable buffer used while constructing one chunk.

    The buffer collects structured elements until the builder decides that
    the chunk should be finalised.
    """

    elements: list[StructuredElement] = field(default_factory=list)
    token_count: int = 0

    @property
    def is_empty(self) -> bool:
        """Return whether the buffer currently contains no elements."""
        return not self.elements

    def clear(self) -> None:
        """Reset the buffer so it can be reused for the next chunk."""
        self.elements.clear()
        self.token_count = 0


class ChunkBuilder:
    """
    Build final document chunks from analysed document elements.

    Parameters
    ----------
    target_tokens:
        Preferred chunk size. The builder may finalise a chunk near this size
        when appropriate.

    max_tokens:
        Hard maximum size for ordinary chunks.

    overlap_tokens:
        Number of tokens that later phases will carry from one chunk into the
        next. Phase 1 stores and validates this setting but does not yet apply
        overlap.

    tokenizer:
        Optional tokenizer instance. A default ``Tokenizer`` is created when
        none is supplied.
    """

    def __init__(
        self,
        target_tokens: int | None = None,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        settings = get_settings()

        self.target_tokens = (
            target_tokens
            if target_tokens is not None
            else settings.chunk_target_tokens
        )
        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else settings.chunk_max_tokens
        )
        self.overlap_tokens = (
            overlap_tokens
            if overlap_tokens is not None
            else settings.chunk_overlap_tokens
        )
        self.tokenizer = tokenizer or Tokenizer()

        self._validate_configuration()

    def build_chunks(
        self,
        elements: Iterable[StructuredElement],
        document_id: str | UUID,
        file_name: str,
        blob_name: str,
        file_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """
        Convert structured elements into ordered document chunks.

        Oversized elements are split before buffering. When a chunk is finalised
        because of size, a sentence-based overlap may be carried into the next
        chunk. Overlap is never carried across a section boundary.
        """
        normalised_document_id = str(document_id).strip()

        if not normalised_document_id:
            raise ValueError("document_id must not be empty.")

        if not file_name.strip():
            raise ValueError("file_name must not be empty.")

        if not blob_name.strip():
            raise ValueError("blob_name must not be empty.")

        normalised_file_type = file_type.lower().lstrip(".")

        if normalised_file_type not in {"pdf", "docx"}:
            raise ValueError(
                "file_type must be either 'pdf' or 'docx'."
            )

        document_metadata = dict(metadata or {})
        chunk_buffer = _ChunkBuffer()
        chunks: list[DocumentChunk] = []

        for original_element in elements:
            if not original_element.text or not original_element.text.strip():
                continue

            split_elements = self._split_oversized_element(
                original_element
            )

            for element in split_elements:
                element_token_count = self.tokenizer.count_tokens(
                    element.text
                )

                should_flush_for_section = self._section_changed(
                    buffer=chunk_buffer,
                    next_element=element,
                )

                should_flush_for_size = (
                    not chunk_buffer.is_empty
                    and (
                        chunk_buffer.token_count + element_token_count
                        > self.max_tokens
                    )
                )

                if should_flush_for_section or should_flush_for_size:
                    overlap_element: StructuredElement | None = None

                    # Overlap is appropriate only when the chunk is split because
                    # of size while remaining inside the same section.
                    if (
                        should_flush_for_size
                        and not should_flush_for_section
                        and self.overlap_tokens > 0
                    ):
                        overlap_element = self._build_overlap_element(
                            buffer=chunk_buffer,
                            next_element=element,
                        )

                    chunks.append(
                        self._create_chunk(
                            buffer=chunk_buffer,
                            document_id=normalised_document_id,
                            chunk_index=len(chunks),
                            file_name=file_name,
                            blob_name=blob_name,
                            file_type=normalised_file_type,
                            document_metadata=document_metadata,
                        )
                    )
                    chunk_buffer.clear()

                    if overlap_element is not None:
                        overlap_count = self.tokenizer.count_tokens(
                            overlap_element.text
                        )

                        # Avoid adding overlap when it would leave no room for the
                        # actual next element.
                        if (
                            overlap_count + element_token_count
                            <= self.max_tokens
                        ):
                            self._append_element(
                                buffer=chunk_buffer,
                                element=overlap_element,
                                element_token_count=overlap_count,
                            )

                self._append_element(
                    buffer=chunk_buffer,
                    element=element,
                    element_token_count=element_token_count,
                )

        if not chunk_buffer.is_empty:
            chunks.append(
                self._create_chunk(
                    buffer=chunk_buffer,
                    document_id=normalised_document_id,
                    chunk_index=len(chunks),
                    file_name=file_name,
                    blob_name=blob_name,
                    file_type=normalised_file_type,
                    document_metadata=document_metadata,
                )
            )

        return chunks
    def _append_element(
        self,
        buffer: _ChunkBuffer,
        element: StructuredElement,
        element_token_count: int,
    ) -> None:
        """
        Add one structured element to the active buffer.
        """
        buffer.elements.append(element)
        buffer.token_count += element_token_count

    @staticmethod
    def _section_changed(
        buffer: _ChunkBuffer,
        next_element: StructuredElement,
    ) -> bool:
        """
        Return whether the next element begins a different section.

        A heading only forces a new chunk when the current buffer already
        contains body content. This prevents an isolated heading chunk when a
        heading is immediately followed by its first paragraph.
        """
        if buffer.is_empty:
            return False

        current_path = buffer.elements[-1].section_path
        next_path = next_element.section_path

        if current_path == next_path:
            return False

        buffer_contains_body = any(
            element.element_type is not ElementType.HEADING
            for element in buffer.elements
        )

        return buffer_contains_body

    def _create_chunk(
        self,
        buffer: _ChunkBuffer,
        document_id: str,
        chunk_index: int,
        file_name: str,
        blob_name: str,
        file_type: str,
        document_metadata: dict[str, Any],
    ) -> DocumentChunk:
        """
        Create one immutable ``DocumentChunk`` from buffered elements.
        """
        if buffer.is_empty:
            raise ValueError(
                "Cannot create a chunk from an empty buffer."
            )

        content = self._join_element_text(buffer.elements)
        token_count = self.tokenizer.count_tokens(content)

        page_numbers = [
            element.page_number
            for element in buffer.elements
            if element.page_number is not None
        ]

        paragraph_numbers = [
            element.paragraph_number
            for element in buffer.elements
            if element.paragraph_number is not None
        ]

        section_path = self._resolve_section_path(buffer.elements)
        section = section_path[-1] if section_path else None

        chunk_metadata = self._build_chunk_metadata(
            elements=buffer.elements,
            file_name=file_name,
            blob_name=blob_name,
            file_type=file_type,
            document_metadata=document_metadata,
        )

        return DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            content_type=self._resolve_content_type(
                buffer.elements
            ),
            token_count=token_count,
            page_start=min(page_numbers) if page_numbers else None,
            page_end=max(page_numbers) if page_numbers else None,
            section=section,
            section_path=section_path,
            paragraph_start=(
                min(paragraph_numbers)
                if paragraph_numbers
                else None
            ),
            paragraph_end=(
                max(paragraph_numbers)
                if paragraph_numbers
                else None
            ),
            metadata=chunk_metadata,
        )

    @staticmethod
    def _join_element_text(
        elements: list[StructuredElement],
    ) -> str:
        """
        Join elements while preserving readable document structure.

        Headings and body paragraphs are separated with blank lines. Adjacent
        list items remain on consecutive lines.
        """
        content_parts: list[str] = []
        for index, element in enumerate(elements):
            text = element.text.strip()

            if not text:
                continue

            if not content_parts:
                content_parts.append(text)
                continue

            previous_element = elements[index - 1]

            if (
                previous_element.element_type is ElementType.LIST
                and element.element_type is ElementType.LIST
            ):
                content_parts.append(f"\n{text}")
            else:
                content_parts.append(f"\n\n{text}")        

        return "".join(content_parts).strip()

    @staticmethod
    def _resolve_section_path(
        elements: list[StructuredElement],
    ) -> list[str]:
        """
        Select the deepest available section path in the chunk.
        """
        paths = [
            element.section_path
            for element in elements
            if element.section_path
        ]

        if not paths:
            return []

        deepest_path = max(paths, key=len)
        return list(deepest_path)

    @staticmethod
    def _resolve_content_type(
        elements: list[StructuredElement],
    ) -> ContentType:
        """
        Determine the most appropriate chunk content type.

        A chunk containing table content is marked as ``TABLE``. A chunk made
        primarily from list items is marked as ``LIST``. All other chunks are
        treated as normal text.
        """
        body_elements = [
            element
            for element in elements
            if element.element_type is not ElementType.HEADING
        ]

        if any(
            element.element_type is ElementType.TABLE
            for element in body_elements
        ):
            return ContentType.TABLE

        if body_elements and all(
            element.element_type is ElementType.LIST
            for element in body_elements
        ):
            return ContentType.LIST

        return ContentType.TEXT

    @staticmethod
    def _build_chunk_metadata(
        elements: list[StructuredElement],
        file_name: str,
        blob_name: str,
        file_type: str,
        document_metadata: dict[str, Any],
    ) -> ChunkMetadata:
        """
        Combine document-level and element-level metadata.

        Element metadata is stored under ``element_metadata`` so information
        from the parser is not discarded.
        """
        element_metadata = [
            dict(element.metadata)
            for element in elements
            if element.metadata
        ]

        extra = dict(document_metadata)

        if element_metadata:
            extra["element_metadata"] = element_metadata

        styles = [
            element.style
            for element in elements
            if element.style
        ]

        if styles:
            extra["styles"] = list(dict.fromkeys(styles))

        return ChunkMetadata(
            file_name=file_name,
            blob_name=blob_name,
            file_type=file_type,
            extra=extra,
        )
    def _split_oversized_element(
        self,
        element: StructuredElement,
    ) -> list[StructuredElement]:
        """
        Split one element when its content exceeds the maximum token limit.

        Sentence boundaries are preferred. If an individual sentence is itself
        too large, it is divided using a word-based fallback.

        All resulting elements preserve the original structural and source
        metadata.
        """
        text = element.text.strip()

        if not text:
            return []

        if self.tokenizer.count_tokens(text) <= self.max_tokens:
            return [element]

        sentences = self.tokenizer.split_sentences(text)

        if not sentences:
            return self._split_element_by_words(element)

        fragments: list[str] = []
        current_sentences: list[str] = []
        current_token_count = 0

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            sentence_token_count = self.tokenizer.count_tokens(sentence)

            # A single sentence may still exceed the hard maximum.
            if sentence_token_count > self.max_tokens:
                if current_sentences:
                    fragments.append(" ".join(current_sentences).strip())
                    current_sentences = []
                    current_token_count = 0

                word_fragments = self._split_text_by_words(sentence)
                fragments.extend(word_fragments)
                continue

            proposed_token_count = (
                current_token_count + sentence_token_count
            )

            if (
                current_sentences
                and proposed_token_count > self.target_tokens
            ):
                fragments.append(" ".join(current_sentences).strip())
                current_sentences = [sentence]
                current_token_count = sentence_token_count
            else:
                current_sentences.append(sentence)
                current_token_count = proposed_token_count

        if current_sentences:
            fragments.append(" ".join(current_sentences).strip())

        if not fragments:
            return self._split_element_by_words(element)

        split_count = len(fragments)
        split_elements: list[StructuredElement] = []

        for split_index, fragment in enumerate(fragments):
            split_metadata = dict(element.metadata)
            split_metadata.update(
                {
                    "is_split_fragment": True,
                    "split_fragment_index": split_index,
                    "split_fragment_count": split_count,
                }
            )

            split_elements.append(
                replace(
                    element,
                    text=fragment,
                    metadata=split_metadata,
                )
            )

        return split_elements

    def _split_element_by_words(
        self,
        element: StructuredElement,
    ) -> list[StructuredElement]:
        """
        Split an element by words when sentence splitting is insufficient.
        """
        fragments = self._split_text_by_words(element.text)

        split_count = len(fragments)
        split_elements: list[StructuredElement] = []

        for split_index, fragment in enumerate(fragments):
            split_metadata = dict(element.metadata)
            split_metadata.update(
                {
                    "is_split_fragment": True,
                    "split_fragment_index": split_index,
                    "split_fragment_count": split_count,
                    "split_method": "words",
                }
            )

            split_elements.append(
                replace(
                    element,
                    text=fragment,
                    metadata=split_metadata,
                )
            )

        return split_elements

    def _split_text_by_words(self, text: str) -> list[str]:
        """
        Divide text into fragments that do not exceed ``max_tokens``.

        The current tokenizer uses approximate word counting, so this fallback
        groups words conservatively according to the configured target size.
        """
        words = text.split()

        if not words:
            return []

        fragments: list[str] = []
        current_words: list[str] = []

        for word in words:
            proposed_words = [*current_words, word]
            proposed_text = " ".join(proposed_words)

            if (
                current_words
                and self.tokenizer.count_tokens(proposed_text)
                > self.target_tokens
            ):
                fragments.append(" ".join(current_words))
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            fragments.append(" ".join(current_words))

        return fragments

    def _build_overlap_element(
        self,
        buffer: _ChunkBuffer,
        next_element: StructuredElement,
    ) -> StructuredElement | None:
        """
        Build a synthetic element containing the end of the previous chunk.

        Sentences are selected from the end of the buffered body content until
        the configured overlap size is reached. Headings are excluded because
        the section path already preserves heading context.
        """
        body_elements = [
            element
            for element in buffer.elements
            if element.element_type is not ElementType.HEADING
        ]

        if not body_elements:
            return None

        sentences: list[str] = []

        for element in body_elements:
            element_sentences = self.tokenizer.split_sentences(
                element.text
            )

            if element_sentences:
                sentences.extend(element_sentences)
            elif element.text.strip():
                sentences.append(element.text.strip())

        if not sentences:
            return None

        selected_sentences: list[str] = []
        selected_token_count = 0

        for sentence in reversed(sentences):
            sentence = sentence.strip()

            if not sentence:
                continue

            sentence_token_count = self.tokenizer.count_tokens(sentence)

            if selected_sentences and (
                selected_token_count + sentence_token_count
                > self.overlap_tokens
            ):
                break

            # When the final sentence is larger than the requested overlap,
            # retain only its trailing words.
            if (
                not selected_sentences
                and sentence_token_count > self.overlap_tokens
            ):
                sentence = self._take_trailing_tokens(
                    sentence,
                    self.overlap_tokens,
                )
                sentence_token_count = self.tokenizer.count_tokens(
                    sentence
                )

            selected_sentences.insert(0, sentence)
            selected_token_count += sentence_token_count

            if selected_token_count >= self.overlap_tokens:
                break

        overlap_text = " ".join(selected_sentences).strip()

        if not overlap_text:
            return None

        source_element = body_elements[-1]
        overlap_metadata = dict(source_element.metadata)
        overlap_metadata.update(
            {
                "is_overlap": True,
                "overlap_token_count": self.tokenizer.count_tokens(
                    overlap_text
                ),
            }
        )

        return StructuredElement(
            text=overlap_text,
            element_type=source_element.element_type,
            section=next_element.section,
            section_path=list(next_element.section_path),
            heading_level=None,
            page_number=source_element.page_number,
            paragraph_number=source_element.paragraph_number,
            style=source_element.style,
            metadata=overlap_metadata,
        )

    def _take_trailing_tokens(
        self,
        text: str,
        token_limit: int,
    ) -> str:
        """
        Return the trailing portion of text within an approximate token limit.
        """
        if token_limit <= 0:
            return ""

        words = text.split()

        if len(words) <= token_limit:
            return text.strip()

        return " ".join(words[-token_limit:]).strip()
    def _validate_configuration(self) -> None:
        """
        Validate chunk-size settings during builder construction.
        """
        if self.target_tokens < 1:
            raise ValueError(
                "target_tokens must be at least 1."
            )

        if self.max_tokens < 1:
            raise ValueError(
                "max_tokens must be at least 1."
            )

        if self.overlap_tokens < 0:
            raise ValueError(
                "overlap_tokens must not be negative."
            )

        if self.target_tokens > self.max_tokens:
            raise ValueError(
                "target_tokens must not exceed max_tokens."
            )

        if self.overlap_tokens >= self.max_tokens:
            raise ValueError(
                "overlap_tokens must be smaller than max_tokens."
            )