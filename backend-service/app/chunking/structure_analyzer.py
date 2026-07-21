"""
Document-structure analysis for the chunking pipeline.

This module converts cleaned parser units into structured document elements.
It identifies headings, paragraphs, lists, and tables while preserving source
metadata such as page numbers, paragraph numbers, and Word styles.

The structure analyser sits between text cleaning and chunk construction:

    Parsed document units
            ↓
       TextCleaner
            ↓
    StructureAnalyzer
            ↓
     StructuredElement[]
            ↓
       ChunkBuilder

Responsibilities
----------------
- classify document units by content type
- recognise DOCX headings from Word styles
- recognise likely PDF headings using conservative rules
- maintain a hierarchical section path
- preserve source location metadata

This module deliberately does not:
- split content into final chunks
- calculate overlaps
- generate embeddings
- access Azure Blob Storage
- write data to PostgreSQL
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from app.chunking.cleaner import TextCleaner


class ElementType(str, Enum):
    """
    Types of structured document elements recognised by the analyser.

    Attributes
    ----------
    HEADING:
        A section or subsection heading.

    TEXT:
        A normal body-text paragraph.

    LIST:
        An ordered or unordered list item.

    TABLE:
        Text representing a table or a section of a table.
    """

    HEADING = "heading"
    TEXT = "text"
    LIST = "list"
    TABLE = "table"


@dataclass(slots=True)
class StructuredElement:
    """
    Represents one analysed element from a PDF or DOCX document.

    This is an internal chunking-pipeline object. It preserves document
    structure before several elements are combined into a final
    ``DocumentChunk``.

    Attributes
    ----------
    text:
        Cleaned textual content of the element.

    element_type:
        Classification assigned by the structure analyser.

    section:
        Closest active heading associated with the element.

    section_path:
        Ordered hierarchy of active headings.

        Example:
            [
                "Safety Requirements",
                "Risk Assessment",
                "Hazard Identification",
            ]

    heading_level:
        Heading depth when this element is a heading. ``None`` for normal
        text, lists, and tables.

    page_number:
        One-based PDF page number when available.

    paragraph_number:
        Zero-based or source-defined DOCX paragraph position when available.

    style:
        Source style name, such as ``"Heading 1"`` or ``"List Paragraph"``.

    metadata:
        Additional parser metadata preserved for later pipeline stages.
    """

    text: str
    element_type: ElementType

    section: str | None = None
    section_path: list[str] = field(default_factory=list)
    heading_level: int | None = None

    page_number: int | None = None
    paragraph_number: int | None = None
    style: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


class StructureAnalyzer:
    """
    Analyse cleaned PDF and DOCX units while preserving document hierarchy.

    DOCX heading detection primarily uses Word paragraph styles such as
    ``Heading 1``, ``Heading 2``, and ``Heading 3``.

    PDF heading detection uses conservative textual heuristics because many
    PDFs do not preserve semantic heading information. The rules recognise:

    - numbered clauses such as ``2 Risk Assessment``
    - subsection numbers such as ``2.3 Hazard Identification``
    - short uppercase headings
    - short title-style lines without sentence-ending punctuation

    False-positive prevention is important. A normal sentence should remain
    body text unless it strongly resembles a heading.
    """

    # Matches Word heading styles such as:
    # Heading 1
    # Heading 2
    # Heading 3
    _DOCX_HEADING_STYLE_PATTERN = re.compile(
        r"^heading\s+([1-9]\d*)$",
        flags=re.IGNORECASE,
    )

    # Matches numbered headings such as:
    # 1 Introduction
    # 2.3 Risk Assessment
    # 4.2.1 General Requirements
    #
    # The heading must contain text after its numeric prefix.
    _NUMBERED_HEADING_PATTERN = re.compile(
        r"^(?P<number>\d+(?:\.\d+){0,5})\.?\s+(?P<title>\S.*)$"
    )

    # Matches common ordered and unordered list formats.
    _LIST_ITEM_PATTERN = re.compile(
        r"^(?:"
        r"[-*]\s+|"                  # - item or * item
        r"\d+[.)]\s+|"               # 1. item or 1) item
        r"[a-zA-Z][.)]\s+|"          # a. item or A) item
        r"\([a-zA-Z0-9]+\)\s+"        # (a) item or (1) item
        r")"
    )

    # Sentence-ending punctuation generally indicates body text.
    _SENTENCE_ENDINGS = (".", "!", "?", ";")

    # A heading should normally be reasonably short.
    _MAX_HEADING_CHARACTERS = 140
    _MAX_HEADING_WORDS = 16

    @classmethod
    def analyze(
        cls,
        units: Iterable[Any],
        file_type: str,
    ) -> list[StructuredElement]:
        """
        Analyse parser units and return structured document elements.

        The method accepts parser units represented either as objects or
        dictionaries. This keeps the analyser compatible with Pydantic models,
        dataclasses, and test fixtures.

        Expected parser-unit fields may include:

        - ``text``
        - ``page_number``
        - ``paragraph_number``
        - ``style``
        - ``section``
        - ``content_type``
        - ``metadata``

        Parameters
        ----------
        units:
            Ordered PDF or DOCX parser units.

        file_type:
            Source document type, normally ``"pdf"`` or ``"docx"``.

        Returns
        -------
        list[StructuredElement]
            Analysed elements in the same order as the source units.

        Raises
        ------
        ValueError
            If the source file type is unsupported.
        """
        normalised_file_type = file_type.lower().lstrip(".")

        if normalised_file_type not in {"pdf", "docx"}:
            raise ValueError(
                "file_type must be either 'pdf' or 'docx'."
            )

        structured_elements: list[StructuredElement] = []

        # Maps heading levels to active titles:
        # {1: "Safety", 2: "Risk Assessment"}
        active_headings: dict[int, str] = {}

        for unit in units:
            raw_text = cls._get_value(unit, "text", default="")
            cleaned_text = TextCleaner.clean_text(str(raw_text))

            # Ignore empty parser units after cleaning.
            if not cleaned_text:
                continue

            style = cls._normalise_optional_string(
                cls._get_value(unit, "style")
            )
            page_number = cls._normalise_optional_integer(
                cls._get_value(unit, "page_number")
            )
            paragraph_number = cls._normalise_optional_integer(
                cls._get_value(unit, "paragraph_number")
            )
            metadata = cls._normalise_metadata(
                cls._get_value(unit, "metadata", default={})
            )

            declared_content_type = cls._normalise_optional_string(
                cls._get_value(unit, "content_type")
            )

            heading_level = cls._detect_heading_level(
                text=cleaned_text,
                style=style,
                file_type=normalised_file_type,
            )

            if heading_level is not None:
                cls._update_heading_hierarchy(
                    active_headings=active_headings,
                    heading_level=heading_level,
                    heading_text=cleaned_text,
                )

                section_path = cls._build_section_path(active_headings)

                structured_elements.append(
                    StructuredElement(
                        text=cleaned_text,
                        element_type=ElementType.HEADING,
                        section=cleaned_text,
                        section_path=section_path,
                        heading_level=heading_level,
                        page_number=page_number,
                        paragraph_number=paragraph_number,
                        style=style,
                        metadata=metadata,
                    )
                )
                continue

            element_type = cls._detect_non_heading_type(
                text=cleaned_text,
                style=style,
                declared_content_type=declared_content_type,
                metadata=metadata,
            )

            section_path = cls._build_section_path(active_headings)
            closest_section = (
                section_path[-1]
                if section_path
                else cls._normalise_optional_string(
                    cls._get_value(unit, "section")
                )
            )

            structured_elements.append(
                StructuredElement(
                    text=cleaned_text,
                    element_type=element_type,
                    section=closest_section,
                    section_path=section_path,
                    heading_level=None,
                    page_number=page_number,
                    paragraph_number=paragraph_number,
                    style=style,
                    metadata=metadata,
                )
            )

        return structured_elements

    @classmethod
    def _detect_heading_level(
        cls,
        text: str,
        style: str | None,
        file_type: str,
    ) -> int | None:
        """
        Determine whether an element is a heading and return its level.

        DOCX styles are treated as the strongest signal. PDF headings are
        identified using textual rules.
        """
        if file_type == "docx":
            docx_level = cls._heading_level_from_docx_style(style)

            if docx_level is not None:
                return docx_level

        numbered_level = cls._heading_level_from_numbering(text)

        if numbered_level is not None:
            return numbered_level

        if cls._looks_like_uppercase_heading(text):
            return 1

        if cls._looks_like_title_heading(text):
            return 2

        return None

    @classmethod
    def _heading_level_from_docx_style(
        cls,
        style: str | None,
    ) -> int | None:
        """
        Extract a heading level from a DOCX paragraph style.
        """
        if not style:
            return None

        match = cls._DOCX_HEADING_STYLE_PATTERN.fullmatch(style.strip())

        if not match:
            return None

        return int(match.group(1))

    @classmethod
    def _heading_level_from_numbering(
        cls,
        text: str,
    ) -> int | None:
        """
        Infer a heading level from numeric clause depth.

        Examples
        --------
        ``"1 Introduction"`` returns level 1.

        ``"2.3 Risk Assessment"`` returns level 2.

        ``"4.2.1 Requirements"`` returns level 3.
        """
        if not cls._is_reasonable_heading_length(text):
            return None

        match = cls._NUMBERED_HEADING_PATTERN.fullmatch(text.strip())

        if not match:
            return None

        title = match.group("title").strip()

        # Avoid classifying ordinary numbered list sentences as headings.
        if title.endswith(cls._SENTENCE_ENDINGS):
            return None

        number_prefix = match.group("number")
        return number_prefix.count(".") + 1

    @classmethod
    def _looks_like_uppercase_heading(cls, text: str) -> bool:
        """
        Return whether text resembles a short uppercase heading.
        """
        stripped = text.strip()

        if not cls._is_reasonable_heading_length(stripped):
            return False

        if stripped.endswith(cls._SENTENCE_ENDINGS):
            return False

        alphabetic_characters = [
            character
            for character in stripped
            if character.isalpha()
        ]

        if not alphabetic_characters:
            return False

        return all(
            character.isupper()
            for character in alphabetic_characters
        )

    @classmethod
    def _looks_like_title_heading(cls, text: str) -> bool:
        """
        Conservatively recognise short title-style headings.

        This rule is intentionally stricter than Python's ``str.istitle()``
        because technical headings may contain connector words such as
        ``"and"``, ``"of"``, and ``"for"``.
        """
        stripped = text.strip()

        if not cls._is_reasonable_heading_length(stripped):
            return False

        if stripped.endswith(cls._SENTENCE_ENDINGS):
            return False

        if "\n" in stripped:
            return False

        words = stripped.split()

        # Single capitalised words are often headings, but very short words
        # such as "The" are too ambiguous.
        if len(words) == 1:
            return (
                len(words[0]) >= 4
                and words[0][0].isupper()
            )

        connector_words = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "by",
            "for",
            "from",
            "in",
            "of",
            "on",
            "or",
            "the",
            "to",
            "with",
        }

        meaningful_word_count = 0
        title_style_word_count = 0

        for index, raw_word in enumerate(words):
            word = raw_word.strip("()[]{}:,-/")

            if not word:
                continue

            lower_word = word.casefold()

            if lower_word in connector_words and index != 0:
                continue

            meaningful_word_count += 1

            if word[0].isupper() or word.isupper():
                title_style_word_count += 1

        if meaningful_word_count == 0:
            return False

        # Require every meaningful word to look title-like.
        return title_style_word_count == meaningful_word_count

    @classmethod
    def _is_reasonable_heading_length(cls, text: str) -> bool:
        """
        Check whether text is short enough to plausibly be a heading.
        """
        if not text:
            return False

        if len(text) > cls._MAX_HEADING_CHARACTERS:
            return False

        return len(text.split()) <= cls._MAX_HEADING_WORDS

    @classmethod
    def _detect_non_heading_type(
        cls,
        text: str,
        style: str | None,
        declared_content_type: str | None,
        metadata: dict[str, Any],
    ) -> ElementType:
        """
        Classify a non-heading element as text, list, or table.
        """
        declared_type = (
            declared_content_type.casefold()
            if declared_content_type
            else ""
        )

        if declared_type in {"table", "table_row", "tabular"}:
            return ElementType.TABLE

        metadata_type = str(
            metadata.get("content_type", "")
        ).casefold()

        if metadata_type in {"table", "table_row", "tabular"}:
            return ElementType.TABLE

        if style and "table" in style.casefold():
            return ElementType.TABLE

        if declared_type in {
            "list",
            "list_item",
            "bullet",
            "numbered_list",
        }:
            return ElementType.LIST

        if style and "list" in style.casefold():
            return ElementType.LIST

        if cls._LIST_ITEM_PATTERN.match(text):
            return ElementType.LIST

        return ElementType.TEXT

    @staticmethod
    def _update_heading_hierarchy(
        active_headings: dict[int, str],
        heading_level: int,
        heading_text: str,
    ) -> None:
        """
        Update the current heading hierarchy.

        When a new heading appears, headings at the same or deeper levels are
        removed before the new heading is inserted.

        Example
        -------
        Existing hierarchy:

            1 Safety Requirements
            2 Risk Assessment
            3 Hazard Identification

        New level-2 heading:

            2 Emergency Response

        Updated hierarchy:

            1 Safety Requirements
            2 Emergency Response
        """
        levels_to_remove = [
            level
            for level in active_headings
            if level >= heading_level
        ]

        for level in levels_to_remove:
            del active_headings[level]

        active_headings[heading_level] = heading_text

    @staticmethod
    def _build_section_path(
        active_headings: dict[int, str],
    ) -> list[str]:
        """
        Build an ordered section path from the active heading hierarchy.
        """
        return [
            active_headings[level]
            for level in sorted(active_headings)
        ]

    @staticmethod
    def _get_value(
        unit: Any,
        field_name: str,
        default: Any = None,
    ) -> Any:
        """
        Read a value from either an object or dictionary parser unit.
        """
        if isinstance(unit, dict):
            return unit.get(field_name, default)

        return getattr(unit, field_name, default)

    @staticmethod
    def _normalise_optional_string(
        value: Any,
    ) -> str | None:
        """
        Convert a value to a stripped string or return ``None``.
        """
        if value is None:
            return None

        normalised = str(value).strip()
        return normalised or None

    @staticmethod
    def _normalise_optional_integer(
        value: Any,
    ) -> int | None:
        """
        Convert a value to an integer when possible.

        Invalid or missing values return ``None`` instead of interrupting the
        complete document-analysis process.
        """
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalise_metadata(
        value: Any,
    ) -> dict[str, Any]:
        """
        Return a safe copy of parser metadata.
        """
        if isinstance(value, dict):
            return dict(value)

        return {}